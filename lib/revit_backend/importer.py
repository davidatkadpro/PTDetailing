# -*- coding: utf-8 -*-
"""High-level import workflow for PTD text files.

Usage (from pushbutton script):

    from revit_backend.importer import import_ptd_file
    import_ptd_file(doc, filepath)

Steps:
1. Ensure required families are loaded (auto-loader).
2. Parse PTD file into TendonSet using existing parser helper.
3. Adapt raw parsed tendons to objects compatible with creator.py
4. Compute translation after adaptation (we now have XYZ in feet)
5. Create tendon elements via `creator.create_tendons`.
6. (future) Snap ends if setting enabled.
"""

from __future__ import absolute_import

# pyRevit APIs – extension must run inside Revit

from pyrevit import revit  # type: ignore
from pyrevit import DB  # Add missing import for DB module
from pyrevit import forms
from .families import ensure_families, get_tendon_symbol
from .alignment import get_alignment_transform
from .creator import create_tendons
from .snapper import snap_tendon_ends
from . import settings as _settings
from ptd_parser import parse_ptd_file
from .ptd_adapter import load_tendons_from_ptd
from .grouping import group_tendons
from .settings import load as load_settings
from utils.geometry import centroid

# Attempt to import existing PTD parser (legacy)
try:
    from revit_backend.ptd_adapter import load_tendons_from_ptd  # type: ignore
except Exception:  # noqa: BLE001
    try:
        from example_lib.ImportPTD import ImportTendonsText  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("No PTD parser found: {}".format(exc))

    def load_tendons_from_ptd(path):  # type: ignore
        return ImportTendonsText(path).process()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Revit has a hard limit on the number of elements that can be in a group.
_MAX_GROUP_SIZE = 10000

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def import_ptd_file(doc, ptd_file_path, view):
    """Import a PTD file and create all Revit elements.

    This is the main entry point that orchestrates parsing, adapting, and
    creating all elements inside a single Revit transaction.
    """

    # 1. Ensure required families are loaded before we do anything else.
    #    The function returns False if families are missing and can't be loaded.
    if not ensure_families(doc):
        forms.alert(
            "Required families are missing. Please check project settings.",
            title="Families Not Found",
            warn_icon=True,
        )
        return

    # 2. Parse the raw PTD file into a structured format.
    try:
        # NOTE: The adapter currently re-parses the file. This is inefficient
        # and should be refactored to pass the parsed data directly.
        # ptd_data = parse_ptd_file(ptd_file_path)
        pass
    except Exception as e:
        forms.alert(
            "Failed to parse PTD file:\n{}".format(e),
            title="Import Error",
            warn_icon=True,
        )
        return

    # 3. Adapt PTD data into Tendon objects
    tendon_set = load_tendons_from_ptd(ptd_file_path)
    if not tendon_set:
        forms.alert("No tendons found in PTD file.", title="Import Warning")
        return

    # 4. Align imported tendons with the model by transforming coordinates
    try:
        points = []
        for t in tendon_set:
            points.append((t.start.X, t.start.Y))
            points.append((t.end.X, t.end.Y))

        if points:
            xf = get_alignment_transform(doc, points, view=view)
            if xf is None:
                return  # User cancelled alignment

            angle_rad, dx, dy = xf
            if angle_rad != 0.0 or dx != 0.0 or dy != 0.0:
                origin = centroid(points)
                _apply_transform(tendon_set, angle_rad, dx, dy, origin=origin)
    except ImportError:
        # If alignment module is missing, just proceed without it.
        # This could be the case in older versions or if files were moved.
        pass
    except Exception as e:
        forms.alert("Failed to align tendons: {}".format(e), title="Alignment Error")
        return

    # 5. Load settings to determine import options
    cfg = load_settings()
    group = cfg.get("group_tendons", True)
    snap = cfg.get("auto_snap_ends", True)
    create_group = cfg.get("create_detail_group", True)

    # 6. Create all the primary Revit elements (tendons, drapes, leaders)
    #    This is done in one transaction. We get back the IDs of all created elements.
    created_ids = create_tendons(
        doc,
        tendon_set,
        group=group,
        snap_all_ends=snap,
        view=view,
    )

    if not created_ids:
        forms.alert("Failed to create any tendon elements.", title="Import Error")
        return

    # 7. Optionally, create a final detail group from all created elements.
    #    This is done in a separate transaction to avoid "modified outside group edit" warnings.
    if create_group and created_ids:
        if len(created_ids) > _MAX_GROUP_SIZE:
            forms.alert(
                "Number of elements ({}) exceeds Revit's group limit of {}.".format(
                    len(created_ids), _MAX_GROUP_SIZE
                ),
                title="Group Too Large",
            )
        else:
            try:
                from System.Collections.Generic import List as ClrList
                
                with revit.Transaction("Create PT Detail Group"):
                    # Convert python list to .NET List[ElementId]
                    element_ids_net = ClrList[DB.ElementId]()
                    for eid in created_ids:
                        element_ids_net.Add(eid)
                    doc.Create.NewGroup(element_ids_net)
            except Exception as e:
                # Fail gracefully if grouping fails for any reason
                forms.alert(
                    "Failed to create final detail group:\n{}".format(e),
                    title="Grouping Error",
                )

    return len(created_ids)


def get_tendon_points(filepath):
    # Implementation of get_tendon_points function
    # This function is not provided in the original file or the code block
    # It's assumed to exist as it's called in the import_ptd_file function
    # If this function is not needed, it can be removed from the code block
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_translation(tendon_set, dx, dy):
    """Mutate *tendon_set* coordinates by *dx, dy* (feet)."""

    for tendon in tendon_set:
        tendon.start = DB.XYZ(tendon.start.X + dx, tendon.start.Y + dy, tendon.start.Z)
        tendon.end = DB.XYZ(tendon.end.X + dx, tendon.end.Y + dy, tendon.end.Z)
        # Shift any intermediate tendon_points if present (x positions only)
        if getattr(tendon, "tendon_points", None):
            shifted = []
            for x_ft, elev_mm in tendon.tendon_points:
                # *Distance* along tendon should remain unchanged – it is relative
                # to the (already-translated) start point, *not* an absolute X-coord.
                shifted.append([x_ft, elev_mm])
            tendon.tendon_points = shifted


# ---------------------------------------------------------------------------
# New transform helper – rotation + translation (Jul 2025)
# ---------------------------------------------------------------------------


def _apply_transform(tendon_set, angle_rad, dx, dy, origin=(0.0, 0.0)):
    """Rotate each tendon start/end about *origin* by *angle_rad* then translate."""
    from math import cos, sin

    if angle_rad == 0.0 and (dx == 0.0 and dy == 0.0):
        return  # nothing to do

    ox, oy = origin
    cos_a = cos(angle_rad)
    sin_a = sin(angle_rad)

    def _rot(x, y):
        tx = x - ox
        ty = y - oy
        rx = tx * cos_a - ty * sin_a + ox
        ry = tx * sin_a + ty * cos_a + oy
        return rx + dx, ry + dy

    for tendon in tendon_set:
        sx, sy = tendon.start.X, tendon.start.Y
        ex, ey = tendon.end.X, tendon.end.Y

        rsx, rsy = _rot(sx, sy)
        rex, rey = _rot(ex, ey)

        tendon.start = DB.XYZ(rsx, rsy, tendon.start.Z)
        tendon.end = DB.XYZ(rex, rey, tendon.end.Z)


# ---------------------------------------------------------------------------
# Adaptation helpers
# ---------------------------------------------------------------------------


def _adapt_tendons(raw_set):
    """Return list of tendon objects with `start`/`end` XYZ in feet."""

    from utils.conversions import mm_to_ft  # type: ignore

    class _Tendon(object):
        """Lightweight mutable container for tendon attributes."""

    out = []
    for td in raw_set:
        if hasattr(td, "start") and hasattr(td, "end"):
            out.append(td)
            continue

        sx, sy = td.start_xy_mm
        ex, ey = td.end_xy_mm

        t = _Tendon()
        t.start = DB.XYZ(mm_to_ft(sx), mm_to_ft(sy), 0.0)
        t.end = DB.XYZ(mm_to_ft(ex), mm_to_ft(ey), 0.0)
        t.length = td.length_mm / 1000.0  # metres
        t.strand_no = td.strand_count
        t.start_is_live = getattr(td, "start_is_live", True)
        t.end_is_live = getattr(td, "end_is_live", False)
        t.tendon_points = [
            [mm_to_ft(p.distance_mm), p.height_mm] for p in getattr(td, "points", [])
        ]

        out.append(t)

    return out 
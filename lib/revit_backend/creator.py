# -*- coding: utf-8 -*-
"""Create Revit elements from imported tendon data.

This module handles the creation of all Revit geometry inside a transaction.

Public API:
  create_tendons(doc, tendon_set) → list of created ElementIds

Design notes:
 - The module is written to be CPython-compatible for testing, using stub
   implementations of Revit API objects where necessary. When running inside
   pyRevit, the actual `pyrevit.DB` is used.
 - All element creation is batched inside a single Revit transaction for
   performance and to allow a single rollback if any part fails.
 - Activation of family symbols is handled automatically.
"""

from __future__ import absolute_import

from utils.conversions import mm_to_ft
# Updated family helpers (renamed constants)
from .families import (
    get_tendon_symbol,
    get_leader_symbol,
    get_drape_symbols,
)

from .grouping import group_tendons
from .settings import load as load_settings
from .snapper import snap_tendon_ends
from . import tagger

__all__ = ["create_tendons"]

try:
    from pyrevit import DB, revit
except ImportError:
    raise ImportError("pyRevit API not available – PTDetailing must run inside Revit.")

uidoc = revit.uidoc

def _group_and_flag_tendons(tendon_set, tol_args):
    """Run grouping, identify primary tendon, and flag secondaries.

    Returns the generated list of groups.
    """
    from .grouping import group_tendons

    groups = group_tendons(tendon_set, **tol_args)
    for group in groups:
        if len(group) < 2:
            continue  # single tendons are implicitly primary

        # Determine primary (first if 2 tendons, middle otherwise)
        # This matches the logic that will be used for leader placement.
        primary_td = group[0] if len(group) == 2 else group[len(group) // 2]

        for td in group:
            if td is not primary_td:
                td.grouped = True  # type: ignore[attr-defined]

    return groups

def create_tendons(doc, tendon_set, group=False, group_name=None, snap_all_ends=False, view=None):
    """Place tendon elements for *tendon_set* into *doc*.

    Parameters
    ----------
    doc            Revit document
    tendon_set     Legacy `TendonSet` containing `Tendon` objects
    group          If True, run grouping logic and create leaders.
    group_name     Optional name for the group
    snap_all_ends  If True, run snapping logic before returning.
    view           Optional view for snapping
    Returns list of ElementIds created.
    """

    created_ids = []  # list of ElementIds

    # Ensure family symbols loaded **before** starting transaction.
    tendon_symbol = get_tendon_symbol(doc)  # anchor symbol used at both ends
    leader_symbol = get_leader_symbol(doc)  # separate family for grouped leader annotation
    drape_mid_sym, drape_start_sym, drape_end_sym = get_drape_symbols(doc)

    # Load settings and determine groups before transaction starts
    cfg = load_settings()
    drape_end_tags = cfg.get("drape_end_tags", False)

    groups = []
    if group:
        # Convert mm settings to feet for the grouping function
        tol_args = {
            "angle_tol": cfg["group_angle_tol_deg"],
            "length_tol": mm_to_ft(cfg["group_length_tol_mm"]),
            "dist_tol": mm_to_ft(cfg["group_drape_dist_tol_mm"]),
            "height_tol": cfg["group_drape_height_tol_mm"],
            "spacing_tol": mm_to_ft(cfg["group_spacing_tol_mm"]),
            "shift_tol": mm_to_ft(cfg["group_shift_tol_mm"]),
        }
        groups = _group_and_flag_tendons(tendon_set, tol_args)

    t = DB.Transaction(doc, "Create PT Tendons")
    t.Start()
    try:
        # Activate symbols once inside transaction
        tendon_sym = _ensure_symbol_active(doc, tendon_symbol)
        leader_sym = _ensure_symbol_active(doc, leader_symbol)
        drape_mid_sym = _ensure_symbol_active(doc, drape_mid_sym)
        drape_start_sym = _ensure_symbol_active(doc, drape_start_sym)
        drape_end_sym = _ensure_symbol_active(doc, drape_end_sym)

        for tendon in tendon_set:  # type: ignore[annotation-unchecked]
            # Single tendon detail component along the full path
            start_xyz = DB.XYZ(tendon.start.X, tendon.start.Y, tendon.start.Z)
            inst = _place_instance(
                doc,
                tendon_sym,
                start_xyz,
                DB.XYZ(tendon.end.X, tendon.end.Y, tendon.end.Z),
            )

            if inst:
                _set_end_params(inst, tendon.start_type, tendon.end_type, cfg)

                # Set instance parameters for ID and strand count
                try:
                    p_id = inst.LookupParameter("PT Tendon Id")
                    if p_id:
                        p_id.Set(tendon.ID)

                    p_strands = inst.LookupParameter("PT No. of Strands within Tendon")
                    if p_strands:
                        p_strands.Set(tendon.strand_no)

                    

                    p_data = inst.LookupParameter("PT Tendon Data")
                    if p_data:
                        # Format drape points as "dist:height,dist:height,..."
                        # dist is in feet, height is in mm
                        drape_str = ",".join(
                            "{}:{}".format(dist_ft, height_mm)
                            for dist_ft, height_mm in tendon.tendon_points
                        )
                        p_data.Set(drape_str)

                except Exception:
                    # Fail silently if params do not exist on the family
                    pass
                
                created_ids.append(inst.Id)

                # Persist element reference on the tendon so grouping/leader logic
                # can write back shared parameters afterwards.
                try:
                    tendon.element = inst  # type: ignore[attr-defined]
                except Exception:
                    pass

            # Drape symbols only for primary (non-grouped) tendons and if enabled
            if not cfg.get("drape_tags", False) or getattr(tendon, "grouped", False):
                continue

            vec = tendon.end - tendon.start  # type: ignore[attr-defined]
            horiz_len = (vec.X ** 2 + vec.Y ** 2) ** 0.5 or 1.0  # feet

            for i, (dist_ft, height_mm) in enumerate(tendon.tendon_points):
                is_start_or_end = i == 0 or i == len(tendon.tendon_points) - 1
                if is_start_or_end and not drape_end_tags:
                    continue

                ratio = dist_ft / horiz_len
                px = tendon.start.X + vec.X * ratio
                py = tendon.start.Y + vec.Y * ratio
                pz = tendon.start.Z  # plan view – keep Z constant
                p_xyz = DB.XYZ(px, py, pz)

                if i == 0:
                    sym = drape_start_sym
                    param_name = "Drape End"
                elif i == len(tendon.tendon_points) - 1:
                    sym = drape_end_sym
                    param_name = "Drape End"
                else:
                    sym = drape_mid_sym
                    param_name = "Drape"

                inst = _place_instance(doc, sym, p_xyz)
                if inst:
                    try:
                        param = inst.LookupParameter(param_name)
                        if param:
                            param.Set(str(int(height_mm)))
                    except Exception:
                        pass
                    created_ids.append(inst.Id)

                    # Align drape symbol with tendon direction (rotate in plan)
                    try:
                        import math  # Local import to avoid module-level overhead

                        # Angle between tendon vector and global X axis (plan)
                        angle = vec.AngleTo(DB.XYZ.BasisX)
                        # Rotate so symbol points along tendon (subtract 90° so extents align)
                        rotation_axis = DB.Line.CreateBound(p_xyz, p_xyz + DB.XYZ.BasisZ)
                        DB.ElementTransformUtils.RotateElement(
                            doc,
                            inst.Id,
                            rotation_axis,
                            angle - (math.pi / 2.0),
                        )
                    except Exception:
                        # Fallback silently if rotation fails (e.g., during unit tests with stubs)
                        pass

        # --- Grouping Logic ---
        # 1. Flag the secondary tendons in our logical groups (not a Revit action)
        for logical_tendon_group in groups:
            for td in logical_tendon_group:
                if getattr(td, "grouped", False):
                    try:
                        param = td.element.LookupParameter("Grouped")
                        param_comment = td.element.LookupParameter("Comments")
                        if param:
                            param.Set(True)
                        if param_comment:
                            param_comment.Set("GROUPED")
                    except Exception:
                        pass  # element may not have param

        # 2. Create the leader elements and add their IDs to our list
        leader_ids = _place_group_leaders(doc, groups, leader_symbol)
        created_ids.extend(leader_ids)

        # Snap ends if requested, before creating the final group
        if snap_all_ends:
            tol_ft = cfg.get("auto_snap_tolerance_mm", 50) / 304.8
            snap_tendon_ends(doc, tendon_set, tol_ft, view=view)

    finally:
        t.Commit()

    # After main transaction, tag the live ends if setting is enabled
    if cfg.get("tag_tendon_strands", True):
        tag_ids = tagger.tag_live_ends(doc, tendon_set)
        created_ids.extend(tag_ids)

    return created_ids

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_symbol_active(doc, symbol):
    """Activate symbol if it is not active (required before placement)."""

    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()
    return symbol


def _set_end_params(inst, start_type, end_type, cfg):
    """Set family instance parameters for end display modes and offsets."""
    if inst is None:
        return
    try:
        p_start = inst.LookupParameter("End 1 Display Mode")
        p_end = inst.LookupParameter("End 2 Display Mode")
        p_start_offset = inst.LookupParameter("Pan Offset End 1")
        p_end_offset = inst.LookupParameter("Pan Offset End 2")

        # Set end types (Live/Dead/Pan)
        if p_start and p_start.StorageType == DB.StorageType.Integer:
            p_start.Set(start_type)
        if p_end and p_end.StorageType == DB.StorageType.Integer:
            p_end.Set(end_type)

        # Get offset value from settings and convert to feet
        pan_offset_ft = mm_to_ft(cfg.get("pan_stressed_end_offset_mm", 1000))

        # Set offset only for pan-stressed ends (type 3)
        if start_type == 3:
            if p_start_offset and p_start_offset.StorageType == DB.StorageType.Double:
                p_start_offset.Set(pan_offset_ft)
        
        if end_type == 3:
            if p_end_offset and p_end_offset.StorageType == DB.StorageType.Double:
                p_end_offset.Set(pan_offset_ft)

    except Exception:
        # Fail silently if params do not exist on the family
        pass


def _set_drape_params(drape_inst, tendon):
    """Populate basic parameters on the drape symbol."""

    mappings = {
        "Length": getattr(tendon, "length", None),
        "Strands": getattr(tendon, "strand_no", None),
    }
    for pname, value in mappings.items():
        if value is None:
            continue
        try:
            param = drape_inst.LookupParameter(pname)
            if param and param.StorageType in (DB.StorageType.Double, DB.StorageType.Integer):
                if param.StorageType == DB.StorageType.Double:
                    param.Set(mm_to_ft(value * 1000.0))  # assume length in m → mm
                else:
                    param.Set(int(value))
        except Exception:
            pass

def _place_instance(doc, symbol, xyz, end_xyz=None):
    """Place family symbol at xyz with correct overload depending on placement type."""
    view = uidoc.ActiveView if uidoc else None

    if end_xyz and hasattr(DB, "Line") and hasattr(DB.Line, "CreateBound"):
        # Attempt line-based overload (line, symbol, view) when API available
        z_level = view.GenLevel.Elevation if hasattr(view, "GenLevel") else xyz.Z
        start_pt = DB.XYZ(xyz.X, xyz.Y, z_level)
        end_pt = DB.XYZ(end_xyz.X, end_xyz.Y, z_level)
        line = DB.Line.CreateBound(start_pt, end_pt)
        return doc.Create.NewFamilyInstance(line, symbol, view)

    # Point based overload (xyz, symbol, view)
    return doc.Create.NewFamilyInstance(xyz, symbol, view)

# ---------------------------------------------------------------------------
# Leader placement helpers (grouped tendons)
# ---------------------------------------------------------------------------

def _place_group_leaders(doc, groups, leader_symbol):
    """Place a single leader component for each grouped tendon set.

    Groups are determined via ``grouping.group_tendons``. The leader is placed
    perpendicular to the tendon direction at the one-third length position of
    the *representative* tendon (middle index of the group).
    """

    view = uidoc.ActiveView if uidoc else None
    if not view:
        return []

    created = []

    for group in groups:
        if len(group) < 2:
            continue  # Single tendon – no need for shared leader

        # Use first tendon as reference axis
        ref = group[0]
        vec = ref.end - ref.start  # type: ignore[attr-defined]
        length = (vec.X ** 2 + vec.Y ** 2) ** 0.5 or 1.0
        dir_u = DB.XYZ(vec.X / length, vec.Y / length, 0)
        perp_u = DB.XYZ(-dir_u.Y, dir_u.X, 0)  # rotate 90°

        # Compute perpendicular offset for each tendon (signed)
        offsets = []
        for td in group:
            diff = td.start - ref.start  # type: ignore[attr-defined]
            off = diff.X * perp_u.X + diff.Y * perp_u.Y
            offsets.append((off, td))

        offsets.sort(key=lambda o: o[0])

        # Calculate spacings between adjacent tendons
        spacings = [offsets[i + 1][0] - offsets[i][0] for i in range(len(offsets) - 1)]
        tol = 0.1  # ft tolerance when considering equal spacing

        uniform = max(spacings) - min(spacings) <= tol if spacings else False

        def _leader_between(off_a, off_b):
            mid_offset = (off_a + off_b) / 2.0
            base = DB.XYZ(
                ref.start.X + dir_u.X * (length / 3.0) + perp_u.X * mid_offset,
                ref.start.Y + dir_u.Y * (length / 3.0) + perp_u.Y * mid_offset,
                ref.start.Z,
            )
            span_vec = DB.XYZ(perp_u.X * (off_b - off_a), perp_u.Y * (off_b - off_a), 0)
            p1 = DB.XYZ(base.X - span_vec.X / 2.0, base.Y - span_vec.Y / 2.0, base.Z)
            p2 = DB.XYZ(base.X + span_vec.X / 2.0, base.Y + span_vec.Y / 2.0, base.Z)
            return p1, p2, abs(off_b - off_a)

        if uniform:
            total_span = offsets[-1][0] - offsets[0][0]
            spacing_val = total_span / float(len(offsets) - 1) if len(offsets) > 1 else total_span
            p1, p2, _ = _leader_between(offsets[0][0], offsets[-1][0])
            inst = _place_instance(doc, leader_symbol, p1, p2)
            if inst:
                _set_centres_param(inst, spacing_val)
                created.append(inst.Id)
        else:
            for i in range(len(offsets) - 1):
                off_a, _ = offsets[i]
                off_b, _ = offsets[i + 1]
                p1, p2, spacing = _leader_between(off_a, off_b)
                inst = _place_instance(doc, leader_symbol, p1, p2)
                if inst:
                    _set_centres_param(inst, spacing)
                    created.append(inst.Id)

    return created

def _set_centres_param(inst, spacing):
    """Helper to set Centres parameter on leader instance (feet)."""

    try:
        centres = inst.LookupParameter("Centres")
        if centres and centres.StorageType == DB.StorageType.Double:
            centres.Set(spacing)
    except Exception:
        pass
        

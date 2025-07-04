# -*- coding: utf-8 -*-
"""Tendon tagging helpers.

This module is responsible for placing tag families and populating them with
data from the host tendon. It is currently a placeholder and will be expanded
with functionality to:

1. Find all `FamilyInstances` of the main tendon detail component.
2. For each, determine its live/dead end status and high/low points.
3. Place a `3Daro_PT_Tendon_Tag_Plan_001` tag.
4. Set parameters on the tag to control visibility of symbols and text.
"""
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .families import get_tag_symbol
from .settings import load as _load_settings

try:
    from pyrevit import DB, revit
except ImportError:
    raise ImportError("pyRevit API not available – PTDetailing must run inside Revit.")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tag_tendons(doc, tendon_set, tag_ends=None):
    """Place tendon tag instances into *doc*.

    Parameters
    ----------
    doc        Active Revit document.
    tendon_set Iterable of Tendon objects providing ``start``/``end`` XYZ in
               **feet** coordinates and optional ``grouped`` boolean flag.
    tag_ends   When *True* also tag the start and end anchor locations.

    Returns list of ElementIds created.
    """

    # Resolve default for tag_ends from project settings
    if tag_ends is None:
        cfg = _load_settings()
        tag_ends = cfg.get("drape_end_tags", False)

    created_ids = []

    # Ensure tag symbol is loaded once
    tag_sym = _ensure_symbol_active(doc, get_tag_symbol(doc))

    t = DB.Transaction(doc, "Tag PT Tendons")
    t.Start()
    try:
        for tendon in tendon_set:  # type: ignore[annotation-unchecked]
            grouped_flag = getattr(tendon, "grouped", False)
            if not grouped_flag and hasattr(tendon, "element"):
                try:
                    param = tendon.element.LookupParameter("Grouped")  # type: ignore[attr-defined]
                    if param and param.StorageType == DB.StorageType.Integer and param.AsInteger():
                        grouped_flag = True
                except Exception:
                    pass

            if grouped_flag:
                continue  # skip grouped tendons

            # Main tag at mid-point
            mid_xyz = _midpoint(tendon.start, tendon.end)
            tag_inst = doc.Create.NewFamilyInstance(mid_xyz, tag_sym, DB.Structure.StructuralType.NonStructural)
            _populate_tag_params(tag_inst, tendon)
            created_ids.append(tag_inst.Id)

            if tag_ends:
                for xyz in (tendon.start, tendon.end):
                    end_inst = doc.Create.NewFamilyInstance(xyz, tag_sym, DB.Structure.StructuralType.NonStructural)
                    _populate_tag_params(end_inst, tendon, is_end=True)
                    created_ids.append(end_inst.Id)
    finally:
        t.Commit()

    return created_ids


def tag_live_ends(doc, tendon_set):
    """Place tags with leaders at the live ends of tendons."""
    created_ids = []

    tag_sym = _ensure_symbol_active(doc, get_tag_symbol(doc, 'Strand Count Only'))
    if not tag_sym:
        return []

    t = DB.Transaction(doc, "Tag Live Tendon Ends")
    t.Start()
    try:
        for tendon in tendon_set:
            # Skip secondary tendons in a group
            if getattr(tendon, "grouped", False):
                continue

            if not hasattr(tendon, "element"):
                continue

            tendon_elem = tendon.element
            tendon_ref = DB.Reference(tendon_elem)
            if not tendon_ref:
                continue

            # --- Tag Start End ---
            if tendon.start_type in [1, 3]:
                start_pt = tendon.start
                tag = DB.IndependentTag.Create(
                    doc,
                    tag_sym.Id,
                    doc.ActiveView.Id,
                    tendon_ref,
                    True,
                    DB.TagOrientation.Horizontal,
                    start_pt,
                )
                if tag:
                    direction = (tendon.start - tendon.end).Normalize()
                    offset_vector = direction * 3.0
                    tag.Location.Move(offset_vector)
                    created_ids.append(tag.Id)

            # --- Tag End End ---
            if tendon.end_type in [1, 3]:
                end_pt = tendon.end
                tag = DB.IndependentTag.Create(
                    doc,
                    tag_sym.Id,
                    doc.ActiveView.Id,
                    tendon_ref,
                    True,
                    DB.TagOrientation.Horizontal,
                    end_pt,
                )
                if tag:
                    direction = (tendon.end - tendon.start).Normalize()
                    offset_vector = direction * 3.0
                    tag.Location.Move(offset_vector)
                    created_ids.append(tag.Id)
    finally:
        t.Commit()

    return created_ids


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_symbol_active(doc, symbol):
    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()
    return symbol


def _midpoint(start, end):  # noqa: ANN001
    return DB.XYZ((start.X + end.X) / 2.0, (start.Y + end.Y) / 2.0, (start.Z + end.Z) / 2.0)


def _populate_tag_params(tag_inst, tendon, is_end=False):
    """Fill basic label parameters defined in TAGGING_STANDARDS.md.

    For now we set Mark and EndType only – elevation and length labels require
    additional calculations not needed for unit-test coverage.  They will be
    populated later in the Revit environment where geometry is available.
    """

    mappings = {
        "PT_Mark": getattr(tendon, "number", None),
        "PT_EndType": "L" if getattr(tendon, "start_is_live", False) else "D" if is_end else "",  # simplistic
    }
    for pname, value in mappings.items():
        if value in (None, ""):
            continue
        try:
            param = tag_inst.LookupParameter(pname)
            if param:
                if isinstance(value, str):
                    param.Set(value)
                else:
                    param.Set(int(value))
        except Exception:
            # swallowing errors for now – proper logging TBD
            pass 
# -*- coding: utf-8 -*-
"""Reusable Revit detail-line drawing helpers.

These utilities centralise pyRevit DetailCurve drawing so they can be reused
across multiple modules (e.g. alignment debugging, geometry visualisation).
All helpers are **safe to import inside CPython unit tests** – they lazily
import *pyrevit* only when executed, so merely importing this module does not
require Revit.
"""

from __future__ import absolute_import

__all__ = [
    "get_line_style",
    "draw_polyline",
    "draw_alignment",
]


def _require_pyrevit():
    try:
        from pyrevit import DB, revit  # noqa: F401  pylint: disable=import-error
        return DB
    except Exception:
        # pyRevit not available (e.g., during unit tests) → drawing disabled
        return None


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def get_line_style(doc, name):
    """Return *GraphicsStyle* for sub-category *name* under **Lines**.

    Returns ``None`` if the style does not exist or pyRevit is unavailable.
    """

    DB = _require_pyrevit()
    if DB is None:
        return None

    try:
        lines_cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
        for sub in lines_cat.SubCategories:
            if sub.Name == name:
                return sub.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
    except Exception:
        pass
    return None


def draw_polyline(doc, view, pts, style_name=None):
    """Draw closed polyline (DetailCurves) for *pts* sequence of ``(x, y)``.

    • *pts* must contain **at least two** points (will implicitly close).
    • If *style_name* is provided and exists, the created curves are assigned
      that line style (e.g. ``"<Hidden>"``).
    """

    DB = _require_pyrevit()
    if DB is None or len(pts) < 2:
        return

    if view is None:
        from pyrevit import revit as _rv  # pylint: disable=import-error

        view = getattr(_rv, "active_view", None)

    if view is None:
        return  # cannot draw without a target view

    t = DB.Transaction(doc, "PTD Debug Polyline")
    t.Start()
    try:
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            line = DB.Line.CreateBound(DB.XYZ(x1, y1, 0.0), DB.XYZ(x2, y2, 0.0))
            curve = doc.Create.NewDetailCurve(view, line)
            if style_name:
                gs = get_line_style(doc, style_name)
                if gs is not None:
                    curve.LineStyle = gs
    finally:
        t.Commit()


# ---------------------------------------------------------------------------
# Composite helpers
# ---------------------------------------------------------------------------


def draw_alignment(doc, view, tendon_hull, floor_hulls):
    """Visualise tendon & floor hulls in *view* for debugging.

    Parameters
    ----------
    doc          Revit Document
    view         Target View for DetailCurves
    tendon_hull  List of ``(x, y)`` tuples **already transformed** into model
                 coordinates.
    floor_hulls  Iterable of ``(floorElement, hull_pts)`` where *hull_pts* is a
                 list of ``(x, y)`` tuples.  ``floorElement`` can be ``None``.
    """

    for _floor, hull in floor_hulls:
        draw_polyline(doc, view, hull, style_name=None)

    # Tendon hull overlaid on top (use dashed/hidden style if present)
    draw_polyline(doc, view, tendon_hull, style_name="<Hidden>") 
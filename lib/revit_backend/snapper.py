# -*- coding: utf-8 -*-
"""Adjust tendon start/end points to nearest slab edge."""

from __future__ import absolute_import

try:
    from pyrevit import DB, revit
except ImportError as exc:
    raise ImportError("pyRevit API not available – PTDetailing must run inside Revit.")

__all__ = ["snap_tendon_ends"]


def snap_tendon_ends(doc, tendon_set, tol_ft, view=None):
    """Snap start/end XYZ of each tendon in *tendon_set* to the nearest
    bounding-box edge of any floor in *view* (or whole doc) if within *tol_ft*.
    """

    if view is None:
        view = getattr(revit, "active_view", None)

    minX, maxX, minY, maxY = _floor_extents(doc, view)
    if minX is None:  # No floors found
        return  # no floors → nothing to do

    for tendon in tendon_set:
        tendon.start = _snap_point(tendon.start, minX, maxX, minY, maxY, tol_ft)
        tendon.end = _snap_point(tendon.end, minX, maxX, minY, maxY, tol_ft)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _floor_extents(doc, view):
    collector = DB.FilteredElementCollector(doc, view.Id if view else None).OfClass(DB.Floor)

    minX = minY = None
    maxX = maxY = None
    for floor in collector:
        bbox = floor.get_BoundingBox(view) if view else floor.get_BoundingBox(None)
        if not bbox:
            continue
        mins = bbox.Min
        maxs = bbox.Max
        if minX is None:
            minX, maxX, minY, maxY = mins.X, maxs.X, mins.Y, maxs.Y
        else:
            minX = min(minX, mins.X)
            maxX = max(maxX, maxs.X)
            minY = min(minY, mins.Y)
            maxY = max(maxY, maxs.Y)

    return minX, maxX, minY, maxY


def _snap_point(pt, minX, maxX, minY, maxY, tol):
    if pt is None:
        return pt

    x = pt.X
    y = pt.Y

    dx_left = abs(x - minX)
    dx_right = abs(x - maxX)
    dy_bottom = abs(y - minY)
    dy_top = abs(y - maxY)

    min_d = min(dx_left, dx_right, dy_bottom, dy_top)

    if min_d > tol:
        return pt  # beyond tolerance

    if min_d == dx_left:
        x = minX
    elif min_d == dx_right:
        x = maxX
    elif min_d == dy_bottom:
        y = minY
    else:
        y = maxY

    return DB.XYZ(x, y, pt.Z) 
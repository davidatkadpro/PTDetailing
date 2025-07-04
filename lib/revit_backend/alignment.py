# -*- coding: utf-8 -*-
"""Automatic alignment helpers for tendon placement.

The algorithm is intentionally SIMPLE so that it runs fast inside IronPython
and has minimal dependency on heavy geometry API calls:

1. Compute convex hull of all tendon end points (import data) and take its
   centroid.
2. Collect all *Floor* elements visible in the active view, gather their
   bounding-box corners, compute their convex hull and centroid.
3. Return translation ``dx, dy`` so that the tendon centroid matches the
   floor centroid.  If floor centroid cannot be determined, ``(0, 0)`` is
   returned (caller should fall back to manual pick workflow).

Later we can swap in a more sophisticated matcher (e.g. Hausdorff / ICP) but
this heuristic is already a big improvement over requiring the user to pick a
point.
"""

from __future__ import absolute_import

try:
    from pyrevit import DB, revit
except ImportError as exc:
    raise ImportError("pyRevit API not available – PTDetailing must run inside Revit.")

from utils.geometry import (
    convex_hull,
    centroid,
    rotate,
    hausdorff_distance,
    poly_bounds,
    directed_hausdorff_outside as _dhd,
)

__all__ = [
    "compute_translation",
    "find_best_transform",
    "get_alignment_transform",
]

def compute_translation(doc, tendon_points, view=None):
    """Return *(dx, dy)* to align imported tendons to floors in *view*.

    *tendon_points* – iterable of ``(x, y)`` tuples *in feet*.
    If no suitable floor geometry found, returns *(0.0, 0.0)*.
    """

    if view is None:
        # pyRevit exposes revit.active_view
        view = getattr(revit, "active_view", None)

    tendon_cent = centroid(tendon_points)
    if tendon_cent == (0.0, 0.0):
        return (0.0, 0.0)

    floor_pts = _collect_floor_outline(doc, view)
    if not floor_pts:
        return (0.0, 0.0)

    floor_cent = centroid(floor_pts)
    dx = floor_cent[0] - tendon_cent[0]
    dy = floor_cent[1] - tendon_cent[1]
    return (dx, dy)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_floor_outline(doc, view):
    """Return list of (x, y) tuples representing slab outline.

    Implementation uses bounding boxes (cheap) rather than boundary loops –
    accurate enough for centroid matching.  Only considers floors visible in
    *view* if provided.
    """

    collector = DB.FilteredElementCollector(doc, view.Id if view else None).OfClass(DB.Floor)

    pts = []
    for floor in collector:
        try:
            bbox = floor.get_BoundingBox(view) if view else floor.get_BoundingBox(None)
        except Exception:
            bbox = None
        if not bbox:
            continue
        mins = bbox.Min
        maxs = bbox.Max
        # Corners in XY plane
        corners = [
            (mins.X, mins.Y),
            (mins.X, maxs.Y),
            (maxs.X, maxs.Y),
            (maxs.X, mins.Y),
        ]
        pts.extend(corners)

    if not pts:
        return []

    return convex_hull(pts)


# ---------------------------------------------------------------------------
# New accurate slab boundary helper (Jul 2025)
# ---------------------------------------------------------------------------


def _collect_floor_hulls(doc, view):
    """Return list of *(floor, hull_pts)* for each Floor visible in *view*.

    *hull_pts* is a list of (x, y) tuples representing the convex hull of the
    top-face boundary.  Falls back to bounding-box hull if geometry access
    fails (e.g. during unit tests with stubs).
    """

    from math import fabs

    results = []

    collector = DB.FilteredElementCollector(doc, view.Id if view else None).OfClass(DB.Floor)

    opts = DB.Options()
    opts.ComputeReferences = False
    opts.DetailLevel = DB.ViewDetailLevel.Fine

    for floor in collector:
        hull_pts = None
        try:
            geom = floor.get_Geometry(opts)
            if geom is None:
                raise Exception("no geom")

            for obj in geom:
                solid = getattr(obj, "GetEndIterator", None)
                # Revit GeometryObject could be Solid or other; we need Solid
                if not isinstance(obj, DB.Solid):
                    continue
                for face in obj.Faces:
                    # We only want horizontal faces (normal ≈ ±Z)
                    normal = face.FaceNormal
                    if fabs(normal.X) > 1e-3 or fabs(normal.Y) > 1e-3:
                        continue  # not horizontal
                    loops = face.EdgeLoops
                    for loop in loops:
                        pts = [(p.X, p.Y) for p in loop]
                        if len(pts) >= 3:
                            hull_pts = convex_hull(pts)
                            break
                    if hull_pts:
                        break
                if hull_pts:
                    break
        except Exception:
            hull_pts = None  # geometry extraction failed – will fallback

        if not hull_pts:
            # Fallback to bounding-box corners (existing logic)
            try:
                bbox = floor.get_BoundingBox(view) if view else floor.get_BoundingBox(None)
            except Exception:
                bbox = None
            if not bbox:
                continue
            mins = bbox.Min
            maxs = bbox.Max
            corners = [
                (mins.X, mins.Y),
                (mins.X, maxs.Y),
                (maxs.X, maxs.Y),
                (maxs.X, mins.Y),
            ]
            hull_pts = convex_hull(corners)

        if hull_pts:
            results.append((floor, hull_pts))

    return results 


# ---------------------------------------------------------------------------
# Combined slab hull helper – merge all floor outlines into single hull
# ---------------------------------------------------------------------------


def _collect_combined_floor_hull(doc, view):
    """Return convex hull (list of (x,y)) of *all* floors visible in view."""

    from math import fabs

    try:
        from pyrevit import DB
    except ImportError:
        return None

    collector = DB.FilteredElementCollector(doc, view.Id if view else None).OfClass(DB.Floor)

    opts = DB.Options()
    opts.ComputeReferences = False
    opts.DetailLevel = DB.ViewDetailLevel.Fine

    pts = []
    for floor in collector:
        try:
            geom = floor.get_Geometry(opts)
        except Exception:
            geom = None
        if not geom:
            continue
        for obj in geom:
            if not isinstance(obj, DB.Solid):
                continue
            for face in obj.Faces:
                n = face.FaceNormal
                if fabs(n.X) > 1e-3 or fabs(n.Y) > 1e-3:
                    continue  # skip vertical faces
                for loop in face.EdgeLoops:
                    for edge in loop:
                        try:
                            crv = edge.AsCurve()
                            p0 = crv.GetEndPoint(0)
                            pts.append((p0.X, p0.Y))
                        except Exception:
                            pass

    if not pts:
        return None

    return convex_hull(pts)


# ---------------------------------------------------------------------------
# Advanced alignment – rotation + translation search (Jul 2025)
# ---------------------------------------------------------------------------


def find_best_transform(
    doc,
    tendon_pts,
    view=None,
    angle_step_deg=15,
    refine_step_deg=5,
    max_error_ft=3.0,
    tolerance_ft=1.0,
    allow_rotation=True,
):
    """Return *(angle_rad, dx, dy, error)* that best fits *tendon_pts* into
    one of the floor hulls in *view*.

    The search is 2-D only (plan view).  It rotates the tendon convex hull by
    discrete *angle_step_deg* increments (0-360°), translates the result so
    its centroid matches the candidate floor centroid and computes
    Hausdorff distance.  The orientation with minimum error is refined with a
    finer *refine_step_deg* neighbourhood search.

    If the minimum error exceeds *max_error_ft*, returns *None* (caller should
    fall back to manual pick).
    """

    import math

    if view is None:
        view = getattr(revit, "active_view", None)

    slab_hull = _collect_combined_floor_hull(doc, view)
    if not slab_hull:
        return None  # no floors → caller handles fallback

    # Pre-compute tendon convex hull + centroid
    tendon_hull = convex_hull(tendon_pts)
    if not tendon_hull:
        return None

    tend_cent = centroid(tendon_hull)

    best = [None]  # mutable container to avoid Python 2 'nonlocal' limitation

    def _evaluate(angle_rad):
        # Rotate tendon hull around its centroid
        rot_pts = list(rotate(tendon_hull, angle_rad, origin=tend_cent))

        best_local = None  # (err, dx, dy)

        # Strategy A – centroid alignment
        floor_cent = centroid(slab_hull)
        dx = floor_cent[0] - tend_cent[0]
        dy = floor_cent[1] - tend_cent[1]
        shifted = [(x + dx, y + dy) for x, y in rot_pts]
        err = _dhd(shifted, slab_hull)
        best_local = (err, dx, dy)

        # Strategy B – bounding-box bottom-left alignment
        tend_bounds = poly_bounds(rot_pts)
        slab_bounds = poly_bounds(slab_hull)
        dx = slab_bounds[0] - tend_bounds[0]
        dy = slab_bounds[2] - tend_bounds[2]
        shifted = [(x + dx, y + dy) for x, y in rot_pts]
        err = _dhd(shifted, slab_hull)
        if err < best_local[0]:
            best_local = (err, dx, dy)

        # Strategy C – vertex-to-vertex exhaustive scan (coarse but catches odd fits)
        for sx, sy in slab_hull:
            for tx, ty in rot_pts:
                dx = sx - tx
                dy = sy - ty
                shifted = [(x + dx, y + dy) for x, y in rot_pts]
                err = _dhd(shifted, slab_hull)
                if err < best_local[0]:
                    best_local = (err, dx, dy)

        # Strategy D – keep best dy (usually bottom alignment) but align centroid X
        slab_cent_x = centroid(slab_hull)[0]
        tend_cent_x = tend_cent[0]
        dx_cx = slab_cent_x - tend_cent_x
        shifted_cx = [(x + dx_cx, y + dy) for x, y in rot_pts]
        err_cx = _dhd(shifted_cx, slab_hull)
        if err_cx < best_local[0]:
            best_local = (err_cx, dx_cx, dy)

        # Strategy E – keep best dy but align *left* edges (min-X)
        tend_bounds = poly_bounds(rot_pts)
        slab_bounds = poly_bounds(slab_hull)
        dx_left = slab_bounds[0] - tend_bounds[0]  # align min X values
        shifted_left = [(x + dx_left, y + dy) for x, y in rot_pts]
        err_left = _dhd(shifted_left, slab_hull)
        if err_left < best_local[0]:
            best_local = (err_left, dx_left, dy)

        err, dx, dy = best_local

        if best[0] is None or err < best[0][0]:
            best[0] = (err, angle_rad, dx, dy)

    if allow_rotation:
        step_rad = math.radians(angle_step_deg)
        angle = 0.0
        while angle < 2 * math.pi:
            _evaluate(angle)
            angle += step_rad
    else:
        _evaluate(0.0)

    if best[0] is None:
        return None

    # Refine around best angle ±refine
    if allow_rotation:
        refine_rad = math.radians(refine_step_deg)
        best_tuple = best[0]
        base_ang = best_tuple[1]
        for angle_rad in (
            base_ang - refine_rad,
            base_ang + refine_rad,
            base_ang - refine_rad / 2.0,
            base_ang + refine_rad / 2.0,
        ):
            _evaluate(angle_rad)

    # Final decision
    err, angle_rad, dx, dy = best[0]

    # -------------------------------------------------------------------
    # Post-process: snap left edges (min X) if it improves or maintains error
    # -------------------------------------------------------------------
    try:
        from math import cos, sin
    except ImportError:
        cos = sin = None  # running under tests without math? shouldn't happen

    # Recreate transformed tendon hull with current best transform
    if cos and sin:
        cos_a = cos(angle_rad)
        sin_a = sin(angle_rad)
        ox, oy = tend_cent
        trans_tendon = []
        for x, y in tendon_hull:
            tx = x - ox
            ty = y - oy
            rx = tx * cos_a - ty * sin_a + ox + dx
            ry = tx * sin_a + ty * cos_a + oy + dy
            trans_tendon.append((rx, ry))

        tend_bounds_tx = poly_bounds(trans_tendon)
        slab_bounds = poly_bounds(slab_hull)
        snap_dx = slab_bounds[0] - tend_bounds_tx[0]
        if abs(snap_dx) > 1e-6:
            shifted = [(x + snap_dx, y) for x, y in trans_tendon]
            snap_err = _dhd(shifted, slab_hull)
            # Accept if error not worse than current best by more than tolerance_ft
            if snap_err <= err + tolerance_ft:
                dx += snap_dx
                err = snap_err

    if err > max_error_ft:
        return None

    return (angle_rad, dx, dy, err)


# ---------------------------------------------------------------------------
# Public wrapper – decide auto vs manual pick
# ---------------------------------------------------------------------------


def _pick_translation(doc, tendon_pts, view=None):
    """Prompt user to pick bottom-left insertion point; return (dx, dy).

    *tendon_pts* is an iterable of (x, y) tuples (feet).  The function flattens
    to find bottom-left of the tendon hull, then subtracts that from the user
    point.
    """

    try:
        from pyrevit import revit  # late import for tests
        sel = revit.uidoc.Selection
        prompt = "Pick bottom-left insertion point for tendon import"
        picked = sel.PickPoint(prompt)
        if picked is None:
            raise Exception("user cancelled")
    except Exception:
        # User cancelled or running under tests – return zero transform so
        # caller can handle graceful abort.
        return None

    min_x, _, min_y, _ = poly_bounds(tendon_pts)
    dx = picked.X - min_x
    dy = picked.Y - min_y
    return (dx, dy)


# ---------------------------------------------------------------------------
# Simple alignment shortcut – centroid then bottom-left snap (Aug 2025)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NOTE: Extra debug prints added Aug 2025 – remove or toggle as needed
# ---------------------------------------------------------------------------

def _simple_fit(doc, tendon_pts, view, max_error_ft=3.0, tolerance_ft=1.0):
    """Return (angle_rad, dx, dy, err) using a very fast 2-step heuristic.

    1. Translate so tendon centroid matches slab centroid. If Hausdorff error
       ≤ *max_error_ft* → done.
    2. Else translate so tendon bounding-box minX/minY match slab minX/minY
       (bottom-left). If error ≤ *max_error_ft* → done.
    3. Otherwise return *None* so caller can try more advanced search.
    """

    slab_hull = _collect_combined_floor_hull(doc, view)
    if not slab_hull:
        return None

    tendon_hull = convex_hull(tendon_pts)
    if not tendon_hull:
        return None

    # Step 1 – centroid alignment
    tend_cent = centroid(tendon_hull)
    slab_cent = centroid(slab_hull)
    dx_c = slab_cent[0] - tend_cent[0]
    dy_c = slab_cent[1] - tend_cent[1]
    shifted_c = [(x + dx_c, y + dy_c) for x, y in tendon_hull]
    err_c = _dhd(shifted_c, slab_hull)
    if err_c <= max_error_ft + tolerance_ft:
        return (0.0, dx_c, dy_c, err_c)

    # Step 2 – bottom-left (minX/minY) alignment
    t_bounds = poly_bounds(tendon_hull)
    s_bounds = poly_bounds(slab_hull)
    dx_bl = s_bounds[0] - t_bounds[0]  # align minX
    dy_bl = s_bounds[2] - t_bounds[2]  # align minY (bottom)
    shifted_bl = [(x + dx_bl, y + dy_bl) for x, y in tendon_hull]
    err_bl = _dhd(shifted_bl, slab_hull)
    if err_bl <= max_error_ft + tolerance_ft:
        return (0.0, dx_bl, dy_bl, err_bl)

    return None


def get_alignment_transform(
    doc,
    tendon_pts,
    view=None,
    max_error_ft=3.0,
    angle_step_deg=15,
    refine_step_deg=5,
    tolerance_ft=1.0,
    allow_rotation=True,
):
    """Return *(angle_rad, dx, dy)* using auto-fit or manual pick fallback.

    1. Attempt simple centroid/bottom-left fit (fast path).
    2. If allow_rotation or simple fit fails, call *find_best_transform*.
    3. If still no fit within threshold, prompt user via *_pick_translation*.
    4. If user cancels, returns *None* (caller should abort import).
    """

    # Fast simple fit first (no rotation). Helps most typical cases.
    simple_res = _simple_fit(
        doc,
        tendon_pts,
        view,
        max_error_ft=max_error_ft,
        tolerance_ft=tolerance_ft,
    )
    if simple_res is not None:
        angle_s, dx_s, dy_s, err_s = simple_res
        if err_s <= max_error_ft + tolerance_ft:
            return (angle_s, dx_s, dy_s)

    # ---------------------------------------------------------------
    # Fallback to original (potentially rotational) search.
    # ---------------------------------------------------------------
    res = find_best_transform(
        doc,
        tendon_pts,
        view=view,
        angle_step_deg=angle_step_deg,
        refine_step_deg=refine_step_deg,
        max_error_ft=max_error_ft,
        tolerance_ft=tolerance_ft,
        allow_rotation=allow_rotation,
    )

    if res is not None:
        angle_rad, dx, dy, err = res
        if err <= max_error_ft + tolerance_ft:
            return (angle_rad, dx, dy)

    # Fallback → user pick
    pick = _pick_translation(doc, tendon_pts, view=view)
    if pick is None:
        return None  # user cancelled

    dx, dy = pick
    return (0.0, dx, dy)


# ---------------------------------------------------------------------------
# Drawing helpers moved to lib.revit_backend.helpers.detail_drawing
# ---------------------------------------------------------------------------

# (imported lazily to avoid unnecessary Revit API calls)

try:
    from .helpers.detail_drawing import draw_alignment as _debug_draw_alignment  # noqa: F401
except Exception:
    # Not available in unit-test context – ignore
    def _debug_draw_alignment(*_args, **_kwargs):  # type: ignore
        """Placeholder when helper module is unavailable."""

        return 
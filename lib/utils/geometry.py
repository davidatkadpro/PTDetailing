# -*- coding: utf-8 -*-
"""2-D geometry helper functions (IronPython-safe).

All functions operate on *iterables* of ``(x, y)`` tuples.  No external
libraries are required so the code runs inside IronPython 2.7 (pyRevit) as well
as CPython ≥3.6 for testing.

Implemented helpers:

* ``convex_hull(points)`` – returns hull vertices CCW using monotone-chain.
* ``centroid(points)`` – arithmetic mean of input vertices.
* ``hausdorff_distance(a, b)`` – symmetric Hausdorff distance between two
  point sets.
* ``translate(points, dx, dy)`` – generator yielding points translated by *dx*,
  *dy*.

# ---------------------------------------------------------------------------
# New helpers added Jul 2025 – rotation & bounds (needed for advanced alignment)
# ---------------------------------------------------------------------------

* ``rotate(points, angle_rad, origin=(0.0, 0.0))`` – generator yielding points
  rotated *angle_rad* around *origin*.
* ``poly_bounds(points)`` – returns axis-aligned bounding box of *points* as
  *(minX, maxX, minY, maxY)*.

# ---------------------------------------------------------------------------
# New helpers (Aug 2025)
# ---------------------------------------------------------------------------

* ``pt_in_convex(pt, hull)`` – returns True if *pt* is inside (or on edge of)
  the convex *hull*.
* ``directed_hausdorff_outside(a, hull)`` – directed Hausdorff distance from
  set *a* to convex *hull*.
"""

from __future__ import absolute_import, division

__all__ = [
    "convex_hull",
    "centroid",
    "hausdorff_distance",
    "translate",
    "rotate",
    "poly_bounds",
    "pt_in_convex",
    "directed_hausdorff_outside",
]

from math import sqrt, cos, sin


def _cross(o, a, b):
    """2-D cross product (OA × OB)."""

    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points):
    """Return the convex hull of *points* as a list of vertices (counter-clockwise)."""

    # Remove duplicates and sort lexicographically (x, then y)
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts

    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenate without duplicating first/last point
    return lower[:-1] + upper[:-1]


def centroid(points):
    """Return centroid (average) of *points*."""

    pts = list(points)
    if not pts:
        return (0.0, 0.0)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    n = float(len(pts))
    return (sx / n, sy / n)


def _point_distance(pa, pb):
    dx = pa[0] - pb[0]
    dy = pa[1] - pb[1]
    return sqrt(dx * dx + dy * dy)


def _directed_hausdorff(a, b):
    """Compute directed Hausdorff distance *h(a, b)* (one-way)."""

    if not a or not b:
        return 0.0
    max_min = 0.0
    for pa in a:
        min_d = min(_point_distance(pa, pb) for pb in b)
        if min_d > max_min:
            max_min = min_d
    return max_min


def hausdorff_distance(a, b):
    """Return symmetric Hausdorff distance between point sets *a* and *b*."""

    return max(_directed_hausdorff(a, b), _directed_hausdorff(b, a))


def translate(points, dx, dy):
    """Yield each point translated by *dx*, *dy*."""

    for x, y in points:
        yield (x + dx, y + dy)


def rotate(points, angle_rad, origin=(0.0, 0.0)):
    """Yield each *(x, y)* point rotated *angle_rad* around *origin*.

    Parameters
    ----------
    points      iterable of (x, y) tuples
    angle_rad   rotation angle **in radians** (counter-clockwise, XY-plane)
    origin      tuple (ox, oy) – rotation centre (default 0,0)
    """

    ox, oy = origin
    cos_a = cos(angle_rad)
    sin_a = sin(angle_rad)
    for x, y in points:
        # Translate to origin
        tx = x - ox
        ty = y - oy
        # Rotate
        rx = tx * cos_a - ty * sin_a
        ry = tx * sin_a + ty * cos_a
        # Translate back
        yield (rx + ox, ry + oy)


def poly_bounds(points):
    """Return axis-aligned bounding box of *points* as *(minX, maxX, minY, maxY)*.

    If *points* is empty, returns *(0, 0, 0, 0)*.
    """

    pts = list(points)
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)

    min_x = min(p[0] for p in pts)
    max_x = max(p[0] for p in pts)
    min_y = min(p[1] for p in pts)
    max_y = max(p[1] for p in pts)
    return (min_x, max_x, min_y, max_y)


def pt_in_convex(pt, hull):
    """Return True if *pt* is inside (or on edge of) the convex *hull*.

    *hull* must be a list of vertices in counter-clockwise order.
    The function uses a consistent cross-product sign check, which is
    O(N) and suitable for small hull sizes typical here.
    """

    if not hull or len(hull) < 3:
        return False

    x, y = pt
    sign = None
    n = len(hull)
    for i in range(n):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % n]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        # On edge counts as inside
        if abs(cross) < 1e-9:
            continue
        s = cross > 0.0
        if sign is None:
            sign = s
        elif sign != s:
            return False
    return True


def directed_hausdorff_outside(a, hull):
    """Directed Hausdorff distance from set *a* to convex *hull*.

    Only considers points of *a* lying *outside* the hull.  Points inside
    contribute zero.  Distance is approximated using vertex-to-vertex metric.
    """

    if not a or not hull:
        return 0.0

    outside_pts = [p for p in a if not pt_in_convex(p, hull)]
    if not outside_pts:
        return 0.0

    return _directed_hausdorff(outside_pts, hull) 
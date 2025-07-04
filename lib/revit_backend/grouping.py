# -*- coding: utf-8 -*-
"""Tendon grouping helpers.

This module clusters tendons that are effectively *the same* run so that we can
avoid drawing a leader and tag for every single identical tendon.

A *group* is defined by:
1. Direction ‒ tendons are parallel within ``ANGLE_TOL`` degrees.
2. Length ‒ absolute difference <= ``LENGTH_TOL`` feet.
3. Profile ‒ same number of internal drape points and each point pair has:
   • distance difference <= ``DIST_TOL`` ft
   • height difference   <= ``HEIGHT_TOL`` mm

All tolerances are configurable via module‐level constants or by passing explicit
kwargs to :func:`group_tendons`.
"""

from math import degrees, acos
from pyrevit import DB # type: ignore

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# New plan spacing tolerances (Aug 2025)
SPACING_TOL = 5.0  # feet – max perpendicular offset between adjacent tendons
SHIFT_TOL = 2.0    # feet – max longitudinal shift along tendon axis

# Retain old END_TOL for legacy callers but mark as deprecated
DIST_TOL = 0.5  # feet
HEIGHT_TOL = 5  # mm


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _direction(vec):
    """Return *normalised* direction vector (length = 1)."""
    mag = (vec.X ** 2 + vec.Y ** 2 + vec.Z ** 2) ** 0.5
    if mag == 0:
        return vec
    return DB.XYZ(vec.X / mag, vec.Y / mag, vec.Z / mag)


def _angle_between(v1, v2):
    """Return unsigned angle (degrees) between 2 vectors (0-180)."""
    v1n, v2n = _direction(v1), _direction(v2)
    dot = max(-1.0, min(1.0, v1n.DotProduct(v2n)))
    return degrees(acos(dot))


def _profiles_match(p1, p2, dist_tol, height_tol):
    if len(p1) != len(p2):
        return False
    for (d1, h1), (d2, h2) in zip(p1, p2):
        if abs(d1 - d2) > dist_tol:
            return False
        if abs(h1 - h2) > height_tol:
            return False
    return True


# helper for planar distance (ignores Z)
def _planar_dist(p1, p2):
    dx = p1.X - p2.X
    dy = p1.Y - p2.Y
    return (dx * dx + dy * dy) ** 0.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Main public API – returns list of groups.
def group_tendons(
    tendons,
    angle_tol=5.0,  # degrees
    length_tol=0.5,  # feet (~150 mm)
    dist_tol=0.5,  # feet
    height_tol=5,  # mm
    spacing_tol=5.0,  # feet
    shift_tol=2.0,  # feet
):
    """Return list of groups (each group is a list of tendons).

    The function is intentionally generic – it only relies on the **duck-type**
    surface of the tendon object: ``start``, ``end``, ``length`` and
    ``tendon_points`` (list of ``[distance_ft, height_mm]``).
    """

    ungrouped = list(tendons)
    groups = []

    while ungrouped:
        base = ungrouped.pop(0)
        base_dir = base.start - base.end  # type: ignore[attr-defined]
        base_len = getattr(base, "length", None)
        if base_len is None or base_len == 0:
            base_len = (base_dir.X ** 2 + base_dir.Y ** 2 + base_dir.Z ** 2) ** 0.5

        # Skip degenerate tendons with zero plan length to avoid div/0
        if base_len == 0:
            continue

        group = [base]

        # Iterate **copy** of list so we can remove while iterating
        for other in list(ungrouped):
            # 1. Direction check (parallel both orientations)
            ang = _angle_between(base_dir, other.start - other.end)  # type: ignore[attr-defined]
            if ang > 90:
                ang = 180 - ang  # account for reversed vectors (parallel opposite)
            if ang > angle_tol:
                continue

            # 2. Plan spacing checks – perpendicular offset and longitudinal shift
            # Compute perpendicular offset using cross-product magnitude
            diff_start = other.start - base.start  # type: ignore[attr-defined]
            offset = abs(diff_start.X * base_dir.Y - diff_start.Y * base_dir.X) / base_len
            if offset > spacing_tol:
                continue

            # Longitudinal shift (projection on tendon axis)
            shift = abs(diff_start.X * base_dir.X + diff_start.Y * base_dir.Y) / base_len
            if shift > shift_tol:
                continue

            # 3. Length check
            other_len = getattr(other, "length", None)
            if other_len is None or other_len == 0:
                vec_o = other.start - other.end  # type: ignore[attr-defined]
                other_len = (vec_o.X ** 2 + vec_o.Y ** 2 + vec_o.Z ** 2) ** 0.5

            if abs(base_len - other_len) > length_tol:
                continue

            # 4. Profile check
            if not _profiles_match(base.tendon_points, other.tendon_points, dist_tol, height_tol):
                continue

            # Passed all → same group
            ungrouped.remove(other)
            group.append(other)

        groups.append(group)

    return groups

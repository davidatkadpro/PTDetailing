# -*- coding: utf-8 -*-
"""Domain models for tendon data parsed from INDUCTA PTD export files.

These models are **Revit-agnostic** and expressed in SI units (millimetres).

The file supports both modern CPython (3.7+, with `dataclasses`) *and*
IronPython 2.7, which lacks them.  We therefore define two implementations:

• **CPython ≥3.7** – Uses real `@dataclass` definitions so that equality,
  reprs, etc. behave as expected for tests.
• **Legacy / IronPython 2.7** – Fallback plain-old Python classes providing
  the same public attributes and helper methods.
"""

from __future__ import absolute_import, division, print_function

import sys

# ---------------------------------------------------------------------------
# Modern implementation (preferred)
# ---------------------------------------------------------------------------

if sys.version_info >= (3, 7):
    # On modern CPython, import the rich dataclass implementation.
    from ._models_py3 import TendonPoint, TendonData, TendonSet  # type: ignore

# ---------------------------------------------------------------------------
# Legacy fallback for IronPython 2.7 (no dataclasses, no type annotations)
# ---------------------------------------------------------------------------

else:

    class TendonPoint(object):
        # Simple container for a profile point along a tendon.

        def __init__(self, distance_mm, height_mm):
            # type: (float, int) -> None
            self.distance_mm = distance_mm
            self.height_mm = height_mm

        # Provide nice representation for debugging (not critical).
        def __repr__(self):
            return "TendonPoint(distance_mm=%r, height_mm=%r)" % (
                self.distance_mm,
                self.height_mm,
            )


    class TendonData(object):
        # Main tendon record extracted from a PTD export.

        def __init__(
            self,
            id,  # noqa: A002 – shadowing built-in allowed here
            length_mm,
            start_xy_mm,
            end_xy_mm,
            tendon_type,
            strand_type,
            strand_count,
            start_type=1,
            end_type=3,
        ):
            # type: (int, float, tuple, tuple, int, float, int, int, int) -> None
            self.id = id
            self.length_mm = length_mm
            self.start_xy_mm = start_xy_mm
            self.end_xy_mm = end_xy_mm
            self.tendon_type = tendon_type
            self.strand_type = strand_type
            self.strand_count = strand_count
            self.start_type = int(start_type)
            self.end_type = int(end_type)
            self.points = []

        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------

        def add_point(self, point):
            # type: (TendonPoint) -> None
            self.points.append(point)

        # Basic dunder methods for usability --------------------------------

        def __repr__(self):
            return (
                "TendonData(id=%r, length_mm=%r, strand_count=%r, points=%d)"
                % (self.id, self.length_mm, self.strand_count, len(self.points))
            )


    class TendonSet(object):
        # Container for multiple tendons.

        def __init__(self, tendons=None):
            # type: (list) -> None
            self.tendons = list(tendons) if tendons else []

        def append(self, tendon):
            # type: (TendonData) -> None
            self.tendons.append(tendon)

        # Collection protocol helpers --------------------------------------

        def __iter__(self):
            return iter(self.tendons)

        def __len__(self):
            return len(self.tendons) 
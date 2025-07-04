# -*- coding: utf-8 -*-
"""Functions for parsing INDUCTA PTD export text files.

Format (example excerpt)::

    Tendon No. 1
    Length :  12.345m
    End Point co-orinates, start: ( 100.0, 200.0 ) end: ( 300.0, 200.0 )
    Type    : 1
    Type of strands : 12.7
    Number of strands : 3
    No.,    L:5mm,    H:5mm,    Rs,    Rh
    1,      0.000,    0.000,    0.000,  0.000
    2,      3.500,    0.025,    0.000,  0.000
    ...

The exact delimiter usage can vary slightly; we strip whitespace and rely on
presence of sentinel headings.
"""

# NOTE: Removed unsupported __future__ import for IronPython 2.7 compatibility

import re
# pylint: disable=import-error
from pathlib import Path
try:
    from typing import List, Optional  # type: ignore
except ImportError:  # pragma: no cover – IronPython 2.7 fallback
    List = list  # type: ignore
    class _Optional(object):
        """Stand-in for typing.Optional (no runtime effect)."""

    Optional = _Optional  # type: ignore

from .models import TendonData, TendonPoint, TendonSet
from .exceptions import PTDParsingError


_HEADER_TENDON_NO = re.compile(r"^Tendon No\.\s*(\d+)")
_HEADER_LENGTH = re.compile(r"^Length\s*:\s*(\d+\.\d+)m")
_HEADER_COORDS = re.compile(
    r"^End Point co-orinates.*start:\s*\(([^)]+)\)\s*end:\s*\(([^)]+)\)",
    re.IGNORECASE,
)
_HEADER_TENDON_TYPE = re.compile(r"^Type\s*:\s*(\d+)")
_HEADER_STRAND_TYPE = re.compile(r"^Type of strands\s*:\s*([\d\.]+)")
_HEADER_STRAND_NO = re.compile(r"^Number of strands\s*:\s*(\d+)")
_HEADER_START = re.compile(r"^Start\s*:\s*(Live End|Dead End)", re.IGNORECASE)
_HEADER_END = re.compile(r"^End\s*:\s*(Live End|Dead End)", re.IGNORECASE)
_TABLE_ROW = re.compile(r"^(\d+),\s*([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)")
_TABLE_START = re.compile(r"No\.,", re.IGNORECASE)


MM_PER_M = 1000.0


def _float_mm(val):  # type: (str) -> float
    """Convert value in metres to millimetres (float)."""

    return float(val) * MM_PER_M


def _coord_pair(raw):  # type: (str) -> tuple
    x_str, y_str = (c.strip() for c in raw.split(","))
    return float(x_str) * MM_PER_M, float(y_str) * MM_PER_M


def parse_ptd_file(path):  # type: (str) -> TendonSet
    """Parse a PTD export text file and return a TendonSet."""

    path = Path(path)
    if not path.exists():
        raise PTDParsingError("File not found: {}".format(path))

    tendons = []  # type: List[TendonData]
    tendon = None  # type: Optional[TendonData]
    in_table = False

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue

            match = _HEADER_TENDON_NO.match(line)
            if match:
                if tendon:
                    tendons.append(tendon)
                tendon_id = int(match.group(1))
                tendon = TendonData(
                    id=tendon_id,
                    length_mm=0,
                    start_xy_mm=(0, 0),
                    end_xy_mm=(0, 0),
                    tendon_type=0,
                    strand_type=0.0,
                    strand_count=0,
                )
                in_table = False
                continue

            if tendon is None:
                # ignore lines before first tendon header
                continue

            match = _HEADER_LENGTH.match(line)
            if match:
                tendon.length_mm = _float_mm(match.group(1))
                continue

            match = _HEADER_COORDS.match(line)
            if match:
                tendon.start_xy_mm = _coord_pair(match.group(1))
                tendon.end_xy_mm = _coord_pair(match.group(2))
                continue

            match = _HEADER_TENDON_TYPE.match(line)
            if match:
                tendon.tendon_type = int(match.group(1))
                continue

            match = _HEADER_STRAND_TYPE.match(line)
            if match:
                tendon.strand_type = float(match.group(1))
                continue

            match = _HEADER_STRAND_NO.match(line)
            if match:
                tendon.strand_count = int(match.group(1))
                continue

            match = _HEADER_START.match(line)
            if match:
                is_live = "live" in match.group(1).lower()
                if is_live:
                    tendon.start_type = 3 if tendon.tendon_type == 2 else 1
                else:
                    tendon.start_type = 2  # Dead End
                continue

            match = _HEADER_END.match(line)
            if match:
                is_live = "live" in match.group(1).lower()
                if is_live:
                    tendon.end_type = 3 if tendon.tendon_type == 2 else 1
                else:
                    tendon.end_type = 2  # Dead End
                continue

            if _TABLE_START.search(line):
                in_table = True
                continue

            if in_table:
                row_match = _TABLE_ROW.match(line)
                if row_match:
                    _, dist_str, _h_raw, h5_str = row_match.groups()
                    point = TendonPoint(
                        distance_mm=_float_mm(dist_str),
                        height_mm=int(float(h5_str) * MM_PER_M),
                    )
                    tendon.add_point(point)
                else:
                    # End of table for current tendon
                    in_table = False

    if tendon:
        tendons.append(tendon)

    return TendonSet(tendons) 
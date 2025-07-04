"""Adapter converting `ptd_parser` models into existing legacy `TendonSet`.

This keeps new parsing logic separated from Revit placement code while we
refactor progressively.
"""
# -*- coding: utf-8 -*-

# Revit API stubs / runtime
from pyrevit import DB

# Internal imports
from ptd_parser import parse_ptd_file, TendonData
from Tendon import Tendon
from TendonSet import TendonSet
from utils.conversions import mm_to_ft


def _convert_td(td):
    """Convert TendonData -> legacy Tendon object (Revit units = ft)."""

    t = Tendon(ID=td.id)
    t.length = mm_to_ft(td.length_mm)
    t.start = DB.XYZ(mm_to_ft(td.start_xy_mm[0]), mm_to_ft(td.start_xy_mm[1]), 0)
    t.end = DB.XYZ(mm_to_ft(td.end_xy_mm[0]), mm_to_ft(td.end_xy_mm[1]), 0)
    t.tendon_type = td.tendon_type
    t.strand_type = td.strand_type
    t.strand_no = td.strand_count
    t.start_type = td.start_type
    t.end_type = td.end_type
    # points list [[distance_ft, height_mm]]
    t.tendon_points = [[mm_to_ft(p.distance_mm), int(p.height_mm)] for p in td.points]
    return t


def load_tendons_from_ptd(file_path):
    """Parse file and return TendonSet compatible with existing writer."""

    parsed_set = parse_ptd_file(file_path)
    legacy_set = TendonSet()
    for td in parsed_set:
        legacy_set.append(_convert_td(td))
    return legacy_set 
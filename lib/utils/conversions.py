"""Unit conversion helpers shared across modules.

Revit's internal length unit is *decimal feet*; project data from PTD is in
metres or millimetres. Keep all helpers in one place to avoid magic numbers.
"""

# Constants
FT_PER_MM = 1.0 / 304.8  # 1 mm in feet
MM_PER_FT = 304.8

FT_PER_M = 3.280839895
M_PER_FT = 1 / FT_PER_M

MM_PER_M = 1000.0
M_PER_MM = 1 / MM_PER_M


def mm_to_ft(mm):
    """Convert millimetres to Revit decimal feet."""
    return mm * FT_PER_MM


def ft_to_mm(ft):
    return ft * MM_PER_FT


def m_to_ft(m):
    return m * FT_PER_M


def ft_to_m(ft):
    return ft * M_PER_FT 
"""Revit-specific adapter layer for PTDetailing.

All modules in this package MAY import Revit API (pyRevit `DB`, `revit` objects).
They should convert pure-python tendon models (from `ptd_parser`) into Revit
FamilyInstances, tags, groups, etc.
"""

# re-export convenience API after renaming constants
from .families import (  # noqa: F401 (re-export)
    get_family_symbol,
    get_tendon_symbol,
    get_leader_symbol,
    get_drape_symbol,
) 
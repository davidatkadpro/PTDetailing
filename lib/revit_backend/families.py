# -*- coding: utf-8 -*-
"""Family resolution and lazy-loading utilities for PTDetailing.

This module centralises lookup and loading of the Revit families used by the
extension so that other code can simply ask for a given family type without
worrying whether it has been loaded into the active document.  A small in-memory
cache avoids duplicate look-ups which is particularly useful inside pyRevit
where multiple commands may run within the same Revit session.

NOTE: This code targets *pyRevit* (IronPython 2.7) at runtime but is authored
in modern CPython syntax for tooling/CI.  Avoid features unsupported by
IronPython (e.g., f-strings with '=' or dataclasses).
"""
# NOTE: __future__ annotations not supported by IronPython 2.7 used by pyRevit

# built-ins
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Revit API – must be available (extension runs inside Revit)
# ---------------------------------------------------------------------------

try:
    from pyrevit import DB, revit, script  # type: ignore
except ImportError as exc:
    # The extension should only be executed inside Revit / pyRevit; fail fast
    raise ImportError("pyRevit API not available – PTDetailing must run inside Revit.")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

from .settings import load as load_settings


# Symbol names (types) inside the family files.
TENDON_SYMBOL = "12.7"
LEADER_SYMBOL = "Max Centres"
DRAPE_MID_SYMBOL = "Drape (Left Middle)"
DRAPE_START_SYMBOL = "Drape (Start)"
DRAPE_END_SYMBOL = "Drape (End)"
TAG_SYMBOL = "Strand Count Only"

# --- DEPRECATED CONSTANTS (kept for backward compatibility) ---
DEFAULT_TENDON_FAMILY = os.getenv(
    "PTD_TENDON_FAMILY",
    "3Daro_PT_Tendon_Plan_001.rfa"
)
DEFAULT_LEADER_FAMILY = os.getenv(
    "PTD_LEADER_FAMILY",
    "3Daro_PT_Tendon_Leader_Plan_001.rfa"
)
DEFAULT_DRAPE_FAMILY = os.getenv(
    "PTD_DRAPE_FAMILY",
    "3Daro_PT_Tendon_Drape_Plan_001.rfa"
)
DEFAULT_TAG_FAMILY = os.getenv(
    "PTD_TAG_FAMILY",
    "3Daro_PT_Tendon_Tag_Plan_001.rfa"
)
# --- End DEPRECATED ---


# Mapping of family names to their default internal symbol name.
# Used by ensure_families to check if everything is loaded.
_REQUIRED_FAMILIES = {
    # Populated dynamically from settings at runtime
}


# Where family files live relative to the extension root.  We assume the
# repo layout keeps .rfa assets next to pyRevit bundles, e.g.
# PTDetailing.extension/
# ├─ families/
# │    └─ <family>.rfa
_EXTENSION_ROOT = Path(__file__).resolve().parents[2]
_FAMILY_DIR = _EXTENSION_ROOT / "content"

# In-memory cache {(family_name, symbol_name): FamilySymbol}
_cache = {}

# ---------------------------------------------------------------------------
# Required families & 3Daro_ID mapping
# ---------------------------------------------------------------------------

# Map of family filename -> expected 3Daro_ID parameter value
REQUIRED_FAMILIES = {
    DEFAULT_TENDON_FAMILY: "3DPT001.001",
    DEFAULT_LEADER_FAMILY: "3DPT002.001",
    DEFAULT_DRAPE_FAMILY: "3DPT003.001",
    DEFAULT_TAG_FAMILY: "3DPT004.001",
}

# Default symbol name inside the leader family (for grouped tendons)
LEADER_SYMBOL_NAME = os.getenv("PTD_LEADER_SYMBOL", "Max Centres")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_family_symbol(doc, family_name, symbol_name=None):
    """Return (and load if necessary) the *FamilySymbol* requested.

    If *symbol_name* is *None* the first symbol in the family is returned.
    Raises *ValueError* if the family or symbol cannot be found.
    """

    key = (family_name, symbol_name)
    if key in _cache:
        return _cache[key]

    # Try to find already-loaded symbol first
    symbol = _find_symbol_in_doc(doc, family_name, symbol_name)
    if symbol is None:
        # Not loaded yet → attempt to load family file
        _load_family(doc, family_name)
        symbol = _find_symbol_in_doc(doc, family_name, symbol_name)

    if symbol is None:
        raise ValueError("Family symbol not found: {} :: {}".format(family_name, symbol_name))

    _cache[key] = symbol
    return symbol


def get_tendon_symbol(doc):
    """Return the main *Tendon* detail component symbol."""

    cfg = load_settings()
    family_name = cfg.get("tendon_family", DEFAULT_TENDON_FAMILY)
    return get_family_symbol(doc, family_name, TENDON_SYMBOL)


def get_leader_symbol(doc):
    """Return the *Leader* detail component symbol (defaults to 'Max Centres')."""

    cfg = load_settings()
    family_name = cfg.get("leader_family", DEFAULT_LEADER_FAMILY)
    return get_family_symbol(doc, family_name, LEADER_SYMBOL)


def get_drape_symbol(doc):
    """Convenience wrapper for the *Drape* family symbol."""

    return get_family_symbol(doc, DEFAULT_DRAPE_FAMILY)


def get_tag_symbol(doc, symbol_name=None):
    """Return FamilySymbol for the tag family defined in settings."""
    cfg = load_settings()
    family_name = cfg.get("tag_family", DEFAULT_TAG_FAMILY)
    return get_family_symbol(doc, family_name, symbol_name)


def get_drape_symbols(doc):
    """Return tuple (mid_sym, start_sym, end_sym) for drape family."""

    cfg = load_settings()
    family_name = cfg.get("drape_family", DEFAULT_DRAPE_FAMILY)
    mid = get_family_symbol(doc, family_name, DRAPE_MID_SYMBOL)
    start = get_family_symbol(doc, family_name, DRAPE_START_SYMBOL)
    end = get_family_symbol(doc, family_name, DRAPE_END_SYMBOL)

    return mid, start, end

# ---------------------------------------------------------------------------
# Public helper – bulk ensure
# ---------------------------------------------------------------------------

def ensure_families(doc):
    """Check for all required families and try to load any that are missing.

    Returns True if all families are present, False otherwise.
    """
    # Dynamically populate from settings on each call
    cfg = load_settings()
    _REQUIRED_FAMILIES.clear()
    _REQUIRED_FAMILIES[cfg.get("tendon_family")] = TENDON_SYMBOL
    _REQUIRED_FAMILIES[cfg.get("leader_family")] = LEADER_SYMBOL
    _REQUIRED_FAMILIES[cfg.get("drape_family")] = DRAPE_MID_SYMBOL  # Check one is enough
    _REQUIRED_FAMILIES[cfg.get("tag_family")] = TAG_SYMBOL  # Tag is just family name

    loaded_families = {f.Name for f in DB.FilteredElementCollector(doc).OfClass(DB.Family)}
    missing = []
    required_filenames = _REQUIRED_FAMILIES.keys()

    for fname in required_filenames:
        # The family name inside the RFA does not include the extension.
        internal_name = fname.replace(".rfa", "")
        if internal_name not in loaded_families:
            missing.append(fname)

    if not missing:
        return True

    # Try to load missing families from default content folder
    content_path = script.get_bundle_file("content")
    if not content_path or not os.path.isdir(content_path):
        return False  # Cannot find content folder to load from

    with revit.Transaction("Load PTDetailing Families"):
        for fname in missing:
            fpath = os.path.join(content_path, fname)
            if os.path.exists(fpath):
                try:
                    doc.LoadFamily(fpath)
                except Exception:
                    pass  # Fail silently, check will run again below

    # Final check after attempting to load
    loaded_families = {f.Name for f in DB.FilteredElementCollector(doc).OfClass(DB.Family)}
    for fname in required_filenames:
        internal_name = fname.replace(".rfa", "")
        if internal_name not in loaded_families:
            return False

    return True

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_symbol_in_doc(doc, family_name, symbol_name):
    """Search the document for the requested symbol."""

    target_name = Path(family_name).stem  # family names in Revit exclude .rfa
    collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
    for symbol in collector:  # type: DB.FamilySymbol
        fam = getattr(symbol, "Family", None)
        if not fam:
            continue
        try:
            if fam.Name != target_name:
                continue
        except AttributeError:
            print("--- PTDetailing Debug ---")
            print("A FamilySymbol with a malformed .Family property was found.")
            try:
                print("Symbol causing error: {}".format(symbol.Name))
            except Exception:
                print("Symbol causing error has no .Name property.")
            print("Family object type: {}".format(type(fam)))
            print("-------------------------")
            continue
        sym_name = _sym_name(symbol)
        if symbol_name is None or sym_name == symbol_name:
            return symbol
    return None


def _load_family(doc, family_name):
    """Load the given family into *doc* if the .rfa exists on disk."""

    fam_path = _FAMILY_DIR / family_name
    if not fam_path.exists():
        raise ValueError("Family file not found on disk: {}".format(fam_path))

    t = DB.Transaction(doc, "Load {}".format(family_name))
    t.Start()
    try:
        doc.LoadFamily(str(fam_path))
    finally:
        t.Commit()

    # Return success boolean so caller can decide.
    return _find_symbol_in_doc(doc, family_name, None) is not None

# ---------------------------------------------------------------------------
# Internal helpers – extended
# ---------------------------------------------------------------------------

def _family_in_document(doc, family_name, expected_id):
    """Return *True* if any loaded symbol matches *family_name* or 3Daro_ID."""

    target_name = Path(family_name).stem  # family names in Revit exclude .rfa
    collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
    for symbol in collector:  # type: DB.FamilySymbol
        fam = getattr(symbol, "Family", None)
        if not fam:
            continue
        try:
            fam_name = fam.Name
        except AttributeError:
            # Malformed family object – skip
            continue

        # Match by family file name (without extension) or by 3Daro_ID parameter
        if fam_name == target_name:
            return True

        # Shared parameter lookup (may exist on symbol or family)
        for elem in (symbol, fam):
            param = elem.LookupParameter if hasattr(elem, "LookupParameter") else None
            if param:
                p = param("3Daro_ID")
                if p and p.AsString() == expected_id:
                    return True

    return False

def _prompt_missing_families(missing):
    """Display an alert listing *missing* family filenames.

    Safe no-op in non-Revit environments.
    """

    try:
        from pyrevit import forms  # type: ignore

        msg_lines = [
            "The following required families were not found in the project "
            "and could not be auto-loaded:",
            "",
        ] + [" • {}".format(n) for n in missing] + ["", "Please load them manually and re-run the command."]

        forms.alert("\n".join(msg_lines), ok=True, title="PTDetailing – Missing Families")
    except Exception:  # noqa: BLE001
        # In unit tests or CI just print – avoids crashing.
        print("[PTDetailing] Missing families: {}".format(", ".join(missing)))

# ---------------------------------------------------------------------------
# Helper – robust symbol name accessor (handles IronPython quirks)
# ---------------------------------------------------------------------------

def _sym_name(elem):
    """Return element name using fallback accessor for IronPython."""

    try:
        return elem.Name  # standard
    except Exception:
        try:
            return DB.Element.Name.__get__(elem)  # fallback accessor
        except Exception:
            return None

# ---------------------------------------------------------------------------
# End of file
# --------------------------------------------------------------------------- 
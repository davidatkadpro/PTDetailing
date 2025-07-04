# -*- coding: utf-8 -*-
"""Project settings persistence helper for PTDetailing.

Uses *pyRevit* `script.get_project_settings()` which stores data inside the
Revit document (DataStorage element).  Settings therefore travel with the
project file and are available to all users.

The settings payload is a JSON string stored against a single key so we can
version/extend it in future without cluttering the project settings store.
"""
# -*- coding: utf-8 -*-
import json

try:
    from pyrevit import script  # type: ignore
except ImportError:  # during unit tests
    script = None  # type: ignore

_KEY = "PTDetailing.Settings"

_DEFAULTS = {
    # Families
    "tendon_family": "3Daro_PT_Tendon_Plan_001.rfa",
    "leader_family": "3Daro_PT_Tendon_Leader_Plan_001.rfa",
    "drape_family": "3Daro_PT_Tendon_Drape_Plan_001.rfa",
    "tag_family": "3Daro_PT_Tendon_Tag_Plan_001.rfa",
    # Tagging
    "drape_tags": True,
    "drape_end_tags": False,
    "tag_tendon_strands": True,
    # Grouping
    "group_tendons": True,
    "create_detail_group": True,
    "group_angle_tol_deg": 5.0,
    "group_length_tol_mm": 200.0,
    "group_spacing_tol_mm": 1500.0,
    "group_shift_tol_mm": 600.0,
    "group_drape_dist_tol_mm": 200.0,
    "group_drape_height_tol_mm": 5,
    "pan_stressed_end_offset_mm": 1000,
    # Snapping
    "auto_snap_ends": True,
    "auto_snap_tolerance_mm": 50,
    # Misc
    "units": "mm",  # options: mm | ft
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


# Minimal in-memory stand-in used during unit-tests or when running inside
# environments that expose an older pyRevit build lacking the
# `script.get_project_settings` utility (e.g. IronPython 2.7 inside Revit 2017
# with pyRevit ≤ 4.8.9).


class _FallbackStore(dict):
    """Dict that mimics the pyRevit settings store API (get / set)."""

    def get(self, key, default=None):  # type: ignore[override]
        # IronPython (Python 2.7) does **not** support the zero-arg ``super()``
        # form available in CPython 3.  Use an explicit base-class reference.
        return dict.get(self, key, default)

    def set(self, key, value):  # noqa: D401 – simple setter
        self[key] = value


class _StoreDataWrapper(object):
    """Wrapper for older pyRevit store_data/load_data API."""

    def get(self, key, default=None):
        # load_data does not have a default arg; return None if not found
        try:
            return script.load_data(key)
        except Exception:
            return default

    def set(self, key, value):
        script.store_data(key, value)


_FALLBACK_STORE = _FallbackStore()


def _get_store():
    """Return a key-value store living on the Revit document (preferred).

    Falls back to an in-memory dict when the current pyRevit version does not
    provide ``script.get_project_settings`` (older releases) or when the code
    is executed outside the Revit/pyRevit context (unit tests).
    """

    if script is None:
        # Not running inside Revit (e.g. pytest) – use dummy store.
        return _FALLBACK_STORE

    # Newer pyRevit versions expose the helper we actually want.
    if hasattr(script, "get_project_settings"):
        return script.get_project_settings()

    # This version seems to be what the user has
    if hasattr(script, "store_data") and hasattr(script, "load_data"):
        return _StoreDataWrapper()

    # Older pyRevit < 4.8 fall back to document‐level data if available.
    if hasattr(script, "get_document_data"):
        return script.get_document_data()

    # Last-ditch fallback – in-memory only (won't persist between sessions).
    return _FALLBACK_STORE


def load():
    """Return settings dict merged onto defaults."""

    store = _get_store()
    raw = store.get(_KEY)
    if raw:
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
    else:
        data = {}
    merged = _DEFAULTS.copy()
    # Use .update for py2 compatibility (dict unpacking supported only py3.5+)
    merged.update(data)
    return merged


def save(data):
    """Persist *data* (dict) into project settings store."""

    store = _get_store()
    payload = json.dumps(data)
    store.set(_KEY, payload) 
# -*- coding: utf-8 -*-
"""PTD export file parsing utilities.

This package provides:
- dataclass models representing tendon data
- parser functions to read PTD text exports
- helper functions / exceptions

The package is CPython-only and contains **no Revit API calls**, so it can be
tested head-less with pytest.
"""

# ---------------------------------------------------------------------------
# Safe import of "importlib.metadata" across different Python versions.
# - CPython >=3.8  : stdlib "importlib.metadata" is available.
# - CPython <3.8  : backport package "importlib_metadata" can be installed.
# - IronPython 2.x: neither is guaranteed to exist, so we fall back to a
#   minimal fake implementation that satisfies the attributes we use.
# ---------------------------------------------------------------------------

try:
    # 1. Prefer the dedicated back-port if present (works on older Pythons).
    import importlib_metadata as metadata  # type: ignore
except Exception:  # pragma: no cover - package not installed or other import issues
    try:
        # 2. Try the standard library variant (Python >=3.8).
        from importlib import metadata as metadata  # type: ignore
    except Exception:
        # 3. Final fall-back for IronPython 2.7 or very old interpreters.
        class _FakeMetadata(object):
            """Minimal stub mimicking the subset of importlib.metadata used here."""

            class PackageNotFoundError(Exception):
                pass

            @staticmethod
            def version(name):  # noqa: D401 - simple stub
                """Always raise PackageNotFoundError – no distribution metadata."""
                raise _FakeMetadata.PackageNotFoundError()

        metadata = _FakeMetadata()  # type: ignore

__all__ = [
    "parse_ptd_file",
    "TendonPoint",
    "TendonData",
    "TendonSet",
    "PTDParsingError",
]

try:
    __version__ = metadata.version("ptd-parser")  # type: ignore[attr-defined]
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

from .models import TendonPoint, TendonData, TendonSet  # noqa: E402
from .parser import parse_ptd_file  # noqa: E402
from .exceptions import PTDParsingError  # noqa: E402 
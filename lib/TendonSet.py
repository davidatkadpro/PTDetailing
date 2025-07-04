# -*- coding: utf-8 -*-
"""Legacy placeholder mapping to the consolidated implementation.

This module forwards the `TendonSet` class from *example_lib.TendonSet* to the
historic import path so that legacy pyRevit scripts importing
``from TendonSet import TendonSet`` continue to work.
"""

import os, sys

_EXT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _EXT_ROOT not in sys.path:
    sys.path.append(_EXT_ROOT)

try:
    from example_lib.TendonSet import TendonSet  # type: ignore  # noqa: F401
except ImportError:
    from example_lib import TendonSet  # type: ignore  # noqa: F401

__all__ = ["TendonSet"]

# (legacy runtime code removed) 
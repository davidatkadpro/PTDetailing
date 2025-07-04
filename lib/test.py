# -*- coding: utf-8 -*-
"""Compatibility shim so that `from test import do_import` (used by old
Import button script) resolves even after code reorganisation.

It simply re-exports everything from *example_lib.test*.
"""

import os
import sys

_EXT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _EXT_ROOT not in sys.path:
    sys.path.append(_EXT_ROOT)

from example_lib import test as _impl  # noqa: F401

# Re-export public names
for _name in getattr(_impl, "__all__", dir(_impl)):
    globals()[_name] = getattr(_impl, _name)

del _name, _impl, os, sys, _EXT_ROOT 
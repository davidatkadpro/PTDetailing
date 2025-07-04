# -*- coding: utf-8 -*-
"""Wrapper inside *lib* so that `import Tendon` works when 'lib' folder is on sys.path.

Delegates to main implementation in *example_lib.Tendon*.
"""

# Ensure extension root (parent of this file's directory) is on sys.path so
# that the *example_lib* package can be imported even when pyRevit only adds
# the *lib* directory to sys.path.

import os
import sys

_EXT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _EXT_ROOT not in sys.path:  # pragma: no cover – runtime safeguard
    sys.path.append(_EXT_ROOT)

# Import the canonical implementation.
try:
    from example_lib.Tendon import Tendon  # type: ignore  # noqa: F401
except ImportError:  # package found but submodule not imported yet
    # Fallback to attribute exported by package __init__ (IronPython quirk)
    from example_lib import Tendon  # type: ignore  # noqa: F401

__all__ = ["Tendon"] 
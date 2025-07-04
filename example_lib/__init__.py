# -*- coding: utf-8 -*-
"""Legacy helper package containing the original Tendon / TendonSet classes.

This file turns *example_lib* into a real Python package so that IronPython 2.7
can import it (Python-2 requires an ``__init__.py``).  It re-exports the two
classes so callers can simply write ``from example_lib import Tendon``.
"""

from .Tendon import Tendon  # noqa: F401
from .TendonSet import TendonSet  # noqa: F401

__all__ = ["Tendon", "TendonSet"] 
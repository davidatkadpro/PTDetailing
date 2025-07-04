"""Drape profile writer for PTDetailing.

Creates Detail Lines (plan view) representing the tendon drape profile between
anchor points.  For now we work in the active view and assume a *plan* view
where Z = 0.  Z-offsets from tendon points are stored as elevations on the
curve via Z coordinates so that vertical curvature can be inferred for
scheduling later.  Future work may replace Detail Lines with native Revit
Tendon elements when API matures.
"""
# -*- coding: utf-8 -*-

from types import SimpleNamespace

# Unit conversions
from utils.conversions import mm_to_ft

# ---------------------------------------------------------------------------
# Revit API bindings (pyRevit at runtime, stubs otherwise)
# ---------------------------------------------------------------------------

try:
    from pyrevit import DB, revit  # type: ignore
except ImportError:  # pragma: no cover – during unit tests / pure-python
    try:
        from revit_stubs import DB, revit  # type: ignore
    except ImportError:
        class _StubXYZ(SimpleNamespace):
            def __sub__(self, other):
                return _StubXYZ(X=self.X - other.X, Y=self.Y - other.Y, Z=self.Z - other.Z)

            def __init__(self, X=0.0, Y=0.0, Z=0.0):  # noqa: N803
                super().__init__(X=X, Y=Y, Z=Z)

        class _StubLine:
            @staticmethod
            def CreateBound(p1, p2):
                return (p1, p2)

        class _StubTransaction:
            def __init__(self, doc, name):
                self.doc, self.name = doc, name

            def Start(self):
                pass

            def Commit(self):
                pass

        class _StubCreate:
            def __init__(self, doc):
                self.doc = doc

            def NewDetailCurve(self, view, line):
                self.doc._created.append(line)
                return SimpleNamespace(Id=len(self.doc._created))

        class _StubDocument(SimpleNamespace):
            def __init__(self):
                super().__init__()
                self._created = []
                self.ActiveView = SimpleNamespace()
                self.Create = _StubCreate(self)

        class _StubList(list):
            pass

        DB = SimpleNamespace(  # type: ignore
            XYZ=_StubXYZ,
            Line=_StubLine,
            Transaction=_StubTransaction,
            List=_StubList,
        )

        revit = SimpleNamespace()  # type: ignore

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def write_drape(doc, tendon, view=None):
    """Generate a polyline DetailCurve drape for *tendon*.

    Parameters
    ----------
    doc     Revit document
    tendon  Legacy Tendon object with .start/.end XYZ (ft) and .tendon_points
            list of [distance_ft, height_mm] pairs measured from the start.
    view    Target view; defaults to `doc.ActiveView`.
    Returns list of created ElementIds (one per segment).
    """

    if view is None:
        view = doc.ActiveView

    # Build XYZ list along straight line between start and end based on horizontal fraction
    vec = tendon.end - tendon.start  # XYZ subtraction gives vector
    total_horiz = (vec.X ** 2 + vec.Y ** 2) ** 0.5

    points_xyz = [tendon.start]
    for dist_ft, height_mm in tendon.tendon_points:
        ratio = dist_ft / total_horiz if total_horiz else 0
        x = tendon.start.X + vec.X * ratio
        y = tendon.start.Y + vec.Y * ratio
        z = mm_to_ft(height_mm)  # height from soffit; simplified as absolute Z
        points_xyz.append(DB.XYZ(x, y, z))
    points_xyz.append(tendon.end)

    created = []
    t = DB.Transaction(doc, "Write PT Drape")
    t.Start()
    try:
        for p1, p2 in zip(points_xyz[:-1], points_xyz[1:]):
            line = DB.Line.CreateBound(p1, p2)
            curve = doc.Create.NewDetailCurve(view, line)
            created.append(curve.Id)
    finally:
        t.Commit()

    return created 
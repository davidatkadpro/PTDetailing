# -*- coding: utf-8 -*-
from pyrevit import DB, revit

TARGET_FAMILY = "3Daro_PT_Tendon_Drape_Plan_001"
doc = revit.doc

print("Scanning symbols …")
collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)

for sym in collector:
    fam = getattr(sym, "Family", None)
    # Skip symbols that are not from the drape family
    if fam and getattr(fam, "Name", None) != TARGET_FAMILY:
        continue

    print("- Symbol ElementId:", sym.Id.IntegerValue)

    # Try to show symbol name
    try:
        print("   Symbol name :", sym.Name)
    except Exception as e:
        print("   Symbol name : <error> (%s)" % e)

    # Try to show family name
    if fam:
        try:
            print("   Family name :", fam.Name)
        except Exception as e:
            print("   Family name : <error> (%s)" % e)
    else:
        print("   Family object is None")

print("…done")
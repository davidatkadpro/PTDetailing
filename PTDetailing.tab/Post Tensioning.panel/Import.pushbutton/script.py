# -*- coding: utf-8 -*-
"""Import PT Tendons from PTD export with zero-click workflow.

Workflow:
1. Ask user to pick `.txt` PTD export file.
2. Call `revit_backend.importer.import_ptd_file` which:
   – Ensures families, parses file, auto-aligns, snaps ends, creates elements.
3. Report result to user.
"""

from __future__ import absolute_import

import sys
import os

from pyrevit import revit, DB, forms  # type: ignore

from revit_backend.importer import import_ptd_file  # type: ignore

# Add 'lib' directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))


def main():
	doc = revit.doc

	# 1. Get PTD file path from user
	ptd_file = forms.pick_file(title="Select PTD Export File")
	if not ptd_file:
		return  # user cancelled

	# 2. Run the importer
	try:
		count = import_ptd_file(doc, ptd_file, revit.active_view)
		if count is not None:
			forms.alert(
				"Successfully imported {} elements.".format(count),
				title="Import Complete",
			)
	except Exception as e:
		forms.alert(
			"An unexpected error occurred during import:\n{}".format(e),
			title="Import Failed",
			warn_icon=True,
		)


if __name__ == "__main__":
	main()

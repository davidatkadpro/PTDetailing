# PTDetailing Refactor Roadmap

> This document reflects the project's state after the major refactoring and feature additions.

---

## Phase 1 – Core Domain Extraction & Revit Backend
**Status: ✅ COMPLETE**
1.  **`ptd_parser` Package Creation:** **✅**
    *   `models.py`: Defines `TendonData`, `TendonPoint`, `TendonSet` with IronPython 2.7 compatibility.
    *   `parser.py`: Handles parsing of PTD text export into the domain models.
    *   `exceptions.py`: Custom exceptions for parsing errors.
2.  **`revit_backend` Package Creation:** **✅**
    *   `families.py`: Manages family resolution, symbol activation, and a robust `ensure_families` auto-loader.
    *   `settings.py`: Centralized, persistent project settings stored in the Revit document.
    *   `utils` package: Helpers for geometry and unit conversions.
    *   `ptd_adapter.py`: Adapts raw parsed data into Revit-compatible objects.
3.  **Unit Test Foundation:**
    *   Sample PTD export files included for reference (`PTD_Export.txt`).
    *   Initial `Taskfile.yml` setup for `pytest`. (Note: test suite itself is a future task).

## Phase 2 – Advanced Import & Creation Logic
**Status: ✅ COMPLETE**
1.  **Element Creator (`creator.py`):** **✅**
    *   Creates all Revit elements (tendons, drapes, leaders) within a single transaction.
    *   Replaces simple live/dead booleans with `start_type`/`end_type` integers (1=Stress, 2=Dead, 3=Pan) to control `End 1/2 Display Mode`.
    *   Populates instance parameters: `PT Tendon Id`, `PT No. of Strands within Tendon`, and a `PT Tendon Data` string for the full drape profile.
    *   Sets a `Pan Offset` parameter for pan-stressed ends.
2.  **Advanced Grouping (`grouping.py`):** **✅**
    *   Sophisticated logic to group similar tendons based on configurable tolerances (angle, length, spacing, shift, drape distance/height).
    *   Places leader elements for grouped tendons.
3.  **Automatic Alignment & Snapping:** **✅**
    *   `alignment.py`: Implements a smart alignment algorithm (rotation and translation) to best-fit tendons to the slab outline, with a manual picker as a fallback.
    *   `snapper.py`: Automatically snaps tendon ends to nearby geometry (like slab edges) based on a configurable tolerance.
4.  **Import Orchestrator (`importer.py`):** **✅**
    *   Manages the entire import process: family check -> parse -> align -> create -> group.
    *   **Crucially, creates the final Detail Group in a separate transaction** to resolve "modified outside group edit" warnings.
5.  **Automatic Tagging (`tagger.py`):** **✅**
    *   Creates `IndependentTag` instances (not generic annotations) for proper host association.
    *   Uses a specific `'Strand Count Only'` tag type for live ends.
    *   Tags "live" ends (stressing and pan-stressed ends) based on `start_type`/`end_type`.
    *   Correctly offsets tags and avoids tagging secondary tendons in a group.

## Phase 3 – UI & UX Improvements
**Status: ✅ COMPLETE**
1.  **Consolidated Settings Dialog:** **✅**
    *   A comprehensive WPF dialog (`settings.xaml`) replaces individual prompts.
    *   Provides UI for all settings: family names, import/tagging booleans, and all grouping/snapping tolerances.
    *   Settings are persisted in the Revit project via `settings.py`.
2.  **Streamlined UI Scripts:** **✅**
    *   Pushbutton scripts in `PTDetailing.tab/` are now lightweight orchestrators, calling the backend logic in `lib/`.

## Phase 4 – Clean-up & Polish
**Status: ✅ COMPLETE**
1.  **Codebase Cleanup:** **✅**
    *   Deleted obsolete scripts, test folders, and legacy files.
    *   The project now has a clean, logical structure.
2.  **Developer Tooling:** **✅**
    *   `Taskfile.yml` provides `lint`, `format`, `test`, `bundle` commands.
    *   `ruff` is used for linting with an IronPython-compatible ruleset.
3.  **Documentation Update:** **✅**
    *   `README.md`, `PRD.md`, and this `ROADMAP.md` have been updated to reflect the current state of the project.

---

## Future Work (Post-v1.0)
-   **Full Test Suite:** Build out the `pytest` suite with `revit-stubs` to achieve >80% coverage for the `lib/` code, ensuring long-term stability.
-   **Native Revit Tendons:** Investigate using the native Revit `DB.Structure.Tendon` elements introduced in Revit 2023+ as an alternative to the current detail component-based approach.
-   **CI/CD Pipeline:** Fully implement the GitHub Actions workflow in `Taskfile.yml` to run `lint` and `test` on all pull requests, and to automatically `bundle` and create a GitHub Release on new tags.
-   **Profile Preview:** Enhance the settings or import dialog to show a graphical preview of the tendon drape profile before import.
-   **Advanced Renumbering:** Implement the "Renumber Tendons" tool with options to renumber by drawing order or by picking a spline.
-   **Batch Operations:** Optimize for very large projects (>1000 tendons) to improve performance.

## Stretch Goals (post-v1)
• Use native Revit Tendon elements (2023+ API).  
• Advanced profile preview inside dialog.  
• Batch operations optimisation (>1000 tendons).  
• Full CPython plug-in port once Revit adds official CPython support.

## New Features (post-v1)
- [x] Implement advanced tendon alignment algorithm (rotation + translation fit with fallback).

---

### Risk Register (rolling)
| ID | Risk | Impact | Mitigation |
|----|------|--------|-----------|
| R-01 | PTD export format changes | High | Abstract parser & include sample files in tests |
| R-02 | IronPython 2.7 limitations | Medium | Keep heavy logic in pure CPython modules; plan CPython future |
| R-03 | Family mis-match in Workshared model | Medium | Use GUID-based lookup & auto-loader checks |

---

Keep this file up-to-date as tasks close or scope shifts. 
# PTDetailing Refactor Roadmap

> Last updated: {{DATE}}

This document mirrors the high-level plan discussed in chat and should stay updated as the project evolves.

---

## Phase 0 – Project Groundwork
1. Add `pyproject.toml` or `requirements.txt` with dev dependencies (`ruff`, `black`, `pytest`, `revit-stubs`).
2. Initialise `Taskfile.yml` for lint / format / test / package commands.
3. Configure CI (GitHub Actions) to run Taskfile on push & pull-request.

## Phase 1 – Core Domain Extraction
1. Create `ptd_parser` package containing:
   • `models.py` – `@dataclass Tendon`, `TendonPoint`, `TendonSet`.
   • `parser.py` – PTD text → models.
   • `exceptions.py` – custom errors.
2. Move unit/XYZ helpers into `utils.conversions`.
3. Ship sample PTD export files under `tests/fixtures/` + pytest coverage (edge cases).

## Phase 2 – Revit Adapter Layer
1. `revit_backend.families` – family resolution & auto-loader. **✅**
2. `revit_backend.creator` – create tendon instances, parameters, metadata. **✅**
3. `revit_backend.drape_writer` & `tag_writer` – write drapes and tags.
4. Unit-test with `revit-stubs` and dependency-injected mocks. **▶ in progress (T7)**
5. Smart family loader (`ensure_families`) – promptless loading of required .rfa based on 3Daro_ID and content/ folder. **✅**
6. Automatic placement alignment + end-snap. **✅**

## Phase 3 – UI & UX Improvements
1. Consolidated WPF dialog for import: file picker, family preview, coordinate mode, progress bar.
2. Replace multiple `forms.SelectFromList` prompts with single dialog.
3. Persist defaults in `%APPDATA%/PTDetailing/config.json`.
4. Pushbutton scripts reduced to orchestration (<20 lines).

## Phase 4 – Clean-up & Polish
1. Delete obsolete scripts (`test.py`, placeholder modules).
2. Run `black` + `ruff`; add pre-commit hook.
3. Update documentation (README, CONTRIBUTING, PRD).
4. Tag `v1.0.0` and publish zipped extension via GitHub Releases.

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
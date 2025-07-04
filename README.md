# PTDetailing – pyRevit Extension for Post-Tension Detailing

## Overview
PTDetailing is an Autodesk Revit® add-in built with **[pyRevit v4.8.16](https://www.notion.so/pyrevit)** (IronPython 2.7.11) that streamlines the transfer of post-tension tendon information from **[INDUCTA PTD](https://inducta.com.au/PTD_main.html)** into Revit 2024 (and later).  
The extension automates the creation, renumbering and annotation of tendons – including live & dead ends plus high/low profile points – using standardised Revit families so that engineers and drafters can produce consistent drawings with minimal manual effort.

---

## Key Features
• **PTD → Revit data import** – Parse PTD text exports and create corresponding Revit tendon objects.  
• **Smart auto-alignment** – Rotates and positions imported tendons to best-fit the slab outline, with manual pick fallback when required.  
• **Automatic tendon tagging** – Place smart tags that report end type, elevations and lengths.  
• **Renumber tools** – Renumber tendons by order or by spline to match shop-drawing conventions.  
• **Standardised families** – Ensures imported tendons land in the correct family/category every time.
• **Smart family auto-loader & zero-click placement alignment** – Automatically loads missing families and aligns imported tendons to the correct slab location without user input.  
• **pyRevit panel integration** – Commands are exposed in the _Post Tensioning_ ribbon panel.  
• **IronPython-only distribution** – No external CPython dependencies required inside Revit.

---

## Repository Layout
```
PTDetailing.extension/
 ├─ lib/                  # Pure-python business logic (Revit-agnostic where possible)
 │   ├─ Drapes.py
 │   ├─ ImportPTD.py      # PTD text-file parser & element builders
 │   ├─ Tagging.py
 │   ├─ Tendon.py         # Tendon data model
 │   ├─ TendonSet.py
 │   └─ Tools.py          # Shared helpers/utilities
 │
 ├─ PTDetailing.tab/      # GUI definitions (bundles) consumed by pyRevit
 │   └─ Post Tensioning.panel/
 │       ├─ Import.pushbutton/
 │       ├─ ReNumberTendons.splitpushbutton/
 │       └─ TagTendons.pushbutton/
 │
 └─ README.md             # ← you are here
```
_Bundles_ follow pyRevit's convention (`bundle.yaml`, `script.py`, icons, etc.).

---

## Installation
1. **Install pyRevit 4.8.16+** (see [docs](https://www.notion.so/pyrevit)).  
2. Clone or download this repo (or just the `PTDetailing.extension` folder).  
3. Copy `PTDetailing.extension` into your local pyRevit extensions directory (usually `%APPDATA%\pyRevit\Extensions`).  
4. Launch Revit 2024 → pyRevit will load the _Post Tensioning_ ribbon panel.

> **Tip:** use `pyrevit extensions info` in a PowerShell console to verify the extension is detected.

### Required Revit Families
The extension ships with standard tendon detail components & tag families (`.rfa`). These must be loaded into the active model (or placed in your office Family Template path).  _If families are missing you will be prompted to load them._

---

## Requirements
Located in `PTDetailing.extension\content\` are the requirements for the tooling.
1. **Tendon** | 3Daro_PT_Tendon_Plan_001        | 3Daro_ID = `3DPT001.001`
2. **Leader** | 3Daro_PT_Tendon_Leader_Plan_001 | 3Daro_ID = `3DPT002.001`
3. **Drape**  | 3Daro_PT_Tendon_Drape_Plan_001  | 3Daro_ID = `3DPT003.001`
4. **Tag**    | 3Daro_PT_Tendon_Tag_Plan_001    | 3Daro_ID = `3DPT004.001`

---

## Usage
1. Export tendons from PTD to `PTD_Export.txt`.  
2. In Revit open the desired floor plan/section.  
3. Click **Import Tendons** – pick the PTD file and the add-in does the rest: loads missing families, aligns to slab, snaps ends and groups if configured.  
4. Optionally run **Re-Number Tendons** or **Tag Tendons** afterwards.

Project-level options such as *auto-snap ends* and tolerance live in **Settings**.

Each command writes to the Revit Undo stack, so changes can be reverted with _Undo_.

---

## Development Guide
### Prerequisites
• Revit 2024 (or vertical product)  
• pyRevit ≥ 4.8.16 (IronPython 2.7.11)  
• A separate CPython ≥3.10 environment (optional) for linting, tests & tooling.

### Recommended Workflow
1. Clone the repo **outside** `%APPDATA%` (e.g. `C:\Repos\PTDetailing`) and create a symlink into pyRevit's extensions dir:  
   `mklink /D %APPDATA%\RevitExtensions\PTDetailing.extension C:\Repos\PTDetailing\PTDetailing.extension`
2. Enable _Attach Debugger_ in pyRevit to step though IronPython code with Visual Studio.
3. Use the **Task-Master** workflow (see below) to run lint, tests and packaging tasks.

### Code Style & Linting
• PEP8 via `ruff` (configured for IronPython compat).  
• Black formatting (python ≥3.10 code only).  
• Docstrings follow Google style.

### Tests
Unit tests live in `lib/tests/` and are executed in standard CPython using pytest + _revit-stubs_ for API mocking.

---

## Task-Master Automation
This repo adopts **[Taskfile.dev Task-Master](https://taskfile.dev/#/) v3** as a lightweight build runner.  Common developer commands are defined in `Taskfile.yml`, e.g.

```yaml
version: '3'

tasks:
  lint:
    desc: Lint python sources with ruff (IronPython compatible ruleset)
    cmds:
      - ruff lib

  format:
    desc: Run black (targets py3 code only)
    cmds:
      - black lib tests

  test:
    desc: Run pytest suite
    cmds:
      - pytest -q

  bundle:  # zip up the extension ready for distribution
    desc: Package PTDetailing.extension into dist/ folder
    cmds:
      - powershell Compress-Archive -Path PTDetailing.extension -DestinationPath dist/PTDetailing.zip -Force
```

Install Task-Master on Windows with **`scoop install task`** or via Chocolatey.  Then:

```ps1
task lint   # run linter
```

---

## Roadmap
- [ ] Refactor `lib/` into OOP modules with full test coverage.  
- [ ] Move parsing logic into a standalone package (`ptd-parser`).  
- [ ] Replace line-based detail components with native Revit Tendon objects (2023+ API).  
- [ ] Add GUI forms with WPF + pyRevit _xaml_ helpers.  
- [ ] CI pipeline (GitHub Actions) running Task-Master tasks.

---

## Contributing
Pull requests are welcome! Please:
1. Create a feature branch from `main`.
2. Ensure lint & tests pass (`task lint test`).
3. Follow commit style `<scope>: <subject>` (conventional commits).
4. Add/update documentation as needed.

---

## License
Distributed under the **MIT License**. See `LICENSE` file for details.

---

## Acknowledgements
* [pyRevit](https://github.com/eirannejad/pyRevit) – Rapid UI & scripting framework for Revit.  
* [INDUCTA PTD](https://inducta.com.au/PTD_main.html) – Source of tendon analysis data.  
* Autodesk Revit API © Autodesk, Inc. 
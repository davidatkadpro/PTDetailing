# PTDetailing – pyRevit Extension for Post-Tension Detailing

## Overview
PTDetailing is an Autodesk Revit® add-in built with **[pyRevit v4.8.16](https://www.notion.so/pyrevit)** that streamlines the transfer of post-tension tendon information from **[INDUCTA PTD](https://inducta.com.au/PTD_main.html)** into Revit 2024 (and later).
The extension automates the creation, grouping, and annotation of tendons—including differentiating between **End Stress**, **Dead End**, and **Pan Stress** conditions—using standardised Revit families so that engineers and drafters can produce consistent, high-quality drawings with minimal manual effort.

---

## Key Features
*   **One-Click PTD Import** – Parse PTD text exports and create corresponding Revit elements in a single operation.
*   **Smart Auto-Alignment** – Automatically rotates and positions imported tendons to best-fit the slab outline, with a manual pick-point fallback.
*   **Advanced, Configurable Grouping** – Intelligently groups similar tendons based on fine-grained tolerances for angle, length, spacing, and drape profile.
*   **Automatic End Tagging** – Places `IndependentTag` instances on "live" tendon ends (End Stress and Pan Stress), correctly associating them with their host.
*   **Differentiates End Types** – Sets parameters on tendon families to correctly display anchor types for stressing, dead, and pan-stressed ends.
*   **Consolidated Settings UI** – A comprehensive WPF dialog to manage all project-level settings for families, grouping tolerances, and import options.
*   **Smart Family Auto-Loader** – Automatically loads required families from the extension's `content/` folder if they are missing from the project.
*   **Robust & Performant** – Batches all element creation into minimal transactions to ensure performance and prevent common Revit errors like "modified outside group edit mode".

---

## Repository Layout
The codebase has been refactored into a clean, modular structure.
```
PTDetailing.extension/
 ├─ lib/                  # Core business logic (Revit-agnostic where possible)
 │   ├─ ptd_parser/       # PTD text-file parser and data models
 │   ├─ revit_backend/    # Revit-specific implementation (creation, settings, etc.)
 │   └─ utils/            # Shared helpers/utilities
 │
 ├─ PTDetailing.tab/      # GUI definitions (bundles) consumed by pyRevit
 │   └─ Post Tensioning.panel/
 │       ├─ Import.pushbutton/
 │       ├─ Settings.pushbutton/
 │       └─ TagTendons.pushbutton/
 │
 ├─ content/              # Bundled Revit families (.rfa)
 │
 ├─ README.md             # ← you are here
 ├─ ROADMAP.md            # Tracks future development
 ├─ PRD.md                # Detailed product requirements
 └─ Taskfile.yml          # Developer task automation
```
_Bundles_ follow pyRevit's convention (`bundle.yaml`, `script.py`, icons, etc.).

---

## Installation
1.  **Install pyRevit 4.8.16+** (see [docs](https://www.notion.so/pyrevit)).
2.  Clone or download this repo and locate the `PTDetailing.extension` folder.
3.  Copy `PTDetailing.extension` into your local pyRevit extensions directory (find it via the pyRevit Settings dialog).
4.  Launch Revit 2024 → pyRevit will load the _Post Tensioning_ ribbon panel.

### Required Revit Families
The extension is bundled with all required standard tendon detail components & tag families (`.rfa`) in the `content/` folder. The add-in will **automatically load** these families into your project if they are not already present.

---

## Usage
1.  Export tendons from PTD to a `.txt` file.
2.  In Revit, open the desired floor plan view.
3.  (First time) Click **Settings** in the _Post Tensioning_ panel to review and configure project-specific options like grouping tolerances and family names. These settings are saved with the Revit project.
4.  Click **Import Tendons** – pick the PTD file and the add-in does the rest: loads missing families, aligns the tendon set to the slab, creates all tendon elements, groups them, and tags the live ends according to your settings.
5.  Optionally run **Tag Tendons** to add additional tags.

Each command writes to the Revit Undo stack, so changes can be easily reverted.

---

## Development Guide
### Prerequisites
*   Revit 2024
*   pyRevit ≥ 4.8.16 (IronPython 2.7.11)
*   A separate CPython environment (e.g., 3.10+) for running developer tools.

### Recommended Workflow
1.  Clone the repo **outside** your pyRevit extensions folder (e.g., `C:\dev\PTDetailing`).
2.  Create a symbolic link from your extensions folder to your repo:
    `mklink /D "%APPDATA%\pyRevit\Extensions\PTDetailing.extension" "C:\dev\PTDetailing\PTDetailing.extension"`
3.  Use the **Task-Master** workflow (see below) to run lint, tests and packaging tasks.

### Code Style & Linting
*   PEP8 via `ruff` (configured for IronPython compatibility).
*   Docstrings follow Google style.

### Tests
The foundation for a `pytest` suite is in place. Full test coverage using `revit-stubs` is a future goal as outlined in the [ROADMAP.md](mdc:ROADMAP.md).

---

## Task-Master Automation
This repo uses **[Task](https://taskfile.dev/) v3** as a lightweight build runner. Common developer commands are defined in `Taskfile.yml`:

```yaml
version: '3'

tasks:
  lint:
    desc: Lint python sources with ruff (IronPython-compatible)
    cmds:
      - ruff lib

  format:
    desc: Format code with black (run on py3 compatible code)
    cmds:
      - black lib

  test:
    desc: Run pytest test-suite (work in progress)
    cmds:
      - pytest -q

  bundle:
    desc: Package the extension into dist/PTDetailing.zip
    cmds:
      - powershell Compress-Archive -Path PTDetailing.extension -DestinationPath dist/PTDetailing.zip -Force
```

Install Task on Windows with **`scoop install task`** or another package manager. Then:
```powershell
# Run the linter
task lint

# Package the extension for distribution
task bundle
```

---

## Roadmap
The initial MVP and subsequent refactoring are complete. Future work, including building out the test suite and implementing a renumbering tool, is tracked in the [**ROADMAP.md**](mdc:ROADMAP.md) file.

---

## Contributing
Pull requests are welcome! Please:
1.  Create a feature branch from `main`.
2.  Ensure linter passes (`task lint`).
3.  Follow conventional commit style: `<scope>: <subject>`.
4.  Add/update documentation as needed.

---

## License
Distributed under the **MIT License**.

---

## Acknowledgements
* [pyRevit](https://github.com/eirannejad/pyRevit) – Rapid UI & scripting framework for Revit.  
* [INDUCTA PTD](https://inducta.com.au/PTD_main.html) – Source of tendon analysis data.  
* Autodesk Revit API © Autodesk, Inc. 
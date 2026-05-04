# Screenshots

Screenshots in this folder are **manually captured** and committed to the
repository. They are referenced directly by the docs pages in `docs/screens/`.

---

## How to replace a screenshot

1. Launch the app: `uv run openstan`  
   The window opens at **1280 × 800 px** — this is the target capture size.
2. Set up the app state described in the table below for the screenshot you want.
3. Capture exactly the application window at 1280 × 800.
4. Save the file using the **exact filename** shown in the table (PNG format).
5. Drop it into this folder, replacing the existing file.
6. Commit — the docs site rebuilds automatically on push to `master`.

### Capture tips by platform

| Platform | Recommended tool | Notes |
|---|---|---|
| **macOS** | `Cmd+Shift+4` then `Space`, click window | Use **Shottr** or **CleanShot X** for exact pixel sizing |
| **Windows** | **ShareX** (free) | Define a fixed 1280×800 capture region |
| **Linux** | **Flameshot** (`flameshot gui`) | Resize the window first with your WM or `wmctrl -r openstan -e 0,-1,-1,1280,800` |

---

## Screenshot index

| File | Docs page | What it shows | State to capture |
|---|---|---|---|
| `title.png` | — | Application title bar | App open, any project selected, showing the logo, About and Admin buttons |
| `project_view.png` | `screens/project-management.md` | Project selector bar | At least one project registered; drop-down showing project name; Create New and Add Existing buttons visible |
| `project_nav.png` | `screens/project-management.md` | Navigation bar | Project with committed data selected; all four nav buttons visible (Project Info, Import Statements, Export Data, Run Reports) |
| `project_wizard.png` | `screens/project-management.md` | Create New Project wizard | Wizard open in **new** mode; Project Name field filled in; folder path chosen |
| `statement_queue.png` | `screens/import-statements.md` | Import queue with files | Queue populated with at least one folder group containing 2–3 PDF files; Run Statement Import button enabled |
| `statement_results.png` | `screens/import-results.md` | Import results panel | Batch complete; SUCCESS tab active and showing at least 2 rows; summary bar showing counts; Commit Batch button enabled |
| `debug_info.png` | `screens/import-results.md` | Debug Info dialog | Dialog open; at least one REVIEW or FAILURE row visible; debug status column showing `done`; Open JSON and Open PDF buttons visible |
| `project_info.png` | `screens/project-info.md` | Project Info panel | At least 2 accounts in the table; date range populated; gap warning button visible |
| `gap_detail.png` | `screens/project-info.md` | Gap Detail dialog | Dialog open; at least one account node expanded showing a gap description |
| `export_data.png` | `screens/export-data.md` | Export Data — Standard tab | Standard Exports tab active; Type/Batch/File naming/Folder parameters all visible; export buttons enabled |
| `advanced_export.png` | `screens/advanced-export.md` | Export Data — Advanced tab | Advanced tab active; Account drop-down populated; at least one export spec button visible |
| `run_reports.png` | `screens/run-reports.md` | Run Reports — builder and preview | Builder pane: report title filled, 3+ columns ticked, 1 filter row added, Group By populated; Preview pane: results table showing data |
| `admin.png` | `screens/admin.md` | Admin dialog | Dialog open (double-click footer); all three sections visible; project drop-downs populated |
| `about.png` | `screens/about.md` | About dialog | Dialog open; version number, links, and BSP version all visible |

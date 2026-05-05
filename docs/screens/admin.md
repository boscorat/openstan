# Admin

The **Admin** dialog is used for project management operations that modify or remove data. It is intentionally hidden from the main navigation to prevent accidental use.

---

## Opening the Admin dialog

Click the **Admin** button in the top-right corner of the application title bar. A confirmation is not required to open the dialog — destructive actions inside the dialog each have their own confirmation step.

![Admin dialog](../assets/screenshots/admin.png#only-light)
![Admin dialog](../assets/screenshots/dark/admin.png#only-dark)

---

## Delete Project

Permanently removes a project from both the openstan UI database and, optionally, from disk.

| Control | Description |
|---|---|
| **Project** drop-down | Select the project to delete. |
| **Also delete the project folder from disk** checkbox | When ticked, the project folder and all its contents are deleted from the filesystem after the UI record is removed. |
| **Delete Project** button | Initiates deletion after a confirmation dialog. |

!!! danger "This cannot be undone"
    If **Also delete the project folder from disk** is ticked, all statement PDFs, configuration files, and the project database are permanently deleted. Ensure you have a backup before proceeding.

---

## Remove Project from UI Only

Removes a project from the openstan application database without touching any files on disk. The project folder remains intact and can be re-added later using **Add Existing Project**.

| Control | Description |
|---|---|
| **Project** drop-down | Select the project to remove. |
| **Remove from UI** button | Removes the project registration after a confirmation dialog. |

Use this option if you want to temporarily hide a project from the selector, or if you are moving a project folder and will re-register it from its new location.

---

## Reset Application

Deletes and recreates the openstan application database (`gui.db`), effectively returning the application to a clean first-run state.

**All project registrations are removed.** Project folders on disk are not affected.

Click **Empty Database & Restart** to proceed. A confirmation dialog is shown before any action is taken. The application closes and must be restarted manually after the reset completes.

!!! warning "Use with care"
    After a reset, all projects must be re-added via **Add Existing Project**. The project data (statements, transactions) stored in each project folder is unaffected.

---
description: "Solve common openstan issues: import failures, logs not showing, verbose mode, and how to share logs with support. Troubleshooting FAQ and solutions."
---

# Troubleshooting

Need help? This guide covers common issues and solutions.

---

## Importing Statements

### "The import fails or shows errors"

**Check the Import Results screen:**

1. After import completes, click **View Results** or go to the Import Results screen
2. Look for the **Issue Summary** section
3. Check which fields/banks failed

**For detailed diagnostics:**

1. Enable verbose mode: Admin → Logging Settings → Check "Enable verbose mode"
2. Try the import again
3. Click Admin → View Project Log
4. Look for error messages in the log
5. Disable verbose mode when done

**Common issues:**

| Issue | Solution |
|---|---|
| "Unrecognized bank format" | The PDF format isn't supported for this bank yet. Check [bank_statement_parser issues](https://github.com/boscorat/bank_statement_parser/issues) for status. |
| "Could not extract field X" | The field exists in the PDF but parser couldn't read it. Enable verbose mode for details. File an issue with the PDF (redacted). |
| "PDF is corrupted or password-protected" | Try opening the PDF in your PDF reader to confirm it's valid. Password-protected files aren't supported. |
| "Out of memory" | You're importing too many statements at once. Split into smaller batches. |

### "Statement imports are very slow"

**Normal behavior:** Importing 10–20 statements takes 2–5 minutes depending on size and complexity.

**If it's taking longer than expected:**

1. Check your system resources (open System Monitor/Task Manager)
2. Close other applications consuming CPU/memory
3. Enable verbose mode and check logs for per-field extraction timing
4. Try importing a smaller batch

---

## Logging & Debugging

### "I don't see logs in the viewer"

**Possible causes:**

1. **Log file doesn't exist yet**
   - App has just started; perform an action (import, export) to generate entries
   - Click Refresh button in the log viewer
   - Solution: Perform an operation, then check logs again

2. **Wrong log selected**
   - App Log is always available
   - Project Log only appears when a project is selected
   - Solution: Make sure you've selected a project

3. **File permissions issue**
   - App doesn't have write access to log directory
   - Solution (Linux): Check `chmod` on `~/.local/share/openstan/` (should be user-owned)
   - Solution (Windows/macOS): Try opening log file manually (see [Finding Log Files Manually](guides/logging.md#finding-log-files-manually))

4. **Enable verbose mode for more output**
   - Normal log level only shows milestones and errors
   - DEBUG level shows many more entries
   - Solution: Admin → Logging Settings → Check "Enable verbose mode"

### "Logs are growing too large"

**Normal behavior:** Logs rotate automatically at 10 MB and keep 5 backups (~60 MB total).

**To reduce output:**

- Disable verbose mode: Admin → Logging Settings → Uncheck "Enable verbose mode"
- Logs won't shrink until files rotate, but new logging will be quieter

**Manual cleanup (if disk space is critical):**

1. Navigate to log directory (see [Finding Log Files Manually](guides/logging.md#finding-log-files-manually))
2. Delete old session files (safe; each file is one session)
3. Keep current session's log file (app still writing to it)

**Linux example:**
```bash
cd ~/.local/share/openstan/
# List files by date (newest first)
ls -lt
# Delete old sessions (more than 30 days old)
find . -name "*.log*" -mtime +30 -delete
```

### "Verbose mode is showing too much output"

**Expected behavior:** Verbose mode increases output 3–5× compared to normal.

DEBUG logging shows:

- Per-field extraction details (slow fields identified)
- Database operations (INSERT, UPDATE, DELETE)
- Library diagnostics from `bank_statement_parser` and `uk_bank_statement_anonymiser`

**Solution:**

- Disable verbose mode when done troubleshooting
- Admin → Logging Settings → Uncheck "Enable verbose mode"
- Changes apply immediately (no restart needed)

### "How do I share logs with support?"

**Step 1:** Enable verbose mode (optional, for detailed info)
- Admin → Logging Settings → Check "Enable verbose mode"
- Perform the action that's failing
- Wait 10–30 seconds

**Step 2:** Gather logs
- Admin → View App Log or View Project Log
- Click **Copy** button

**Step 3:** Redact sensitive data
- Review logs and remove account numbers, names, etc. (use `****` as placeholder)
- See [Sharing Logs with Support](guides/logging.md#sharing-logs-with-support) for examples

**Step 4:** Submit
- [GitHub issue](https://github.com/boscorat/openstan/issues/new?template=bug-report.yml)
- Or [community@openstan.org](mailto:community@openstan.org)

---

## Exporting Data

### "Export fails or produces unexpected output"

**Check the export settings:**

1. Go to Export Data screen (Alt+E)
2. Verify:
   - Export Type is correct (Single/Split/Pivot)
   - Output Format is correct (Excel/CSV/JSON)
   - Date range and filters are correct
3. Try exporting a smaller date range

**For diagnostics:**

1. Enable verbose mode: Admin → Logging Settings → Check "Enable verbose mode"
2. Perform the export
3. View Project Log and look for error messages
4. Disable verbose mode when done

### "The Excel file is corrupted"

**Possible causes:**

1. **Antivirus software blocked the file** — Check your antivirus logs
2. **File was partially written** — Not enough disk space available
3. **File is too large** — Excel has a 1M row limit; use CSV for very large datasets

**Solutions:**

- Check your free disk space
- Try exporting to CSV instead
- Split the export into smaller date ranges
- Disable antivirus temporarily (only for testing)

### "Export is very slow"

**Normal behavior:** Exporting 100k+ rows takes 1–2 minutes depending on export type.

**To speed up:**

- Export smaller date range
- Use "Single" export type (faster than Split or Pivot)
- Close other applications
- Check disk space (slow disk = slow export)

---

## Anonymisation

### "Anonymisation fails or takes too long"

**First check:**

1. Enable verbose mode: Admin → Logging Settings → Check "Enable verbose mode"
2. Try anonymising a single statement first
3. View Project Log and look for errors
4. Check the anonymisation results screen

**Common issues:**

| Issue | Solution |
|---|---|
| "PDF is corrupted or password-protected" | Try opening in PDF reader first. Anonymiser doesn't support password-protected PDFs. |
| "Exclusion patterns didn't match" | Check regex patterns are correct. Test with a simple pattern first. |
| "Anonymisation is very slow" | Large PDFs (100+ pages) can take 30+ seconds. Normal behavior. |
| "Output PDF is corrupted" | Try anonymising a different statement first. File an issue with the PDF (redacted). |

### "Can't find the anonymised PDFs"

**Default location:** Same folder as the source PDF files

**To check:**

1. In Import Statements, find the folder you imported from
2. Look for a `_anonymised/` subfolder in that directory
3. Files are named: `[original-name]_anonymised.pdf`

**If not found:**

1. Check the anonymisation results screen
2. Enable verbose mode and try again
3. Look in Project Log for file path information

---

## Installation & Startup

### "App won't start or crashes on startup"

**Check the App Log:**

1. Navigate to log directory manually (see [Finding Log Files Manually](guides/logging.md#finding-log-files-manually))
2. Open the most recent log file with a text editor
3. Look for ERROR messages at the end

**Common startup issues:**

| Platform | Issue | Solution |
|---|---|---|
| **Windows** | "Missing library" error | Reinstall the app (may be incomplete installation). Try [latest installer](https://github.com/boscorat/openstan/releases) |
| **macOS** | "App is damaged" warning | App wasn't downloaded properly. Re-download and try again. |
| **Linux** | Qt library errors | Install Qt dependencies. See [Installation Guide](../installation.md#linux-debian-ubuntu) |

**To debug further:**

1. Enable verbose mode: Create a new project and check logs
2. Try running from a different location (e.g., USB drive)
3. Check for recently installed security software blocking the app
4. Report issue with App Log attached (see [Sharing Logs with Support](#how-do-i-share-logs-with-support))

### "Database error: 'gui.db' is locked or corrupted"

**The database is locked:**

1. Close all openstan windows
2. Wait 30 seconds
3. Restart the app

**The database is corrupted:**

1. Backup your projects: `~/.local/share/openstan/projects/` (Linux example)
2. Delete `~/.local/share/openstan/gui.db`
3. Restart the app (creates new empty database)
4. Try re-opening your projects

**If issue persists:**

- Report with App Log attached
- Include your platform and app version (Help → About)

---

## General Help

### "I've followed all steps and still have issues"

**Collect logs:**

1. Enable verbose mode: Admin → Logging Settings
2. Reproduce the issue
3. Gather both App Log and Project Log (if applicable)

**Report the issue:**

1. [GitHub issue](https://github.com/boscorat/openstan/issues/new?template=bug-report.yml)
2. Include:
   - Description of what you did
   - What error you saw
   - Your platform (Windows/macOS/Linux)
   - App version (Help → About)
   - Relevant log excerpts (with PII redacted)

3. Or email: [community@openstan.org](mailto:community@openstan.org)

### "Where can I find help?"

- **[Full documentation](../index.md)** — Complete guides for all features
- **[GitHub Discussions](https://github.com/boscorat/openstan/discussions)** — Ask questions, share ideas
- **[GitHub Issues](https://github.com/boscorat/openstan/issues)** — Report bugs
- **[Privacy Policy](../privacy.md)** — How your data is handled
- **[Community & Support](../community.md)** — Ways to get help and contribute

---

## Related Topics

- [Logging & Debugging Guide](guides/logging.md) — Full reference for logging features
- [Installation Guide](../installation.md) — Platform-specific setup
- [Quick Start](../quickstart.md) — Get started in 5 minutes
- [Community & Support](../community.md) — Connect with the community

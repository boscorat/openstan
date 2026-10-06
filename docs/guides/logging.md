---
description: "View application and project logs, enable verbose mode for debugging, and safely share logs with support. Platform-specific paths and privacy guidance."
---

# Logging & Debugging

openstan writes two log files — an App Log and a Project Log — that capture events, errors, and diagnostics as you use the application. This guide explains how to view them, how to enable verbose (DEBUG) mode for detailed diagnostics, and how to share logs safely with support.

---

## What are logs?

Logs are records of what happens inside the application as you use it. They capture important events like:

- When the app starts
- When you import statements
- When operations succeed or fail
- Detailed diagnostic information during import, export, and anonymisation

Logs help diagnose problems and are invaluable when reporting issues to support.

## Privacy Notice ⚠️

**Logs may contain sensitive bank account information.** Be cautious when sharing logs with others. Review logs before pasting into public forums or sending to unverified recipients. See [Sharing Logs with Support](#sharing-logs-with-support) below for safe sharing practices.

---

## Viewing Logs

There are two types of logs:

| Log Type | Contains | View When |
|---|---|---|
| **App Log** | Application-wide events, startup diagnostics, menu actions, general errors | App crashes, startup issues, menu problems, general diagnostics |
| **Project Log** | Project-specific operations, statement imports, parser errors, anonymiser details | Import failures, statement parsing issues, anonymisation problems |

### Opening the Log Viewer

1. Click the **Admin** button in the top-right corner of the window
2. Look for the **View Logs** section
3. Click either **View Application Log** or **View Project Log**
4. A dialog will open showing the log contents

The log viewer displays the most recent 500 lines of the log file. If the file is larger, a notice appears at the bottom indicating that content has been truncated.

### What You'll See in the Log Viewer

- **File path** at the top (for your reference)
- **Privacy warning banner** (reminder about sensitive data)
- **Log contents** (read-only text area, showing recent entries)
- **Truncation notice** if the file is larger than 500 lines
- **Three buttons:**
  - **Refresh** — reload the log file (shows latest changes)
  - **Copy** — copy displayed text to clipboard
  - **Close** — close the dialog

---

## Finding Log Files Manually

If you prefer to browse log files directly on your computer, here's where to find them:

### Windows 10 / 11

1. Press **`Win+R`** to open the Run dialog
2. Type: **`%APPDATA%\openstan`** and press Enter
3. Your log files are displayed in this folder

Alternatively, open **File Explorer** and navigate to:
```
C:\Users\[YourUsername]\AppData\Roaming\openstan
```

### macOS

1. Open **Finder**
2. Press **`Cmd+Shift+G`** (Go to Folder)
3. Type: **`~/Library/Application Support/openstan`** and press Enter
4. Your log files are displayed in this folder

### Linux

Open a file manager and navigate to:
```
~/.local/share/openstan/
```

Or open a terminal and run:
```bash
ls -la ~/.local/share/openstan/
```

---

## Enabling Verbose Mode (DEBUG Logging)

### What is Verbose Mode?

By default, openstan logs important milestones and errors only. **Verbose mode** enables detailed debugging output, which can help diagnose stubborn issues.

### When to Use Verbose Mode

- **Troubleshooting import failures** — shows per-field extraction details
- **Reporting issues with detailed diagnostics** — support may ask for this
- **Performance investigation** — reveals timing details for slow operations
- **Supporting library issues** — `bank_statement_parser` and `uk_bank_statement_anonymiser` show diagnostic output

### How to Enable Verbose Mode

1. Click the **Admin** button in the top-right corner
2. Look for the **Logging Settings** section
3. Check the **Enable verbose mode** checkbox
4. Changes apply **immediately** (no restart needed)

### Effects of Verbose Mode

| Setting | Log Level | Output | Appearance |
|---------|-----------|--------|-----------|
| **Normal** (unchecked) | INFO | Milestones, errors, important events | Clean, minimal output |
| **Verbose** (checked) | DEBUG | Per-field extraction, database operations, library diagnostics | ~3–5× more output |

### Performance Impact

Verbose mode adds approximately **5–10% overhead** to import and export operations, which is negligible for most users. Disable it once you've finished troubleshooting.

### How Verbose Mode Affects Library Logs

When you enable verbose mode, it cascades to dependent libraries:

- **`bank_statement_parser`** — Shows extraction timing for every field, bank format detection, field mapping details
- **`uk_bank_statement_anonymiser`** — Shows PDF processing details, exclusion pattern matching, anonymisation progress

All output goes to the same project/app log files (no separate files are created).

### Persistent Settings

Your verbose mode setting is saved automatically and will be restored the next time you open the app.

---

## Log Rotation & Retention

### How Automatic Rotation Works

When a log file reaches **10 MB**, it's automatically rotated:

1. The current log file is renamed (e.g., `.log.1`)
2. A new `.log` file is created
3. The app continues writing to the new file

### How Many Backups Are Kept?

The last **5 backup files** are kept (`.log.1` through `.log.5`), giving you approximately **60 MB** of total retention per log type.

### Example: Rotation Sequence

```
openstan.log          ← Currently being written to (10 MB)
openstan.log.1        ← Previous log (10 MB)
openstan.log.2        ← Previous log (10 MB)
openstan.log.3        ← Previous log (10 MB)
openstan.log.4        ← Previous log (10 MB)
openstan.log.5        ← Oldest kept (10 MB)
                      ← openstan.log.6 is deleted when rotation occurs
```

### Cleanup Policies

- **Automatic cleanup:** No automatic cleanup occurs; logs are preserved for audit trail purposes
- **Manual cleanup:** You can delete old session files if disk space is a concern (see below)

### Session-Based Naming

Each time you start openstan, a new unique log file is created based on your session:

- App log: `~/.local/share/openstan/[session-uuid].log` (Linux example)
- Project log: `<project-root>/[session-uuid].log`

**Benefit:** No collision between sessions; you have a complete audit trail of all app sessions.

### Manual Cleanup (Optional)

If log files are consuming significant disk space:

1. Navigate to your log directory (see [Finding Log Files Manually](#finding-log-files-manually))
2. Delete old session files (e.g., sessions from a month ago)
3. **Do NOT delete your current session's log file** — the app is still writing to it

**Linux example:**
```bash
cd ~/.local/share/openstan/
# List old files and confirm before deleting
ls -lt | head -20
# Delete files older than 30 days (example)
find . -name "*.log*" -mtime +30 -delete
```

---

## Sharing Logs with Support

### Why Share Logs?

Support can often diagnose problems much faster with access to your logs. Logs show:

- Exact sequence of events leading to the error
- Error messages and stack traces
- Bank/statement parser diagnostics
- Why a particular import or operation failed

### Safe Sharing Process

**Step 1: Enable Verbose Mode (Optional)**

If the issue is intermittent, enabling verbose mode first provides more detail:

1. Admin → Logging Settings → Check "Enable verbose mode"
2. Perform the action that causes the issue (import, export, etc.)
3. Wait 10–30 seconds, then gather logs

**Step 2: Open the Log Viewer**

1. Admin button → View App Log or View Project Log
2. Review the displayed logs

**Step 3: Copy Logs**

1. Click the **Copy** button
2. Logs are copied to your clipboard (last 500 lines shown in viewer)

**Step 4: Paste and Submit**

Paste logs into:

- **GitHub issue:** [Report a Bug](https://github.com/boscorat/openstan/issues/new?template=bug-report.yml)
- **Email:** [community@openstan.org](mailto:community@openstan.org)

**Step 5: Review and Redact PII**

Before submitting, review logs and remove sensitive data (see below).

### What Support Can See in Logs

Safe to share:

- Timestamps of events
- Error messages and stack traces (e.g., "field X could not be parsed")
- Bank name and statement format
- Import/export progress
- Which operations were performed (import, export, anonymise)

### What NOT to Share

Always remove these before pasting into public forums:

- **Account numbers** (full or partial)
- **Routing numbers**
- **Full names** of account holders
- **Addresses**
- **Dates of birth**
- **Transaction amounts** (context-dependent; ask support)

### Example: Redacting Logs

**Before (with PII):**
```
2026-10-05 14:32:15 | INFO | openstan | User started session
2026-10-05 14:32:16 | INFO | openstan.importers | Importing: Mr John Smith statement Oct 2026.pdf
2026-10-05 14:32:17 | DEBUG | bank_statement_parser | Extracting account: GB12 MIDL 3456 7890 12
2026-10-05 14:32:18 | ERROR | bank_statement_parser | Failed to parse: Unrecognized field format
```

**After (redacted):**
```
2026-10-05 14:32:15 | INFO | openstan | User started session
2026-10-05 14:32:16 | INFO | openstan.importers | Importing: [REDACTED] statement Oct 2026.pdf
2026-10-05 14:32:17 | DEBUG | bank_statement_parser | Extracting account: GB12 [REDACTED]
2026-10-05 14:32:18 | ERROR | bank_statement_parser | Failed to parse: Unrecognized field format
```

---

## Troubleshooting Log Issues

### "I don't see logs in the viewer"

**Possible causes:**

1. **Log file doesn't exist yet**
   - App may have just started; give it a moment
   - Perform an action (import, export) to generate log entries
   - Try clicking **Refresh** button

2. **Wrong log selected**
   - App Log is always available; Project Log is only available when a project is selected
   - Make sure you've selected a project before clicking View Project Log

3. **File permissions issue**
   - App may not have read access to log directory
   - Check that the log directory exists and is readable

**Solution:** Enable verbose mode (creates more log entries), then perform an action, then check logs again.

### "Logs are growing too large"

**Normal behavior:** Logs rotate automatically at 10 MB and keep 5 backups (~60 MB total). This is expected.

**Optional manual cleanup:**

If disk space is critical, you can safely delete old session log files:

1. Navigate to log directory
2. Delete old session UUIDs (keep current session)
3. This won't affect the running app

**To reduce logging output:** Disable verbose mode if it's enabled.

---

## Related Topics

- [Admin Screen](admin.md) — Access logging controls from the UI
- [Troubleshooting Guide](../troubleshooting.md) — Common issues and solutions
- [Privacy Policy](../privacy.md) — How openstan handles your data
- [Community & Support](../community.md) — Report issues or ask questions

# Anonymise PDF

The **Anonymise PDF** tool lets you produce a redacted copy of a bank statement PDF suitable for sharing — for example, when attaching a failing statement to a GitHub issue. All letters are scrambled by default; you control exactly which numeric strings (sort codes, account numbers) are also scrambled, and which structural words must remain intact so that the parser can still process the anonymised file.

---

## Opening the tool

The Anonymise tool can be opened from two places:

- **Admin dialog** → *Anonymise PDF* section → **Open Anonymise Tool** button.
- **Debug Info dialog** → **Anonymise** button on any REVIEW or FAILURE row — the tool opens pre-loaded with that statement's PDF path.

![Anonymise dialog](../assets/screenshots/anonymise.png#only-light)
![Anonymise dialog](../assets/screenshots/dark/anonymise.png#only-dark)

---

## Selecting a source PDF

Use the **Browse…** button to open a file picker and select the PDF you want to anonymise. The full path is shown in the field to the left of the button.

If the tool was opened from the Debug Info dialog, the path is pre-filled with the failing statement's path.

---

## Editing anonymise.toml

The central panel shows the contents of `config/user/anonymise.toml` inside the active project folder. This file is created automatically when the project is initialised, pre-populated with sensible defaults including common UK bank transaction type codes and month names.

Edit the file directly in the text editor. Three sections control the anonymisation:

### `[numbers_to_scramble]`

A list of substrings. Any PDF text fragment containing one of these strings has its digit characters replaced with random digits. Separators (hyphens, spaces) are preserved.

Use this to scramble sort codes and account numbers that would otherwise be left as-is:

```toml
[numbers_to_scramble]
values = [
    "11-22-33",   # sort code
    "12345678",   # account number
]
```

### `[words_to_not_scramble]`

A list of words and phrases that must appear unchanged in the output. Matching ignores case and all whitespace, so multi-word phrases are matched even when the PDF renders them across multiple text fragments.

Pre-populate this with any structural text the parser needs to read — column headers, balance labels, transaction type codes:

```toml
[words_to_not_scramble]
exclude = [
    "Balance Brought Forward",
    "Date",
    "Money In",
    "Money Out",
    # ... bank-specific phrases
]
```

### `[filename_replacements]`

Key/value pairs applied to the output filename stem before the `anonymised_` prefix is prepended. Use this to remove real names or account references from the filename:

```toml
[filename_replacements]
"RealSurname" = "Testname"
```

### Saving the config

Click **Save Config** to write your edits back to disk. The editor validates that the file is valid TOML before saving; an error dialog is shown if the syntax is invalid.

!!! tip "Iterating"
    The typical workflow is: run → open both PDFs → notice what structural text is unreadable → add those phrases to `[words_to_not_scramble]` → save → run again. Repeat until the anonymised PDF is both sufficiently redacted and parseable.

---

## Running the anonymisation

Click **Run Anonymisation**. The tool calls `bsp.anonymise_pdf` in a background thread so the UI remains responsive. The status line updates when the run completes, showing the full path of the output file.

The anonymised PDF is written **alongside the source file** with `anonymised_` prepended to the filename (after any filename replacements are applied).

!!! warning "Re-running overwrites the previous output"
    Each run writes to the same output path. If you need to preserve a previous version, move or rename it before running again.

---

## Viewing the results

Once a run completes, **Open Original PDF** and **Open Anonymised PDF** both become active. Click either button to open the file in your system's default PDF viewer. Open both to compare them side-by-side.

| Button | Action |
|---|---|
| **Open Original PDF** | Opens the source PDF in the system viewer. Available as soon as a file is selected. |
| **Open Anonymised PDF** | Opens the anonymised output in the system viewer. Enabled after a successful run. |

---

## anonymise.toml location

The config file lives at:

```
<project folder>/config/user/anonymise.toml
```

It is created automatically when a project is first initialised or connected. You can also edit it directly outside of openstan with any text editor.

!!! note "Keep anonymise.toml out of source control"
    The file may contain substrings of real sort codes or account numbers used as matching patterns. Treat it as sensitive and exclude it from any repository you share.

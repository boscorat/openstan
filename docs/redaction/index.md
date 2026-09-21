---
description: "Anonymise and redact bank statement PDFs for safe sharing with AI, accountants, or bookkeepers. 100% offline, no data leaves your machine."
---

# Redaction & Anonymisation

Bank statements contain sensitive personal data — account numbers, sort codes,
transaction descriptions, merchant names, and balances. Once you share a
statement PDF, you lose control over where that data goes.

openstan's **Anonymise PDF** tool lets you produce redacted copies of bank
statement PDFs that are safe to share, while keeping the structure intact
so parsers can still read them.

[Anonymise a PDF Now](../screens/anonymise.md){ .md-button .md-button--primary }
[Use Cases](use-cases.md){ .md-button }

---

## Why Redact?

### Sharing with AI

ChatGPT, Claude, and other AI assistants are increasingly used to analyse
financial data. Uploading an unredacted statement exposes account numbers,
sort codes, and personal transaction details to third-party servers.

### Sending to Professionals

Accountants, bookkeepers, and financial advisors need to see your transactions
— but they don't need your full account details. Redaction gives you control
over what they see.

### Bug Reports & Support

When reporting a parsing issue on GitHub, you need to attach a sample PDF.
Anonymising it first protects your financial data while giving developers
what they need to help.

### Compliance

GDPR and other data protection regulations require you to minimise personal
data sharing. Redacting statements before distribution is a practical way
to meet these obligations.

---

## How It Works

1. **Open the Anonymise tool** — click the **Anonymise Statements** button in the nav
   bar, or go to Admin → Open Anonymise Tool.
2. **Select a PDF or folder** — choose a single file or an entire folder
   of statements for batch processing.
3. **Configure rules** — two tables let you control what gets redacted:
   - **Always Anonymise** — force specific string replacements (e.g.,
     sort codes → `00-00-00`)
   - **Never Anonymise** — exclude structural text from scrambling
     (e.g., column headers the parser needs)
4. **Run** — the tool scrambles all text by default, then applies your
   rules. Output files are saved alongside the originals.
5. **Review** — open both the original and anonymised PDF side by side
   to verify the result before sharing.

---

## Key Features

| Feature | Description |
|---|---|
| **Single-file mode** | Anonymise one PDF at a time with instant results |
| **Batch mode** | Process entire folders with progress tracking |
| **Retain descriptions** | Optional mode that preserves transaction descriptions while redacting account details |
| **Persistent config** | Your Always Anonymise and Never Anonymise rules are saved per-project in TOML files |
| **100% offline** | All processing happens locally — no data leaves your machine |

---

## Learn More

- [Use Cases](use-cases.md) — real-world scenarios for redaction
- [Reference](../screens/anonymise.md) — full tool documentation

---

## Related Topics

- [Anonymise PDF Reference](../screens/anonymise.md) – Full tool documentation and config guide
- [Import Results](../screens/import-statements.md) – Import bank statement PDFs
- [Export Data](../screens/export-data.md) – Export transactions to Excel, CSV, or JSON
- [Privacy Policy](../privacy.md) – How openstan handles your financial data
- [Admin Panel](../screens/admin.md) – Access the Anonymise tool from the Admin dialog

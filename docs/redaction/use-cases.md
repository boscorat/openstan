---
description: "Real-world use cases for anonymising bank statement PDFs — sharing with AI assistants, sending to accountants, bug reports, and compliance requirements."
---

# Redaction Use Cases

Bank statements are some of the most sensitive personal documents you
hold. Here are the most common reasons to anonymise them before sharing.

---

## Sharing Bank Statements with AI

AI assistants like ChatGPT, Claude, and Gemini are increasingly used to
analyse financial data — categorising transactions, spotting patterns,
or preparing summaries for tax returns.

**The risk:** uploading an unredacted statement sends your full account
number, sort code, and transaction history to a third-party server.

**The solution:** anonymise the PDF first. Replace account numbers with
placeholders, scramble names and addresses, and keep only the structural
text the AI needs to understand the format.

### Tips for AI sharing

- Use the **Always Anonymise** table to replace your sort code and
  account number with safe placeholders (e.g., `00-00-00`, `00000000`).
- Keep column headers in the **Never Anonymise** tab so the AI can
  parse the table structure.
- If you need the AI to read transaction descriptions (e.g., for
  categorisation), enable **Retain transaction descriptions** — but
  review the output carefully before sharing.

---

## Sending to Accountants and Bookkeepers

Your accountant needs to see your transactions to prepare accounts or
a tax return. They don't need your full account details.

**The risk:** emailing unredacted statements exposes account numbers
and personal details in transit and in the recipient's inbox.

**The solution:** produce an anonymised version that preserves the
financial data while redacting personal identifiers.

### Tips for professional sharing

- Replace bank names in **Always Anonymise** if the professional
  doesn't need to know which bank the account is with.
- Keep **Never Anonymise** entries for any text the accountant's
  software needs to parse (e.g., balance labels, transaction types).
- Use **batch mode** to anonymise an entire year of statements in
  one go.

---

## Bug Reports and GitHub Issues

openstan is open source, and bugs are reported on GitHub. When a
statement fails to parse, the best way to get help is to attach the
failing PDF — but you can't attach a real statement.

**The risk:** attaching an unredacted statement to a public GitHub
issue exposes your financial data to anyone on the internet.

**The solution:** anonymise the PDF before attaching it. The parser
can still read the structure, and developers can reproduce the issue
without seeing your personal data.

### Tips for bug reports

- Use the **Anonymise** button directly from the Debug Info dialog
  (Import Results → click a REVIEW or FAILURE row). The tool opens
  pre-loaded with the failing statement's path.
- Run the anonymisation, then verify the output still reproduces the
  bug before attaching it to the issue.
- If the bug is in parsing logic, keep **Never Anonymise** entries
  for any text the parser depends on.

---

## Compliance and Data Protection

GDPR, UK Data Protection Act 2018, and similar regulations require
organisations to minimise personal data sharing. Bank statements
contain multiple categories of personal data:

- **Account identifiers** — account numbers, sort codes, card numbers
- **Transaction counterparties** — merchant names, payee references
- **Financial details** — balances, amounts, transaction descriptions
- **Personal information** — names, addresses (on statements with
  letterhead)

**The solution:** anonymising statements before distribution is a
practical way to meet data minimisation obligations while still
sharing the financial information that's needed.

### Compliance checklist

- [ ] Replace all account identifiers with safe placeholders
- [ ] Redact personal names and addresses
- [ ] Review transaction descriptions for embedded personal data
  (e.g., payment references containing names)
- [ ] Keep structural text intact for any downstream parsing
- [ ] Document what redaction was applied and when

---

## Internal Demos and Training

If you're demonstrating openstan or training colleagues, you need
realistic-looking data without using real financial information.

**The solution:** anonymise a real statement to create a demo file
that looks authentic but contains no personal data.

### Tips for demos

- Use **Retain transaction descriptions** to keep the data readable.
- Add your own replacements in **Always Anonymise** to swap in
  fictional names or amounts.
- Save the anonymised file as a reusable demo asset.

---

## Related Use Cases

- [Self Assessment](../use-cases/self-assessment.md) – Export clean data for your tax return
- [Small Business](../use-cases/small-business.md) – Track business expenses throughout the year
- [Multi-Account Tracking](../use-cases/multi-account-tracking.md) – Combine multiple bank accounts
- [All use cases](../use-cases/index.md) – Explore how openstan works for different scenarios

## Next Steps

- **[Installation](../installation.md)** – Download and install openstan
- **[Quick Start](../quickstart.md)** – 5-minute walkthrough to get started
- **[Anonymise PDF Reference](../screens/anonymise.md)** – Full tool documentation
- **[Run Reports](../screens/run-reports.md)** – Build custom transaction reports

---
title: "How to Export Multiple Bank Accounts to One Excel File"
date: 2026-09-22
slug: multi-account-bank-export
description: "Export bank statements from HSBC, NatWest, TSB and more into one Excel file. Step-by-step guide for self-assessment, probate & small business. Free, offline."
tags: [export, excel, multi-account, tutorial]
categories: [how-to]
---

You've got statements from three different banks sitting in your downloads folder. Your self-assessment deadline is approaching, or maybe you're sorting out someone's estate and the solicitor needs everything in one spreadsheet. Copying rows by hand from each PDF is the kind of task that chews up a whole evening and still feels uncertain when you're done.

There's a calmer way. openstan lets you import all your PDFs at once, then export bank statements to Excel in a single file — sorted, labelled by account, no manual copying required.

<!-- more -->

# How to Export Multiple Bank Accounts to One Excel File

## Why this is harder than it looks

Bank PDFs are not designed to talk to each other. HSBC formats its dates one way; NatWest uses a different layout entirely; TSB might split credits and debits into separate columns. If you've ever tried to copy-paste three months of transactions into a single spreadsheet and then discovered a column mismatch on row 47, you'll know exactly what that costs you in time and trust.

The goal here isn't just to export — it's to end up with a single, clean table where every row is correctly attributed to the right account and every date is in the same format. That's what makes the file actually useful to an accountant, a probate solicitor, or HMRC.

## What you'll need before you start

- Your statement PDFs, downloaded from each bank's online portal. Most UK banks let you download up to seven years.
- [openstan installed on your computer](https://openstan.org/installation/) — there's a native installer for Windows, macOS, and Linux; no Python required.
- About five minutes.

You don't need to rename or reorganise anything. openstan extracts the bank name and account type from inside each PDF during processing, then saves its own renamed copies into the project's `statements` folder. Your original files stay untouched, wherever they are.

So you can point openstan at a folder — or several folders — of statements with their original downloaded filenames and it just works. If the same statement appears twice (an easy thing to do when you're gathering from multiple sources), duplicates are harmless: openstan quietly ignores them. And if a statement is missing, it flags the gap for you rather than leaving you to wonder why the numbers don't add up.

```
statements/
├── HSBC_CurrentAccount_Oct2024.pdf
├── HSBC_CurrentAccount_Nov2024.pdf
├── NatWest_Current_Oct2024.pdf
└── TSB_Savings_Oct2024.pdf
```

Messy real-world filenames, all in one folder — that's fine.

## Step 1 — Create a project

Open openstan and click **New Project**. Give it a name that means something later ("2024–25 Tax Year" or "Estate of J. Smith"), then choose a folder to save the project database. Click **Create**. This is where openstan will store the project database and its renamed copies of your statements — keep it somewhere you'll find again.

If you've not done this before, the [Quick Start guide](https://openstan.org/quickstart/) walks through the first project in about five minutes.

## Step 2 — Import all your statements at once

Click **Import Statements**. You can select individual PDFs, or select an entire folder and let openstan work through it. Hold Shift or Ctrl to select multiple files at once.

openstan reads the account name, sort code, and transaction data directly from each PDF. You don't need to tell it which bank you're using — it detects that automatically from the file contents. Twelve months of statements from three banks typically processes in under a minute.

Once the import preview appears, you'll see:

- Each account listed separately, with the bank name openstan detected
- A count of transactions per statement
- Any duplicate warnings — useful if the same period overlaps across two downloads
- Balance verification — openstan checks that opening and closing balances match between consecutive statements

When everything looks right, click **Commit**. See the [Import Results screen guide](https://openstan.org/screens/import-results/) for a full walkthrough of what each flag means.

## Step 3 — Export to Excel

Click **Export Data** (or press `Alt+E`). The Export Data panel gives you three choices for format — Excel, CSV, or JSON — and two choices for type:

| Type | What it produces |
|------|-----------------|
| **Single** | One flat table: every transaction from every account, with an "Account" column to tell them apart. Best for accountants and spreadsheet work. |
| **Multi** | Separate tables for accounts, statements, transactions, balances, and gaps. Best for loading into a database or BI tool. |

For most purposes — self-assessment, probate, or a quick review with your accountant — **Single + Excel** is the right combination. Choose your export folder, click **Export Excel**, and you're done.

The resulting file looks something like this:

| Date | Account | Description | Debit | Credit | Balance |
|------|---------|-------------|-------|--------|---------|
| 2024-10-01 | HSBC Current | Opening Balance | — | 3,200.00 | 3,200.00 |
| 2024-10-03 | HSBC Current | SALARY EMPLOYER LTD | — | 2,800.00 | 6,000.00 |
| 2024-10-07 | NatWest Current | DIRECT DEBIT UTILITIES | 87.50 | — | 1,412.50 |
| 2024-10-12 | TSB Savings | TRANSFER IN | — | 400.00 | 2,900.00 |

Every date is in ISO 8601 format (YYYY-MM-DD), regardless of how each bank originally presented it.

For details on all the export options, see the [Export Data screen guide](https://openstan.org/screens/export-data/).

## Who this helps most

The [Self Assessment use case](https://openstan.org/use-cases/self-assessment/) is the most common reason people reach for this workflow. You've got twelve months of PDFs from your current account — perhaps a savings account too — and your accountant needs a flat file they can sort and filter. Doing it manually is genuinely risky: a missed row or a misread decimal is the sort of thing that causes an amendment down the line.

If you're managing an estate, the [Probate & Estate Admin use case](https://openstan.org/use-cases/probate/) covers some additional considerations — particularly around gathering statements from multiple banks when you're acting as executor.

And if you run a small business with separate personal and business accounts, the [Multi-Account Tracking use case](https://openstan.org/use-cases/multi-account-tracking/) explains how to keep those clearly separated inside the same project.

## What usually trips people up

**"openstan didn't detect my bank correctly."**
A handful of PDFs — especially older ones or those downloaded via a mobile app rather than online banking — can vary in layout. If a statement imports with no transactions, try downloading the same period again from your bank's desktop website. The [Supported Bank Accounts](https://openstan.org/#supported-banks) lists the currently supported formats.

**"Some months are missing."**
openstan flags gaps automatically after you commit. If it shows a gap between November and January, that's your cue to download the missing December statement. You don't have to guess — the gap detection does that check for you.

**"The balances don't match between two statements."**
This usually means two overlapping downloads (e.g., a year-end summary PDF that duplicates transactions from monthly statements). openstan will warn you about duplicates in the import preview. Remove the overlapping file and re-import.

## FAQ

**Do I need to import each bank separately?**
No. You can select PDFs from every bank in a single import batch. openstan reads the account details from each file and keeps them separate in the database. Everything lands in one project, ready to export together.

**Will the export work for HMRC?**
The Excel format openstan produces is a plain `.xlsx` file — the same format accountants and tax agents work with every day. HMRC doesn't mandate a specific format for records you keep yourself; what matters is that the data is accurate and complete. For guidance on what HMRC actually expects, [GOV.UK's self-assessment record-keeping page](https://www.gov.uk/self-assessment-tax-returns/record-keeping) is the authoritative source.

**Can I filter the export to just one account or one date range?**
The Standard Exports tab exports all committed data. For filtered or custom exports — say, just the current account between April and April — see the [Advanced Export screen](https://openstan.org/screens/advanced-export/), which uses TOML configuration files to define precisely what gets included. Alternatively, you can build your own reports for export, specifying columns and filters - see the [Run Reports](https://openstan.org/screens/run-reports/) section of the documentation.

**What if I only have CSV downloads, not PDFs?**
openstan's primary input is PDF bank statements. If your bank provides CSV exports, those are typically already spreadsheet-ready — you may be able to combine them directly in Excel. That said, if you want gap detection, balance verification, and a clean combined view, importing PDFs via openstan is worth the extra step of downloading them from your bank's portal.

**Is my data uploaded anywhere?**
No. openstan processes everything locally on your machine. Nothing is sent to any server. See the [Privacy Policy](https://openstan.org/privacy/) for the formal version, but the short answer is: your statements never leave your computer.

## See Also

- [Multi-Account Tracking use case](https://openstan.org/use-cases/multi-account-tracking/) — how openstan handles multiple banks and account types in one project
- [Self Assessment use case](https://openstan.org/use-cases/self-assessment/) — preparing statements for your tax return
- [Export Data screen guide](https://openstan.org/screens/export-data/) — full reference for export formats and options
- [Advanced Export screen](https://openstan.org/screens/advanced-export/) — custom exports and TOML configuration
- [Installation guide](https://openstan.org/installation/) — get openstan running in a few minutes

---

Ready to try it? [Download openstan](https://openstan.org/installation/) and import your first batch of statements — it typically takes less time than reading this guide.

---
title: "HMRC Bank Statements for Self-Assessment: Complete Guide"
date: 2026-10-05
slug: hmrc-bank-statements-self-assessment
description: "What bank statements does HMRC require for self-assessment? Period, retention and what to keep — plus a step-by-step checklist for sole traders."
tags: [hmrc, self-assessment, bank-statements, tax-return, uk-finance]
categories: [how-to]
---

The self-assessment deadline is 31 January. Most people leave their bank statements until the last few weeks — and many discover too late that what they have isn't quite what HMRC expects.

The confusion is understandable: HMRC doesn't publish a precise checklist of formats and requirements. This guide fills that gap — what you need, what to avoid, how to check for gaps, and how long to keep everything.

<!-- more -->

# HMRC Bank Statements for Self-Assessment: Complete Guide

## Quick reference

| Requirement | Notes |
|-------------|-------|
| Period | Full tax year: 6 April – 5 April |
| Format | Official download from your bank portal (PDF where available) |
| Detail | Individual transactions, not a summary — you must be able to identify each business transaction |
| Balance | Opening and closing balance visible per statement |
| Accounts | All accounts used for business income or expenses |
| Submission | Not submitted with your return — kept in case HMRC asks |

## What HMRC actually requires

HMRC's guidance for self-employed taxpayers is set out on [GOV.UK](https://www.gov.uk/self-employed-records). According to that guidance, you must keep records of all your business income and expenses, and you must be able to "identify business transactions." Bank statements and chequebook stubs are listed explicitly as proof.

In practice, this means:

**The right period.** The UK tax year runs from 6 April to 5 April — not January to December. If you prepare twelve months of January-to-December statements, you're covering the wrong window. You need statements from 6 April 2025 to 5 April 2026 for the 2025–26 tax year. Some sole traders use an accounting period that ends on a different date; if so, use that period consistently and note that you may need to allocate profits across two tax years.

**Individual transactions, not summaries.** GOV.UK requires that your records allow you to identify each business transaction. A monthly summary showing only a closing balance does not allow this. Download full statements that show every transaction, not an account overview page.

**All relevant accounts.** If income flows into your personal current account, that account is relevant. If you pay business expenses from a savings account, that one is too. There is no requirement to merge accounts — you can provide separate statements for each — but you need to include all of them.

**Official downloads, not screenshots.** GOV.UK does not specify a file format, but downloading statements from your bank's official portal (rather than screenshotting your banking app) gives you documents that clearly show the bank's header, account details, and statement period. These are more straightforwardly verifiable if HMRC ever asks to see them. Screenshots can be questioned.

**A note on accounting method.** From the 2024–25 tax year, [cash basis is the default accounting method](https://www.gov.uk/simpler-income-tax-cash-basis) for self-employed taxpayers. Under cash basis, you record income and expenses when money is actually received or paid — which is what bank statements naturally reflect. If you've opted out of cash basis and use traditional accounting, your record-keeping requirements are more extensive: you'll also need records of amounts owed but not yet received, and committed but unpaid expenses.

You do not send statements with your tax return. GOV.UK states this explicitly: "You do not need to send your records in when you submit your tax return." You keep them and show them to HMRC if asked.

## Common mistakes

These are the ones that cause problems if HMRC requests your records:

- ❌ **Incomplete statements** — downloading page 1 of a 6-page statement, or missing the final page where the closing balance appears
- ❌ **Summary view instead of full transactions** — many banking apps show a monthly total rather than individual rows; the full statement is what you need
- ❌ **Wrong date range** — January–December instead of April–April, or missing the final few days of March
- ❌ **Missing a secondary account** — a PayPal account used for business, a savings account where invoices land, a second current account
- ❌ **Gaps between months** — statements end on different days; make sure the closing balance of one month matches the opening balance of the next
- ❌ **Screenshots in place of downloaded statements** — screenshots can be questioned as they don't carry the bank's official document structure

## Step-by-step: preparing your statements

### Step 1 — Identify all relevant accounts

List every account where business income arrives or business expenses leave. This usually includes your main current account and may include savings accounts, a business account, or payment processor accounts like PayPal or Stripe.

If you're unsure whether a particular account is relevant, include it. It's easier to have more than you need than to go back for more later.

### Step 2 — Download the right period

Log in to each bank's online portal and download statements covering 6 April to 5 April. Most banks offer downloads by month or by statement period — download each one in turn.

A few practical notes:

- Banks vary in how long they retain online statements — check your bank's own terms rather than assuming a specific number of years. If you need older statements, contact your bank sooner rather than later.
- If your bank's portal only offers CSV or Excel downloads, request the PDF statements specifically — some banks keep them separately under a "documents" or "statements" section rather than the main account view.
- Download to a dedicated folder named for the tax year, e.g. `Self-Assessment-2025-26/HSBC/`.

### Step 3 — Check for gaps

Lay your statements out in order and verify there are no missing months. Check that the closing balance on one statement matches the opening balance on the next — any discrepancy means either a missing statement or an overlapping download.

If you have multiple accounts, openstan can automate this: import your PDFs and the [gap detection](https://openstan.org/use-cases/self-assessment/) feature flags any missing periods across all accounts at once, so you don't have to check each one manually.

At the time of writing openstan supports Halifax, HSBC, NatWest, and TSB — see the full [supported banks list](https://openstan.org/#supported-banks). If your bank isn't listed, you can [request it](https://github.com/boscorat/bank_statement_parser/issues/new?template=new-bank-request.yml) or [add it yourself via a TOML configuration file](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/) — no coding required.

### Step 4 — Verify each statement is complete

Before filing anything away, spot-check each PDF:

- Does it show individual transactions or just a summary?
- Is the bank's official header present with the account name, sort code, and statement period?
- Is the closing balance on the last page? (It's easy to download an incomplete statement if your bank paginates differently from what you expect.)

### Step 5 — Decide on sharing format

If you're working with an accountant, they may want the statements in spreadsheet form for easier filtering. openstan can export all your statements to a single Excel or CSV file — see the [Export Data guide](https://openstan.org/guides/export-data/) for options.

If you're sharing the PDFs directly, consider anonymising them first. Bank statements contain account numbers and sort codes that your accountant doesn't necessarily need — and may pass on to AI tools or other software. The [anonymise guide](/blog/anonymise-bank-statements/) covers how to do this in a few minutes.

## How openstan helps

If you have statements from more than one account, or you're doing this for the first time and want a safety net, openstan handles the mechanical parts of this workflow:

- **Gap detection** — flags any missing months after you import, across all accounts simultaneously
- **Multi-account support** — imports PDFs from HSBC, NatWest, TSB and others in one batch, keeping each account separate
- **Balance verification** — checks that opening and closing balances match between consecutive statements, catching incomplete downloads before they cause problems later
- **Export to Excel or CSV** — produces a clean flat file your accountant can filter and sort

See the [Self Assessment use case](https://openstan.org/use-cases/self-assessment/) for a full walkthrough, or the [Export Bank Statements from Multiple Accounts](/blog/multi-account-bank-export/) guide for step-by-step instructions.

## How long to keep your statements

[GOV.UK](https://www.gov.uk/self-employed-records/how-long-to-keep-your-records) states that self-employed taxpayers must keep records for at least **5 years after the 31 January submission deadline** for the relevant tax year.

In practice: if you filed your 2022–23 return by 31 January 2024, keep all supporting records until at least 31 January 2029.

If you sent your return more than 4 years after the deadline, you must keep records for 15 months after the date you filed.

If your records are lost, stolen, or destroyed, GOV.UK advises you to do your best to provide figures and tell HMRC if you're using estimated or provisional figures when you file.

Keep original PDFs. An openstan export is useful for working with the data, but it is not a substitute for the official bank statements if HMRC requests records.

## FAQ

**Do I need to send bank statements with my tax return?**  
No. GOV.UK states this directly: "You do not need to send your records in when you submit your tax return." You keep them and produce them if HMRC asks.

**What if I changed banks mid-year?**  
Include statements from both banks for the full tax year, covering the dates when each account was active. Make sure there's no gap between them.

**What if a statement is missing?**  
Contact your bank and request a reissue. Banks vary in how long they retain records and whether they charge for older statements — check with your bank directly. Allow several working days for the request to be processed.

**Do I need to include personal transactions if I use a personal account for business?**  
GOV.UK notes that you might use a personal or business bank account for your business. If business income or expenses pass through a personal account, you'll need records covering those transactions. The cleanest solution going forward is a dedicated business account.

**Can HMRC check my bank records?**  
Yes. GOV.UK's [tax compliance checks](https://www.gov.uk/tax-compliance-checks) page explains that HMRC may check your records to make sure you're paying the right amount of tax. This can include your Self Assessment return. If HMRC contacts you about a compliance check, GOV.UK advises you can have an accountant or legal adviser with you, and you can apply for [alternative dispute resolution](https://www.gov.uk/tax-disputes-alternative-dispute-resolution-adr) if you disagree with their findings.

## Sources

The factual claims in this article are drawn from the following GOV.UK pages, checked October 2026:

- [Business records if you're self-employed — Overview](https://www.gov.uk/self-employed-records)
- [Business records if you're self-employed — What records to keep](https://www.gov.uk/self-employed-records/what-records-to-keep)
- [Business records if you're self-employed — How long to keep your records](https://www.gov.uk/self-employed-records/how-long-to-keep-your-records)
- [Self Assessment tax returns — Deadlines](https://www.gov.uk/self-assessment-tax-returns/deadlines)
- [Cash basis (simpler income tax)](https://www.gov.uk/simpler-income-tax-cash-basis)
- [Tax compliance checks](https://www.gov.uk/tax-compliance-checks)

Practical guidance on file formats, bank portal downloads, and sharing with accountants reflects general good practice rather than specific HMRC requirements.

## See Also

- [Export Bank Statements from Multiple Accounts](/blog/multi-account-bank-export/) — combine statements from several banks into one file
- [How to Redact or Anonymise a Bank Statement](/blog/anonymise-bank-statements/) — before sharing with your accountant or a third party
- [Self Assessment use case](https://openstan.org/use-cases/self-assessment/) — full workflow for preparing your tax return with openstan
- [Export Data guide](https://openstan.org/guides/export-data/) — export options and formats

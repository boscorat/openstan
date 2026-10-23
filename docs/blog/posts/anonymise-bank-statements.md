---
title: "How to Redact or Anonymise a Bank Statement (Free, Step-by-Step)"
date: 2026-10-23
slug: anonymise-bank-statements
description: "Need to share a bank statement but not expose your account details? Learn exactly what to redact, what to keep, and how to do it safely — free, step-by-step."
tags: [bank-statements, privacy, anonymise, redact, mortgage, probate]
categories: [how-to]
---

You need to share your bank statements — with a mortgage lender, a solicitor, or your accountant. But handing over a full statement means exposing your account number, sort code, and every personal transaction note to someone who only needs to verify your balance.

The question isn't whether to redact. It's how much you can remove before the document becomes unverifiable — and what happens if you get that wrong.

<!-- more -->

# How to Redact or Anonymise a Bank Statement (Free, Step-by-Step)

This guide covers exactly what to remove, what you must keep, and how to do it consistently using openstan — a free tool that processes your statements locally, so nothing is uploaded to any server.

## When you might need to anonymise a bank statement

Before getting into the how, it helps to be clear about the situation you're in — because the answer to "how much can I redact?" depends partly on who is receiving the document and why.

Common scenarios:

- **Mortgage application:** Your lender needs to see income deposits and spending patterns. They do not need your full account number, sort code, or personal transaction notes.
- **Probate / estate administration:** You're sharing statements with a solicitor who needs to establish the value of an estate. They need balances and transaction totals, not personal identifiers.
- **Accountant or tax preparer:** They need to see amounts and dates for reconciliation. Personal memos, payee names for private transactions, and account details are rarely relevant.
- **Court proceedings** (e.g. child support, financial disclosure): Proof of funds is required, but you may wish to limit unnecessary personal exposure.
- **Landlord reference:** Showing proof of regular income without revealing everything else in your account.

One scenario worth noting separately: if you're sharing statements with an agent acting on your behalf for HMRC self-assessment, the agent typically needs originals — HMRC requires complete records. For guidance on what HMRC specifically needs, see [HMRC Bank Statements for Self-Assessment](/blog/hmrc-bank-statements-self-assessment/).

A growing concern with any professional sharing is that third parties may feed your documents into AI tools — ChatGPT, Copilot, or similar — to summarise or analyse them. An unredacted bank statement sent to an AI assistant exposes your account number, sort code, and full transaction history to external servers. Anonymising before you share means that risk disappears regardless of what the recipient does with the file.

## What to remove

These are the fields you can safely redact without affecting the document's usefulness for verification purposes.

- ❌ **Full account holder name** — once you've provided identity separately (e.g. a copy of your passport), the name on the statement is redundant
- ❌ **Full account number** — redact to the last 4 digits only; this is enough for the recipient to confirm which account they're looking at
- ❌ **Sort code** — not required to verify balances or transaction history
- ❌ **Bank branch address** — too granular; the bank name is sufficient
- ❌ **Personal transaction memos** — notes you've added yourself (e.g. "Dad's birthday", "holiday spending") have no verification value
- ❌ **Sensitive payee names** — optional and case-by-case; if certain payees are private (medical, legal, personal), you can redact those specific rows

The key principle: remove anything that identifies you personally beyond what is strictly necessary for the recipient's purpose.

## What you must keep

This is the part that generic redaction guides miss entirely. Removing too much makes the document useless — or worse, makes it look tampered with.

- ✓ **Transaction date** — required to establish the period the statement covers
- ✓ **Transaction amount** (debit and credit separately) — the core verification data
- ✓ **Running balance** — this is the most important field to preserve; recipients use it to confirm the statement hasn't been altered, because a genuine statement will always show consistent arithmetic between each row
- ✓ **Bank name and logo** — establishes where the document came from
- ✓ **Account type** (Current / Savings) — provides context for the balance figures
- ✓ **Statement period** (e.g. "1 October – 31 October 2025") — required for date range verification
- ✓ **Opening and closing balance** — always keep these; they're the first thing a lender or solicitor will check

If the running balance column is missing from your anonymised version, expect the document to be rejected or questioned.

## Comparing your options

There are several ways to redact a bank statement PDF. They differ significantly in how consistent they are, how private they are, and how much effort they require.

| Method | Effort | Consistency | Privacy risk | Cost |
|--------|--------|-------------|--------------|------|
| Manual — PDF editor (Adobe, Preview) | High | Low — easy to miss a field | Low — local | Free / paid |
| Print, black pen, rescan | Very high | Very low — error-prone | Low — local | Free |
| Online tool (Smallpdf, iLovePDF, Adobe online) | Medium | Medium | **High** — statement uploaded to third-party server | Free tier / paid |
| openstan built-in anonymisation | Low | High — rule-based, applies consistently | **Low** — local, nothing uploaded | Free |

The privacy risk of online tools deserves a specific note. When you upload a bank statement to Smallpdf, iLovePDF, or Adobe's online service, your document — including account numbers, sort codes, and full transaction history — is transmitted to and processed on their servers. For a document this sensitive, that is a meaningful risk. openstan runs entirely on your own computer. Your statements never leave your machine.

## Step-by-step: anonymise with openstan

openstan is a free desktop tool for reading and exporting bank statement PDFs. The anonymisation feature works directly on your original PDFs — you don't need to import a statement first. If you haven't installed it yet, the [installation guide](https://openstan.org/installation/) takes about five minutes.

**Step 1: Open the Anonymise tool**

Click **Anonymise Statements** in the nav bar (or press Alt+A). The tool opens as a standalone dialog — no project import required.

**Step 2: Select your PDF**

Click **Browse…** to select a single statement, or **Browse Folder…** to process an entire folder at once. Folder mode is useful if you're preparing several months of statements for a mortgage application or probate — openstan processes each one and collects the output in a single `anonymised/` subfolder.

**Step 3: Run it first, then review**

Before adjusting any settings, click **Run Anonymisation** straight away. openstan ships with its own built-in anonymisation rules that handle the most common bank statement patterns — sort codes, account numbers, card numbers, and similar structured data are replaced automatically.

When the run completes, click **Open Original PDF** and **Open Anonymised PDF** to view both side by side. Go through every page of the anonymised version and ask:

- Is anything still visible that shouldn't be? → you'll add it to the Always Anonymise table
- Is any structural text (column headers, balance labels) now unreadable? → you'll add it to the Never Anonymise table

For many statements, the built-in rules are sufficient and no further configuration is needed.

**Step 4: Adjust if needed**

If the first run flagged issues, use the two tabs to tune the output:

The **Always Anonymise** tab adds explicit string replacements that run *before* scrambling. Use it for anything the built-in rules missed — a name, a specific reference, or a branch address that appeared in the output:

| Original Text | Replacement |
|---------------|-------------|
| Jane Smith | Account Holder |
| 11-22-33 | 00-00-00 |
| 12345678 | 00000000 |

The **Never Anonymise** tab protects structural text from being scrambled — column headers, balance labels, statement period text — so the document stays readable:

| Phrase |
|--------|
| Balance Brought Forward |
| Date |
| Money In |
| Money Out |

Click **Run Anonymisation** again, compare both versions once more, and repeat until the output is right. Your changes are saved automatically per project.

**What to think about for your recipient:**

Before finalising, consider what the recipient actually needs to see — and what they don't. The right level of anonymisation varies: a lender may need your name visible to match the statement to your identity, but has no need for your sort code. An accountant may need transaction descriptions but not your account number. A solicitor may need balances and totals but nothing else.

If you're unsure, ask the recipient before you anonymise rather than after. It's easier to share a less-redacted version once than to go back and redo it.

One consideration worth raising: some professionals use AI tools to review or summarise documents. An unredacted bank statement fed into a general-purpose AI assistant exposes your account details, sort code, and full transaction history to third-party servers you have no visibility over. Anonymising before sharing — even with a trusted professional — removes that risk entirely. See [Sharing with AI](https://openstan.org/redaction/#sharing-with-ai) for more on this.

**Step 5: File the output correctly**

Output is saved automatically alongside your originals: single-file mode writes `anonymised_[original filename].pdf` next to the source; folder mode writes everything into an `anonymised/` subfolder inside the folder you selected.

Keep the originals exactly where they are. Do not delete them. HMRC, a court, or a future audit may require the unredacted version, and once you've shared the anonymised copy there is no way to undo that.

For the full reference — including the Retain Descriptions option and config file locations — see the [Anonymise PDFs guide](https://openstan.org/guides/anonymise/).

## If you're doing it manually

If you prefer not to use openstan, or you only have a single statement to deal with, here are the manual options — with their caveats.

**Adobe Acrobat Pro (desktop):** Use the dedicated Redact tool, not the annotation layer. Drawing a black rectangle over text in Acrobat does not remove the text — it merely covers it, and the underlying data is still present in the file. The Redact tool permanently deletes the content. After applying redactions, use "Apply All Redactions" before saving.

**macOS Preview:** The markup tool in Preview is annotation-only. Black shapes drawn over text can be removed or the text searched underneath them. This is not secure redaction. Do not use Preview for anything you intend to share securely.

**Print, black pen, rescan:** Genuinely removes the information, but results in a lower-quality document and is impractical for multi-page statements. The quality loss can itself raise questions.

After any manual redaction method, test it: open the resulting PDF, press Ctrl+F or Cmd+F, and search for your account number. If it appears in the search results, your redaction has not worked.

## Before you send

A few checks worth doing regardless of which method you used:

1. **Read the anonymised version in full** — don't assume the tool got everything; scroll every page
2. **Keep the original safe** — store it separately and don't share the location
3. **Ask the recipient what they actually need** — some mortgage underwriters require unredacted originals; a quick email saves you from having to redo this
4. **Password-protect the export** — if you're sending by email, add a PDF password as an additional layer; share the password separately
5. **Confirm receipt** — ask the recipient to acknowledge the file arrived and is readable

## FAQ

**Can I control exactly what gets anonymised?**  
Yes. The **Always Anonymise** tab lets you specify exact strings to replace with safe placeholders (e.g. your sort code → `00-00-00`). The **Never Anonymise** tab protects structural text from being scrambled. Everything else is scrambled by default — which is the safest starting point for sharing externally.

**Is the anonymisation permanent?**  
The anonymised output file has its text scrambled and specific values replaced — openstan does not store your original statements, and nothing is uploaded anywhere. The original PDF on your computer is untouched. Always keep that original; once you've shared the anonymised copy, you cannot un-share it.

**Will a redacted statement be accepted by my mortgage lender?**  
Most lenders accept redacted PDFs provided the transactions, dates, and running balance are all visible. Some underwriters require originals — it varies by lender and by the stage of the application. Check before you redact, not after.

**What about CSV or Excel exports?**  
This guide covers PDF statements. For CSV or Excel, simply delete the column containing the account number or name before sharing — no special tool needed. Be aware that spreadsheet metadata (document author, edit history) may also contain personal data; check the file properties before sending.

**Does the bank name need to stay visible?**  
Yes. The bank name establishes where the document came from. If a recipient can't tell which institution issued the statement, they have no basis to trust it. Do not remove the bank name or logo.

**Can a redacted PDF be challenged in court?**  
If redaction is done correctly — meaning the underlying data is permanently removed, not just covered — the document should not reveal the hidden information. Legal challenges to redaction typically focus on whether the right information was redacted, not on technical recovery. Using a proper redaction tool (not annotation) is important if the document may be used in legal proceedings.

## See Also

- [HMRC Bank Statements for Self-Assessment](/blog/hmrc-bank-statements-self-assessment/) — what HMRC requires and how to prepare your statements
- [Export Bank Statements from Multiple Accounts](/blog/multi-account-bank-export/) — combine statements from several banks into one file
- [Anonymise PDFs guide](https://openstan.org/guides/anonymise/) — full reference for openstan's anonymisation settings
- [Probate & Estate Admin use case](https://openstan.org/use-cases/probate/) — additional considerations when sharing statements for an estate
- [Privacy Policy](https://openstan.org/privacy/) — openstan does not store or transmit your statements

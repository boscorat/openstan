---
title: How We Identified HSBC Bank Statements — Building a PDF Detective
date: 2026-11-18
slug: hsbc-identifying-bank-statements
description: "Learn how we detect HSBC PDFs automatically using regex and location-based extraction. Step-by-step guide to building bank identification configs."
tags: [bank-statements, pdf-parsing, hsbc, toml, configuration]
categories: [how-to]
---

When parsing 100+ bank statements automatically, the first challenge isn't extracting data—it's knowing which bank you're dealing with. We built an HSBC PDF detective using TOML configuration. Here's how we solved it, and how you can do the same for your bank.

<!-- more -->

# How We Identified HSBC Bank Statements — Building a PDF Detective

## Why PDF Bank Detection Matters

Imagine you have a folder with 25 PDFs: 12 from HSBC, 6 from NatWest, 3 from Barclays, 2 from TSB, and 2 more from smaller banks. You need to parse them all automatically, extract transactions, and produce a consolidated spreadsheet. But here's the catch: each bank uses a different PDF layout. Your parser can't use the same extraction rules on an HSBC statement that it would use on a NatWest one.

The first step in any bank statement parser is **bank identification**. Before you extract balances, account numbers, or transactions, you need to answer a simple question: *Which bank issued this PDF?*

This is where `companies.toml` comes in. It's the first config file your parser loads, and its job is to scan an unknown PDF and determine its origin. Without it, you're flying blind.

## The Solution Overview: `companies.toml`

Every bank config starts with a `companies.toml` file. It's small but crucial—typically 10–15 lines of configuration that tell your parser how to recognize that bank's PDFs.

Here's the high-level flow:

1. Parser receives an unknown PDF
2. Opens page 1 and loads all bank identification rules from `companies.toml` files
3. For each bank, tries to find a unique piece of identifying text (usually somewhere on page 1)
4. If the text is found AND matches a regex pattern, the PDF is identified as that bank
5. Parser stops searching and loads that bank's extraction config
6. Remaining extraction uses that bank's configuration (accounts, tables, field mappings)

This is **Step 1 of the config process**. The [bank_statement_parser reference guide](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/#step-1-register-the-account-type) walks through all 7 steps, but we're focusing on the company identification piece here.

The genius of this approach: identification is fast (milliseconds), and it fails safe. If no bank matches, the user can manually assign one. If multiple banks match (rare), the parser picks the first one and flags it for review.

## Dissecting HSBC's companies.toml

Let's look at what HSBC's bank identifier actually looks like. This is the real config from the openstan project:

```toml
[HSBC_UK]
company = 'HSBC Bank UK'
[HSBC_UK.config]
    config = 'Company Info'
    locations = [
        {page_number = 1, top_left = [475,110], bottom_right = [575, 130]},
        {page_number = 1, top_left = [460,145], bottom_right = [575, 165]},
        {page_number = 1, top_left = [460,165], bottom_right = [575, 185]},
    ]
    field = {field = 'website', vital=true, type="string", string_pattern ='^www\.hsbc\.co\.uk$'}
```

Let's break down each part:

**`[HSBC_UK]`** — This is the unique identifier for the HSBC_UK company config. It must be unique across all banks in your project (you can't have two entries with the same name). This identifier is used later when you define account types.

**`company = 'HSBC Bank UK'`** — A human-readable name. This isn't used for detection; it's just for logging and output. When the parser successfully identifies a statement, it records this name so you know which bank it came from.

**`config = 'Company Info'`** — A label for this extraction step. During parsing, the system logs each step it tries: "Attempting Company Info extraction on HSBC_UK..." This is purely for debugging. If extraction fails, you'll see which step failed.

**`locations` array** — This is where the magic happens. It's an array of rectangular regions (bounding boxes) on page 1 of the PDF. Each location has:
- `page_number = 1` — Always page 1 for company detection (we're identifying the bank, not individual accounts)
- `top_left = [475,110]` — Top-left corner of the rectangle: x=475, y=110 (in PDF points, not pixels—important distinction!)
- `bottom_right = [575, 130]` — Bottom-right corner: x=575, y=130

These coordinates define a small rectangular region on the PDF. The parser will crop to this region and look for text.

**`field = {...}`** — This defines what to extract and how to validate it:
- `field = 'website'` — The name of the field we're extracting (mostly for internal use)
- `vital=true` — This field is mandatory. If extraction fails, the entire company detection fails
- `type="string"` — We're extracting text (not a number or currency)
- `string_pattern ='^www\.hsbc\.co\.uk$'` — The extracted text must match this regex pattern exactly

That regex pattern is strict: `^www\.hsbc\.co\.uk$` means:
- `^` — start of string
- `www\.hsbc\.co\.uk` — literal text "www.hsbc.co.uk" (the backslashes escape the dots so they're literal, not wildcards)
- `$` — end of string

So it matches "www.hsbc.co.uk" and nothing else. No "HSBC Investment", no "m.hsbc.co.uk", no leading/trailing whitespace. Perfect.

## Why Three Locations? (Lessons from Real Statements)

Here's something you'll discover when parsing real-world bank statements: **nothing is perfectly consistent**. 

Different HSBC PDFs might have the website URL in slightly different positions depending on:
- Which HSBC product you're using (current account, savings, credit card)
- Whether it's a joint account (different formatting)
- When the statement was generated (banks redesign PDFs occasionally)

So instead of relying on a single coordinate, the HSBC config has three locations. The parser tries them in order:

1. Try location 1: crop to [475,110] → [575,130], search for text
   - If text found AND matches regex → Success! Bank identified.
   - If not found or doesn't match → continue to location 2
2. Try location 2: crop to [460,145] → [575,165], search for text
   - If text found AND matches regex → Success!
   - If not → continue to location 3
3. Try location 3: crop to [460,165] → [575,185], search for text
   - If text found AND matches regex → Success!
   - If not → Bank detection fails (try next bank's config)

This fallback strategy means the parser can handle slight variations in PDF layout. If HSBC redesigns their statements and the website URL moves 50 pixels down, we update one or two location coordinates instead of rewriting the entire config.

## Regex Patterns: From Loose to Strict

The website URL pattern is just one example. Let's talk about pattern matching in general, because this is where false positives can creep in.

Imagine you wanted a loose regex: `.*hsbc.*`

This would match:
- ✓ "www.hsbc.co.uk"
- ✓ "HSBC Bank UK"
- ✓ "HSBC Investment Management"
- ✓ "Contact HSBC here"

Too loose! You'd accidentally identify non-HSBC PDFs containing the word "HSBC".

A tighter regex: `hsbc\.co\.uk`

Better, but still risky:
- ✓ "www.hsbc.co.uk"
- ✓ "https://hsbc.co.uk"
- ✓ "api.hsbc.co.uk"
- ✓ "m.hsbc.co.uk"

The last two aren't what we want. Mobile and API domains are unlikely to appear on a retail statement.

The strict regex HSBC uses: `^www\.hsbc\.co\.uk$`

Perfect:
- ✓ "www.hsbc.co.uk"
- ✗ "https://www.hsbc.co.uk" (extra text at start)
- ✗ "www.hsbc.co.uk/en" (extra text at end)
- ✗ "api.hsbc.co.uk" (different domain)

This level of specificity is crucial. You want high confidence that you've identified the right bank before proceeding with extraction rules designed specifically for that bank.

**Quick regex cheatsheet for bank configs:**

| Pattern | Matches |
|---------|---------|
| `^text$` | Exact match (nothing before or after) |
| `^text` | Starts with text |
| `text$` | Ends with text |
| `\.` | Literal dot (backslash escapes it) |
| `[A-Z0-9]+` | One or more uppercase letters or digits |
| `\d{2}-\d{2}-\d{2}` | Exactly 2-2-2 digits (e.g., sort code) |
| `\|` | Literal pipe character (backslash escapes it) |

## The Extraction Pipeline: What Happens When the Parser Sees a New PDF

Let's trace through the entire company detection process step-by-step:

1. **User loads a PDF into the parser** (e.g., their HSBC statement from January)
2. **Parser opens page 1** and extracts text
3. **Parser loads the config** — It reads `companies.toml` for all supported banks (HSBC_UK, NatWest_UK, TSB_UK, Barclays_UK, etc.)
4. **For each bank, it tries each location in order:**
   - HSBC_UK, location 1: crop PDF to [475,110] → [575,130]
     - Text found: "www.hsbc.co.uk"
     - Regex check: Does "www.hsbc.co.uk" match `^www\.hsbc\.co\.uk$`? YES ✓
     - **PDF identified as HSBC_UK. Stop searching.**
5. **Parser loads HSBC-specific config** (accounts.toml, statement_types.toml, etc.)
6. **Continue with account identification, balance extraction, transaction extraction** (covered in Posts #2 and #3)

If location 1 had failed (no text found, or text didn't match the regex), the parser would have tried locations 2 and 3 before giving up on HSBC. Only after all HSBC locations are exhausted would it try the next bank's config.

This entire process takes milliseconds. Even with 20+ banks in your config, PDF identification is lightning-fast.

## Common Issues & Troubleshooting

**Q: My HSBC statement isn't being detected. What went wrong?**

A: The coordinates are probably wrong. HSBC might have redesigned their PDFs, or your statement version is different. 
- Open your PDF in a PDF reader
- Manually locate the "www.hsbc.co.uk" text
- Note its approximate position on the page (you can use the PDF viewer's pointer)
- Adjust the coordinates and try again
- Or add a 4th location to the config (more fallback options = better coverage)

**Q: Why use PDF points instead of pixel coordinates?**

A: PDF points are a standard measurement (1/72 inch) built into the PDF format. They're consistent across different viewers and screen resolutions. Pixels are screen-dependent and unreliable for PDF extraction.

**Q: How many locations do I need?**

A: Start with 1–2. If that covers 90% of statements from that bank, you're good. If you encounter variations, add more locations. HSBC uses 3; most banks can do with 2–3. Beyond 5 locations, it's usually better to change your identifying text (find something more consistent).

**Q: Can I use multiple identifying texts (not just the website)?**

A: Yes! You could identify HSBC by its website URL, or by its logo, or by specific header text. If the logo changes positions frequently, you might add another location that looks for a text header instead. Mix-and-match whatever's most reliable for that bank.

## Extending This to Other HSBC Account Types

One thing worth mentioning: this `companies.toml` works for HSBC Current Accounts, Savings Accounts, Credit Cards, and ISAs. They all have "www.hsbc.co.uk" in roughly the same location on page 1. 

The account-type-specific config happens later—in `accounts.toml` (covered in Post #2). Company detection is bank-level; account detection is product-level. This separation of concerns means less duplication and easier maintenance.

## Now It's Your Turn: Building a PDF Detector for Your Bank

Ready to try this for your own bank? Here's the process:

1. **Download a few PDFs from your bank.** (3–5 statements, preferably from different months)
2. **Open one in a PDF viewer** and examine page 1.
3. **Find a unique identifying piece of text:**
   - Bank website (most reliable)
   - Bank name or logo (if consistent)
   - Specific header text unique to that bank
   - Account type label
4. **Note its approximate location** on the page (you're looking for rough coordinates; exact pixel-perfect precision isn't required, we'll refine later).
5. **Write a regex pattern** that matches that text (and nothing else).
6. **Create your first `companies.toml` entry** in a new folder: `project/config/import/YOUR_BANK_COUNTRY/companies.toml`
7. **Test with 3–5 statements:**
   ```bash
   python -m bank_statement_parser identify path/to/pdf.pdf
   ```
8. If detection works: congratulations! Move on to account type detection (Post #2).
   If detection fails: adjust coordinates or regex pattern and retry.

The [bank_statement_parser contributing guide](https://github.com/boscorat/bank_statement_parser/blob/main/CONTRIBUTING.md) has more detail if you get stuck.

---

## Common Issues & Solutions

**Q: What's the difference between top_left and bottom_right?**

A: They define a rectangular bounding box. `top_left = [475,110]` is the top-left corner (x=475, y=110). `bottom_right = [575, 130]` is the bottom-right corner. The parser crops the PDF to this rectangle and searches for text inside. Make sure you're measuring on the right page and accounting for where text actually appears.

**Q: Can I use multiple `companies.toml` files?**

A: No, `companies.toml` must be a single file per bank folder. But you can have multiple banks configured. Each bank gets its own folder (HSBC_UK, NatWest_UK, etc.) with its own companies.toml.

**Q: What if my bank's identifying text changes between statement versions?**

A: Add more locations. If location 1 looks for the website URL and location 2 looks for a logo, you've covered both old and new formats. The parser will try locations in order until one succeeds.

---

## See Also

- [Bank Statement Parser Reference — New Bank Config](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/)
- [Bank Statement Parser Contributing Guide](https://github.com/boscorat/bank_statement_parser/blob/main/CONTRIBUTING.md)
- [How to Extract HSBC Account Details (Post #2)](/blog/hsbc-extracting-account-details/)
- [Understanding PDF Coordinates with pdfplumber](https://github.com/jsvine/pdfplumber)

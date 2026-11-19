---
title: Connecting HSBC Configs Together — The statement_types & standard_fields Layer
date: 2026-11-18
slug: hsbc-connecting-the-pieces
description: "Learn how statement types orchestrate extraction and how raw fields map to standardized output. The final piece of the HSBC parser puzzle."
tags: [bank-statements, statement-types, standard-fields, configuration, hsbc]
categories: [how-to]
---

We've built companies.toml, accounts.toml, and statement_tables.toml. We know how to identify the bank, detect the account type, extract balances, and parse transactions. But how do they all work together? The final layer is statement_types.toml, which orchestrates the extraction pipeline. And then we map raw extracted fields to standard output columns using standard_fields.toml. This post brings everything together.

<!-- more -->

# Connecting HSBC Configs Together — The statement_types & standard_fields Layer

## The Big Picture: Five Config Files, One Complete Parser

Let's zoom out and see the entire architecture:

```
Input: Unknown PDF file
    ↓
companies.toml (Post #1)
  Identify bank: "HSBC_UK" ✓
    ↓
accounts.toml (Post #2)
  Identify account type: "HSBC_UK_CUR_STD" ✓
    ↓
statement_types.toml (Post #4 — this post)
  Choose extraction strategy: "HSBC_UK_CUR"
    ↓
statement_tables.toml (Posts #2–3)
  Extract data using 4 tables:
    - Company info (identification)
    - Account summary (balances)
    - Account details (account holder info)
    - Transactions (line items)
    ↓
standard_fields.toml (Post #4 — this post)
  Map raw fields to standardized output:
    - raw 'date' → STD_DATE (ISO 8601)
    - raw '£_paid_in' → STD_AMOUNT
    - raw 'details' → STD_DESCRIPTION
    ↓
Output: Standardized transaction records (CSV, JSON, Parquet)
```

Each layer depends on the previous one. If company detection fails, nothing else runs. If account detection fails, the parser can't load the right extraction rules. This modular architecture means:

- **Reusability:** Multiple account types use the same statement_type and tables (e.g., both CUR_STD and CUR_ADV use HSBC_UK_CUR)
- **Maintainability:** Each file has a clear responsibility
- **Extensibility:** Adding a new bank or account type doesn't require touching old configs

## Introducing statement_types.toml

After account detection succeeds, the parser needs to know *how* to extract data. This is the job of `statement_types.toml`.

Purpose: **Group extraction rules into two sections — header and lines.**

Here's HSBC's complete statement_types.toml (all 3 account types: current, savings, credit card):

```toml
[HSBC_UK_CUR]
statement_type = 'HSBC UK Current Account'
    [HSBC_UK_CUR.header]
        [[HSBC_UK_CUR.header.configs]]
            config = 'Company Info'
            locations = [
                {page_number = 1, top_left = [475,110], bottom_right = [575, 130]},
                {page_number = 1, top_left = [460,145], bottom_right = [575, 165]},
                {page_number = 1, top_left = [460,165], bottom_right = [575, 185]},
            ]
            field = {field = 'website', vital=true, type="string", string_pattern ='^www\.hsbc\.co\.uk$'}

        [[HSBC_UK_CUR.header.configs]]
            config = 'Statement Info'
            locations = [{page_number=1, top_left = [37, 325], bottom_right = [290, 385]}]
            field = {field = 'statement_date', vital=true, type = "string", string_pattern ='^[1-3]?[0-9]\s[A-Z][a-z]{2,8}\s(\d{4}\s)?to\s[1-3]?[0-9]\s[A-Z][a-z]{2,8}\s[0-9]{4}$'}

        [[HSBC_UK_CUR.header.configs]]
            config = 'Account Info'
            statement_table_key = 'HSBC_UK_CUR_ACCT_SUM'

        [[HSBC_UK_CUR.header.configs]]
            config = 'Account Details'
            statement_table_key = 'HSBC_UK_CUR_ACCT_DET'

    [HSBC_UK_CUR.lines]
        [[HSBC_UK_CUR.lines.configs]]
            config = 'Transaction Lines'
            statement_table_key = 'HSBC_UK_CUR_TRANSACTIONS'

[HSBC_UK_SAV]
statement_type = 'HSBC UK Saving Account'
    [HSBC_UK_SAV.header]
        [[HSBC_UK_SAV.header.configs]]
            config = 'Statement Balances'
            statement_table_key = 'HSBC_UK_CUR_ACCT_SUM'

        [[HSBC_UK_SAV.header.configs]]
            config = 'Statement Info'
            locations = [{page_number=1, top_left = [37, 325], bottom_right = [290, 385]}]
            field = {field = 'statement_date', vital=true, type = "string", string_pattern ='^[1-3]?[0-9]\s[A-Z][a-z]{2,8}\s(\d{4}\s)?to\s[1-3]?[0-9]\s[A-Z][a-z]{2,8}\s[0-9]{4}$'}

        [[HSBC_UK_SAV.header.configs]]
            config = 'Account Info'
            statement_table_key = 'HSBC_UK_SAV_ACCT_DET'

    [HSBC_UK_SAV.lines]
        [[HSBC_UK_SAV.lines.configs]]
            config = 'Transaction Lines'
            statement_table_key = 'HSBC_UK_CUR_TRANSACTIONS'

[HSBC_UK_CRD]
statement_type = 'HSBC UK Credit Card'
    [HSBC_UK_CRD.header]
        [[HSBC_UK_CRD.header.configs]]
            config = 'Statement Balances'
            statement_table_key = 'HSBC_UK_CRD_ACCT_SUM'

        [[HSBC_UK_CRD.header.configs]]
            config = 'Statement Info'
            locations = [{page_number=1, top_left = [120, 470], bottom_right = [250, 500]}]
            field = {field = 'statement_date', vital=true, type = "string", string_pattern ='^[0-3]?[0-9]\s[A-Z][a-z]{2,8}\s[0-9]{4}$'}

        [[HSBC_UK_CRD.header.configs]]
            config = 'Account Info'
            locations = [{page_number=2, top_left = [44, 174], bottom_right = [215, 200]}]
            field = {field = 'account_name', vital=true, type = "string", string_pattern ='^[A-Z]+[a-z]*\s[A-Z]+[a-z]*.*$'}

        [[HSBC_UK_CRD.header.configs]]
            config = 'Card Number'
            locations = [{page_number=2, top_left = [220, 175], bottom_right = [340, 197]}]
            field = {field = 'card_number', vital=true, type = "string", string_pattern ='^[0-9]{4}\s[0-9]{4}\s[0-9]{4}\s[0-9]{4}\s?$'}

    [HSBC_UK_CRD.lines]
        [[HSBC_UK_CRD.lines.configs]]
            config = 'Transaction Lines'
            statement_table_key = 'HSBC_UK_CRD_TRANSACTIONS'
```

Let's break down what's happening:

**`[HSBC_UK_CUR]`** — Identifier (must match statement_type_key in accounts.toml). When the parser identifies account HSBC_UK_CUR_STD, it looks up its `statement_type_key = 'HSBC_UK_CUR'` and loads this section.

**`statement_type = 'HSBC UK Current Account'`** — Human-readable label (used in logs and output).

**`.header` section** — Extraction steps that run once per statement (usually from page 1):
- Company info (bank identification)
- Statement info (statement date range)
- Account summary (opening/closing balances)
- Account details (account holder name, sort code, account number)

**`.lines` section** — Extraction steps that run on every page:
- Transaction lines (individual transactions)

## Separating Header & Lines

**Why have two sections?**

**Header** — Runs once
- Extracts statement-level metadata (opening balance, statement period, account info)
- Usually on page 1 (sometimes page 2 for multi-page statements)
- Example: "This is HSBC, it's John Smith's account, 01 Jan to 31 Jan, opening balance 5000"

**Lines** — Runs on every page
- Extracts data that repeats (transactions)
- Applied to pages 1, 2, 3, etc.
- Example: "50 transactions across 3 pages"

**Benefit:** Efficiency. You don't re-extract the opening balance from every page.

**Diagram:**

```
Statement with 3 pages:

Page 1: [Header extraction + Lines extraction]
        Extract: balance, account info, 15 transactions
        
Page 2: [Lines extraction only]
        Extract: 20 transactions
        
Page 3: [Lines extraction only]
        Extract: 15 transactions

Result: 1 set of metadata + 50 total transactions
```

## What About Different Account Types?

Notice that HSBC_UK_CUR and HSBC_UK_SAV are mostly the same, but HSBC_UK_CRD (credit card) is different:

**HSBC_UK_CUR (current account):**
- Header: Company info, statement date, account summary (HSBC_UK_CUR_ACCT_SUM), account details
- Lines: Transactions (HSBC_UK_CUR_TRANSACTIONS)

**HSBC_UK_CRD (credit card):**
- Header: Company info, statement date, account summary (HSBC_UK_CRD_ACCT_SUM), account name, card number
- Lines: Transactions (HSBC_UK_CRD_TRANSACTIONS)

Differences:
- Credit cards use different balance tables (credit limit, APR, minimum payment instead of opening balance)
- Account info is on page 2, not page 1 (note `page_number=2`)
- Card number extraction is specific to credit cards

**Key insight:** Same bank, different statement_types for different products. Each gets its own extraction strategy tailored to that product's PDF layout.

## Mapping Raw Fields to Standard Output: standard_fields.toml

After extraction, we have raw fields with bank-specific names and formats:
- Raw field: `date` = "03 Jan"
- Raw field: `payment_type` = "CHQ"
- Raw field: `£_paid_in` = "2500.00"

But downstream systems (openstan, accounting software, Excel) need standardized fields:
- Standard field: `STD_DATE` = "2026-01-03" (ISO 8601)
- Standard field: `STD_AMOUNT` = "2500.00"
- Standard field: `STD_DESCRIPTION` = "TESCO CARDIFF"

The `standard_fields.toml` file maps raw → standard. Here's an example:

```toml
[[std_refs]]
statement_type = "HSBC UK Current Account"
config = "Transaction Lines"

[std_refs.standard_fields]
STD_DATE = {from = "date", format = "DD MMM YY"}
STD_AMOUNT = {from = "£_paid_in", default = 0}
STD_AMOUNT_OUT = {from = "£_paid_out", default = 0}
STD_BALANCE = {from = "£_balance"}
STD_DESCRIPTION = {from = "details"}
STD_COMPANY = "HSBC Bank UK"
STD_ACCOUNT_NAME = {from = "account_name"}
STD_SORTCODE = {from = "sortcode"}
STD_ACCOUNT_NUMBER = {from = "account_number"}
```

Each mapping has a type:

**`STD_DATE = {from = "date", format = "DD MMM YY"}`** — Extract from raw field "date", parse using format "DD MMM YY", output as ISO 8601

**`STD_AMOUNT = {from = "£_paid_in", default = 0}`** — Extract from raw field "£_paid_in"; if empty, use default 0

**`STD_COMPANY = "HSBC Bank UK"`** — Hardcoded value (not extracted from PDF)

**`STD_ACCOUNT_NAME = {from = "account_name"}`** — Extract from raw field "account_name", pass through as-is

**Why this layer matters:**

Your parser is bank-specific. HSBC uses different field names and formats than NatWest. But your users want consistent output regardless of bank. Standard fields provide that consistency.

## Date Format Transformations

HSBC transactions have dates like "03 Jan". Your output needs ISO 8601 format: "2026-01-03".

The `format` parameter tells the parser how to interpret HSBC's format:
- `DD` = 2-digit day (01–31)
- `MMM` = 3-letter month (Jan, Feb, Mar, etc.)
- `YY` = 2-digit year (00–99, interpreted as 2000–2099)

Parser extracts "03 Jan", interprets as day=3, month=1, year=26, outputs "2026-01-03".

**Why different banks need different formats:**

Different banks use different date notation:
- HSBC: "03 Jan" (day space month)
- NatWest: "03/01/26" (day/month/year)
- Barclays: "03-JAN-26" (day-month-year)

Standard_fields.toml handles these differences with appropriate format strings. The final output is always ISO 8601.

## Handling Bank-Specific Quirks

Some fields are bank-specific:

```toml
STD_CREDIT_LIMIT = {from = "credit_limit"}  # Only for credit cards
STD_INTEREST_RATE = {from = "apr"}  # Only for savings/credit cards
```

For each statement_type, you define which fields are relevant. The parser only extracts fields that exist in that statement_type's config.

**Static fields:**

```toml
STD_COMPANY = "HSBC Bank UK"  # Same for all HSBC transactions
STD_ACCOUNT_TYPE = "Current Account"  # Varies by account type
```

**Fields with defaults:**

```toml
STD_AMOUNT = {from = "£_paid_in", default = 0}
```

If a transaction has no paid_in value (empty field), use 0. This handles cases where only paid_out has a value.

## End-to-End Validation: From PDF to Standardized Output

Here's the complete flow for a single transaction:

**Step 1: Extract raw fields (statement_tables.toml)**
```
Raw: date="03 Jan", type="CHQ", details="TESCO CARDIFF", 
     out=50.00, in=empty, balance=7450.00 D
```

**Step 2: Parse and validate (field-level rules)**
```
date matches pattern? ✓
type matches pattern? ✓
details not empty? ✓
amount is numeric? ✓
balance is numeric? ✓
```

**Step 3: Map to standard fields (standard_fields.toml)**
```
STD_DATE = parse "03 Jan" with "DD MMM YY" → "2026-01-03"
STD_AMOUNT = £_paid_in = empty, default to 0 → 0.00
STD_AMOUNT_OUT = £_paid_out = 50.00 → 50.00
STD_BALANCE = £_balance = 7450.00 (with D suffix, multiply by -1) → -7450.00
STD_DESCRIPTION = details = "TESCO CARDIFF" → "TESCO CARDIFF"
STD_COMPANY = hardcoded → "HSBC Bank UK"
STD_ACCOUNT_NAME = from account_name → "John Smith"
```

**Step 4: Output (CSV, JSON, Parquet)**
```csv
STD_DATE,STD_COMPANY,STD_ACCOUNT_NAME,STD_AMOUNT,STD_AMOUNT_OUT,STD_BALANCE,STD_DESCRIPTION
2026-01-03,HSBC Bank UK,John Smith,0.00,50.00,-7450.00,TESCO CARDIFF
```

Every transaction goes through this pipeline. The result: consistent, standardized output regardless of the input bank.

## Testing the Full Pipeline

```bash
python -m bank_statement_parser import path/to/HSBC_statement.pdf --output=csv --debug
```

Output CSV columns:
- STD_DATE
- STD_COMPANY
- STD_ACCOUNT_NAME
- STD_AMOUNT
- STD_AMOUNT_OUT
- STD_BALANCE
- STD_DESCRIPTION
- STD_SORTCODE
- STD_ACCOUNT_NUMBER

Validation checks:
- ✓ All dates are ISO 8601 (YYYY-MM-DD)
- ✓ All amounts are numeric
- ✓ Opening balance + movements = closing balance
- ✓ No required fields are empty
- ✓ Account identifies correctly

If any check fails, the transaction is flagged for review or deleted (depending on configuration).

## Extending to Multiple Account Types: The Complete Picture

HSBC_UK has 5 account types. Each has:

| Component | HSBC_UK_CUR_STD | HSBC_UK_CUR_ADV | HSBC_UK_SAV_FLX | HSBC_UK_CRD_RCC |
|-----------|---|---|---|---|
| **accounts.toml** | ✓ Account config | ✓ Account config | ✓ Account config | ✓ Account config |
| **statement_types.toml** | HSBC_UK_CUR | HSBC_UK_CUR | HSBC_UK_SAV | HSBC_UK_CRD |
| **statement_tables.toml** | CUR_ACCT_SUM, CUR_ACCT_DET, CUR_TRANSACTIONS | (same as CUR_STD) | SAV_ACCT_DET, CUR_TRANSACTIONS | CRD_ACCT_SUM, CRD_TRANSACTIONS |
| **standard_fields.toml** | Mapping for HSBC_UK_CUR | (same as CUR_STD) | Mapping for HSBC_UK_SAV | Mapping for HSBC_UK_CRD |

Notice reuse: Both CUR_STD and CUR_ADV use the same statement_type, tables, and standard fields (they have the same PDF layout).

The parser handles this automatically:
1. Identify company: HSBC_UK
2. Identify account: HSBC_UK_CUR_STD or HSBC_UK_CUR_ADV?
3. Load statement_type: HSBC_UK_CUR (same for both)
4. Extract using that strategy
5. Map to standard fields using HSBC_UK_CUR mapping

## Common Integration Issues & Troubleshooting

**Q: Statements extract but dates are wrong in CSV**

A: Check standard_fields.toml date format. If you said `format = "DD MMM YY"` but your PDF actually has "MM/DD/YYYY", dates will be misinterpreted. Test with a known transaction and verify the output.

**Q: Some accounts extract but others don't**

A: Likely different account types with different statement_types. Verify that the account's `statement_type_key` in accounts.toml points to a valid section in statement_types.toml. Missing or misspelled references will fail silently.

**Q: Balance reconciliation fails (opening + movements ≠ closing)**

A: Check numeric_modifiers on balance fields. HSBC uses "D" suffix to indicate inverted balances. If your numeric_modifier isn't applied correctly, reconciliation will fail. Enable debug logging to see calculated vs extracted balances.

**Q: Transactions missing from output**

A: Check the `delete_*` flags in statement_tables.toml. If strict validation is enabled, some transactions might be filtered out. Enable debug logging to see which rows were deleted and why.

## Now It's Your Turn: Putting It All Together

You've learned the full stack. Here's the checklist to build a complete parser for your bank:

✓ **Post #1:** Create companies.toml (bank identification)
✓ **Post #2:** Create accounts.toml + statement_tables.toml for summary (account identification + balance extraction)
✓ **Post #3:** Extend statement_tables.toml with transaction table config
✓ **Post #4:** Create statement_types.toml (orchestration) and standard_fields.toml (output mapping)

**Validation workflow:**

1. **Test company detection:**
   ```bash
   python -m bank_statement_parser identify path/to/pdf.pdf
   ```
   Expected: "HSBC_UK" (or your bank)

2. **Test account detection:**
   ```bash
   python -m bank_statement_parser import path/to/pdf.pdf --dry-run
   ```
   Expected: Account type identified, extraction strategy loaded

3. **Test full extraction:**
   ```bash
   python -m bank_statement_parser import path/to/pdf.pdf --output=csv
   ```
   Expected: CSV with all standard fields populated

4. **Verify output:**
   - Check dates are ISO 8601
   - Check amounts are numeric and correct sign
   - Check balances reconcile
   - Check descriptions are readable

5. **Iterate:**
   - Adjust regex patterns if validation fails
   - Adjust coordinates if tables aren't found
   - Adjust field mappings if output is wrong
   - Re-test after each change

6. **Submit PR:**
   - Test thoroughly with 5–10 different statements
   - Anonymize test PDFs (remove account numbers, names)
   - Create PR to bank_statement_parser repository
   - Include test PDFs and brief description of changes
   - Wait for review & merge
   - Your bank is now supported for all openstan users!

## Contributing Your Config Back

The bank_statement_parser project welcomes new bank contributions. Here's how to share your work:

1. **Clone the repository:** `git clone https://github.com/boscorat/bank_statement_parser.git`
2. **Create a new branch:** `git checkout -b add-your-bank-support`
3. **Add your config files** to `bsp_project/config/import/YOUR_BANK_COUNTRY/`
4. **Create test PDFs** (anonymized; remove sensitive data)
5. **Write a test** in `tests/` to verify your config
6. **Submit PR** with a clear description:
   - Bank and products supported
   - Number of test PDFs included
   - Known limitations (if any)
7. **Engage with reviewers** — maintainers may ask for feedback or adjustments
8. **Merge!** Your bank is now part of the project

---

## Common Issues & Solutions

**Q: Why do I need both statement_types.toml AND accounts.toml?**

A: `accounts.toml` identifies which specific account this is (CUR_STD vs CRD_RCC). `statement_types.toml` defines the extraction strategy. The separation allows multiple accounts to use the same extraction strategy (e.g., both CUR_STD and CUR_ADV use HSBC_UK_CUR).

**Q: How do I test my standard_fields mapping?**

A: Run extraction with --output=csv and inspect the results. Check that:
- Dates are properly formatted (ISO 8601)
- Amounts match the PDF
- Descriptions are readable
- No data is truncated or missing

**Q: What if my bank has variable PDF layouts (different designs for different statement dates)?**

A: Add multiple statement_type entries or use pdfplumber's `allow_text_failover` to handle variations. Document known variations in your contribution PR.

---

## Recap: The Journey

We've walked through the complete journey of building a bank parser:

1. **Post #1:** Identify the bank using unique text markers (companies.toml)
2. **Post #2:** Identify the account type and extract balances (accounts.toml + summary tables)
3. **Post #3:** Extract transactions, handling multi-row entries (transaction tables + bookends)
4. **Post #4:** Orchestrate extraction and standardize output (statement_types.toml + standard_fields.toml)

Each step builds on the previous. Each config file has a clear responsibility. Together, they form a robust system that can parse hundreds of bank PDFs, automatically, with minimal manual intervention.

This is how openstan handles 20+ UK banks. The same architecture can extend to any bank, any country, any financial institution.

## See Also

- [How We Identified HSBC PDFs (Post #1)](/blog/hsbc-identifying-bank-statements/)
- [Extracting HSBC Account Details (Post #2)](/blog/hsbc-extracting-account-details/)
- [Parsing HSBC Transactions (Post #3)](/blog/hsbc-extracting-transactions/)
- [Bank Statement Parser Reference — New Bank Config](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/)
- [Bank Statement Parser Contributing Guide](https://github.com/boscorat/bank_statement_parser/blob/main/CONTRIBUTING.md)
- [openstan Quick Start](https://openstan.org/)

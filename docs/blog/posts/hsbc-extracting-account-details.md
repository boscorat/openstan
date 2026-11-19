---
title: Extracting HSBC Account Details — From Current to Savings to Credit Cards
date: 2026-11-18
slug: hsbc-extracting-account-details
description: "Learn how to extract account type, balances, and account info from HSBC statements using TOML. Covers accounts.toml and statement_tables.toml for summary data."
tags: [bank-statements, account-extraction, balance-extraction, hsbc, toml]
categories: [how-to]
---

Now that we can identify an HSBC PDF, the next challenge is figuring out what kind of account it is. HSBC offers current accounts, savings accounts, credit cards, and ISAs—all with different PDF layouts. We built account-type detection and balance extraction using two more TOML files. Here's how.

<!-- more -->

# Extracting HSBC Account Details — From Current to Savings to Credit Cards

## The Problem: One Bank, Multiple Account Types

Imagine you've successfully identified a PDF as HSBC_UK (from Post #1). But now what? HSBC's current account statements look completely different from their savings account statements, which look different again from their credit card statements. Same bank, three different layouts.

Your parser needs to know:
- **Which account type is this?** (Current, Savings, Credit Card, etc.)
- **Where are the balances?** (Different tables for different products)
- **What fields are available?** (Credit cards have "Credit Limit" and "APR"; current accounts have "Opening Balance")

If you use current-account extraction rules on a credit card statement, the parser will fail—it's looking for fields that don't exist in that layout.

This is where `accounts.toml` and account-specific tables come in. After company detection (Post #1), your parser runs **account detection**. It tries each account type until one matches.

## Identifying Account Type with accounts.toml

Here's HSBC's complete accounts.toml file. It has 5 different account types, each with its own config:

```toml
[HSBC_UK_CUR_STD]
account = "Bank Account"
company_key = 'HSBC_UK'
account_type_key = 'CUR'
statement_type_key = 'HSBC_UK_CUR'
exclude_last_n_pages = 1
currency = "GBP"
    [HSBC_UK_CUR_STD.config]
    config = 'Account Info'
    locations = [{page_number = 1, top_left = [37, 400], bottom_right = [255, 465]}]
    field = {field = 'account', vital=true, type = "string", string_pattern = '^(Your[\s])?Bank[\s]*Account'}

[HSBC_UK_CUR_ADV]
account = "HSBC Advance"
company_key = 'HSBC_UK'
account_type_key = 'CUR'
statement_type_key = 'HSBC_UK_CUR'
exclude_last_n_pages = 1
currency = "GBP"
    [HSBC_UK_CUR_ADV.config]
    config = 'Account Info'
    locations = [{page_number = 1, top_left = [25, 400], bottom_right = [270, 445]}]
    field = {field = 'account', vital=true, type = "string", string_pattern = '^Your[\s]*HSBC[\s]*Advance'}

[HSBC_UK_SAV_FLX]
account = "Flexible Saver"
company_key = 'HSBC_UK'
account_type_key = 'SAV'
statement_type_key = 'HSBC_UK_SAV'
exclude_last_n_pages = 1
currency = "GBP"
    [HSBC_UK_SAV_FLX.config]
    config = 'Account Info'
    locations = [{page_number = 1, top_left = [37, 425], bottom_right = [255, 480]}]
    field = {field = 'account', vital=true, type = "string", string_pattern = '^Your[\s]*Flexible[\s]*Saver'}

[HSBC_UK_SAV_OBS]
account = "Online Bonus Saver"
company_key = 'HSBC_UK'
account_type_key = 'SAV'
statement_type_key = 'HSBC_UK_SAV'
exclude_last_n_pages = 1
currency = "GBP"
    [HSBC_UK_SAV_OBS.config]
    config = 'Account Info'
    locations = [{page_number = 1, top_left = [37, 425], bottom_right = [255, 490]}]
    field = {field = 'account', vital=true, type = "string", string_pattern = '^(Your[\s])?Online[\s]*Bonus[\s]*Saver'}

[HSBC_UK_CRD_RCC]
account = "Rewards Credit Card"
company_key = 'HSBC_UK'
account_type_key = 'CRD'
statement_type_key = 'HSBC_UK_CRD'
exclude_last_n_pages = 1
currency = "GBP"
    [HSBC_UK_CRD_RCC.config]
    config = 'Account Info'
    locations = [{page_number = 1, top_left = [275, 20], bottom_right = [575, 70]}]
    field = {field = 'account', vital=true, type="string", string_pattern ='^Your[\s]*Rewards[\s]*Credit[\s]*Card[\s]*statement[\s]*'}
```

That's 5 account types, all from the same bank (HSBC_UK). Let's break down what each field means:

**`[HSBC_UK_CUR_STD]`** — Unique account ID (must be unique across all banks and accounts in your project). Think of it as the account's fingerprint. This ID is used throughout the config system to link to extraction rules.

**`account = "Bank Account"`** — Human-readable name (the actual product name from HSBC's marketing). Used in logs and output.

**`company_key = 'HSBC_UK'`** — Links this account to the company from Post #1. Must match the `[HSBC_UK]` section in companies.toml.

**`account_type_key = 'CUR'`** — Account type code. Standard codes are:
- `CUR` = Current Account
- `SAV` = Savings Account
- `CRD` = Credit Card
- `ISA` = ISA (tax-advantaged savings)

This is registered in `account_types.toml` (which we won't detail here, but it's just a lookup table of codes to names).

**`statement_type_key = 'HSBC_UK_CUR'`** — Links to extraction strategy (covered in Post #4). Different account types use different statement types. Notice that both CUR_STD and CUR_ADV use the same statement_type (`HSBC_UK_CUR`) because they have the same PDF layout. But credit cards (CRD_RCC) use `HSBC_UK_CRD` because their layout is different.

**`exclude_last_n_pages = 1`** — Ignore the last page when extracting. HSBC typically puts T&Cs and marketing on the final page, which we don't want to parse.

**`currency = "GBP"`** — Account currency (used for numeric parsing). All HSBC_UK accounts are GBP, but if your bank offers multi-currency, this varies per account.

**`.config` section** — Account-type detection logic (similar to company detection from Post #1):
- `locations` — where on the page to look (page 1, specific bounding box)
- `field` — what to extract and validate

The regex pattern for HSBC_UK_CUR_STD is: `^(Your[\s])?Bank[\s]*Account`

This matches:
- ✓ "Bank Account" (no "Your")
- ✓ "Your Bank Account" (with "Your")
- ✓ "Your  Bank  Account" (flexible whitespace)
- ✗ "Your Savings Account" (doesn't match, so this account type isn't selected)

## Why Multiple Account Types in One Config File?

HSBC has 5 account types in a single accounts.toml. The parser tries each one in order until one matches:

1. Try HSBC_UK_CUR_STD: Search for "Bank Account" pattern
   - If found → This is a current account, use HSBC_UK_CUR extraction strategy
2. Try HSBC_UK_CUR_ADV: Search for "HSBC Advance" pattern
   - If found → This is an advance account, use HSBC_UK_CUR extraction strategy
3. Try HSBC_UK_SAV_FLX: Search for "Flexible Saver" pattern
   - If found → This is a savings account, use HSBC_UK_SAV extraction strategy
4. Try HSBC_UK_SAV_OBS: Search for "Online Bonus Saver" pattern
   - If found → This is a savings account, use HSBC_UK_SAV extraction strategy
5. Try HSBC_UK_CRD_RCC: Search for "Credit Card" pattern
   - If found → This is a credit card, use HSBC_UK_CRD extraction strategy

Same bank (HSBC_UK), different account types, different extraction strategies. It's like a decision tree: *"I found an HSBC PDF. Now, is it this product, or this product, or this one?"*

## Extracting Account Balances with statement_tables.toml

We've identified the account type. Now we need to extract data. This is where `statement_tables.toml` comes in.

There are three types of tables in a bank statement:
- **Summary tables** — Fixed-structure tables with known row/column positions (opening balance, payments in/out, closing balance)
- **Detail tables** — Account-holder info (name, sort code, account number)
- **Transaction tables** — Variable-length transaction rows (covered in detail in Post #3)

For now, we're focused on summary and detail tables. Here's the HSBC current account summary table config:

```toml
[HSBC_UK_CUR_ACCT_SUM]
type = "summary"
statement_table = 'Account Summary'
table_columns = 2
table_rows = 4
row_spacing = 7
locations = [
    {page_number=1, top_left = [345, 180], bottom_right = [575, 300], 
     vertical_lines = [360, 475, 475, 550], 
     dynamic_last_vertical_line = {image_id = 0, image_location_tag = "x1"}, 
     allow_text_failover = true},
]
fields = [
    {field = 'opening_balance', cell = {row = 1, col = 1}, vital=true, type = 'currency', numeric_modifier = {suffix = "D", multiplier = -1}},
    {field = 'payments_in', cell = {row = 2, col = 1}, vital=true, type = 'currency'},
    {field = 'payments_out', cell = {row = 3, col = 1}, vital=true, type = 'currency'},
    {field = 'closing_balance', cell = {row = 4, col = 1}, vital=true, type = 'currency', numeric_modifier = {suffix = "D", multiplier = -1}},
]
```

**`type = "summary"`** — This is a fixed-structure table (not variable-length transactions).

**`statement_table = 'Account Summary'`** — Label for this table (for logs).

**`table_columns = 2`** — Expected number of columns (Account Summary typically has 2: a label column and a value column).

**`table_rows = 4`** — Expected number of rows (opening balance, payments in, payments out, closing balance = 4 rows).

**`row_spacing = 7`** — PDF row spacing tolerance. If two rows are within 7 PDF points of each other vertically, they're considered part of the same visual row. This handles slight PDF formatting variations.

**`locations`** — Where to find the table:
- `page_number=1` — On page 1
- `top_left = [345, 180]` — Top-left corner at x=345, y=180
- `bottom_right = [575, 300]` — Bottom-right corner at x=575, y=300
- `vertical_lines = [360, 475, 475, 550]` — Column boundaries at x=360, x=475, and x=550
  - Column 0: x=360 to x=475 (labels like "Opening Balance")
  - Column 1: x=475 to x=550 (values like "5,000.00")
  - The pair `[475, 475]` creates a hard column boundary
- `dynamic_last_vertical_line = {image_id = 0, image_location_tag = "x1"}` — The right edge (x1) of image 0 is used as the rightmost column boundary. Why? HSBC has a logo on the right side of the table, and its position varies slightly. Instead of hardcoding x=550, we let the logo's right edge define the boundary. Smart!
- `allow_text_failover = true` — If column detection fails, try again without explicit vertical_lines. Fall back to pdfplumber's automatic column detection as a safety net.

**`fields`** — What to extract from each cell:
- `field = 'opening_balance'` — Field name
- `cell = {row = 1, col = 1}` — Zero-indexed: row 1 = 2nd row, col 1 = 2nd column
- `vital=true` — Extraction failure means the whole statement fails
- `type = 'currency'` — Parse as a currency value
- `numeric_modifier = {suffix = "D", multiplier = -1}` — If value ends with "D" (debit), multiply by -1 (explained below)

## Cell Addressing & Coordinates Explained

Cell addressing uses 1-based row indexing in this config, so row 1 is the first row of the table:

| Row | Col 0 | Col 1 |
|-----|-------|-------|
| 1 | "Opening Balance" | 5,000.00 CR |
| 2 | "Payments In" | 2,500.00 |
| 3 | "Payments Out" | 1,200.50 |
| 4 | "Closing Balance" | 6,300.00 D |
So `cell = {row = 1, col = 1}` points to "2,500.00" (the second row, second column).

The `vertical_lines` define column boundaries. In HSBC's config: `[360, 475, 475, 550]`

This creates:
- **Column 0:** x=360 to x=475 (labels)
- **Column 1:** x=475 to x=550 (values)

The pair `[475, 475]` is special—it's a zero-width boundary that forces a hard column split. Without it, pdfplumber might merge columns if they're close together. With it, we're saying: "Even if there's no visual gap, treat x=475 as a hard boundary."

## The Mysterious "D" Modifier: Debit vs Credit

Here's something you'll encounter with HSBC: balance fields are marked with a suffix—either "CR" (credit) or "D" (debit).

- "CR" or "D" = Negative balance (you owe money, or the balance is inverted in accounting terms)
- Regular number = Positive balance (you have money)

This is HSBC's notation, but it's unusual. Most systems expect:
- Positive number = you have money
- Negative number = you owe money

The `numeric_modifier` solves this:

```toml
numeric_modifier = {suffix = "D", multiplier = -1}
```

This says: "If the extracted value ends with 'D', strip the 'D' and multiply by -1."

Example:
- Raw from PDF: "5,000.00 D"
- After extraction: 5,000.00 (numeric)
- Check suffix: ends with "D"? Yes
- Apply multiplier: 5,000.00 × -1 = -5,000.00
- Final value: -5,000.00

Downstream systems expect this sign convention, so this transformation is crucial. Without it, you'd have inverted balances (positive when they should be negative, and vice versa).

## Account Detail Tables: Sort Code, Account Number, Name

Beyond balances, we also need to extract account holder info. Here's the account detail table config:

```toml
[HSBC_UK_CUR_ACCT_DET]
type = "detail"
statement_table = 'Account Details'
table_columns = 4
table_rows = 2
locations = [
    {page_number = 1, top_left = [37, 365], bottom_right = [575, 410], vertical_lines = [52, 355, 414, 493, 557]},
]
fields = [
    {field = 'account_name', cell = {row = 1, col = 0}, vital = true, type = "string", string_pattern ='^[A-Z]+[a-z]*\s[A-Z]+[a-z]*.*$'},
    {field = 'sortcode', cell = {row = 1, col = 1}, vital=true, type = "string", string_pattern ='^[0-9]{2}-[0-9]{2}-[0-9]{2}$'},
    {field = 'account_number', cell = {row = 1, col = 2}, vital=true, type = "string", string_pattern ='^[0-9]{8}$'},
]
```

Same structure as the summary table, but we're extracting account holder details. Each field has a regex pattern to validate:

- **`account_name`**: `^[A-Z]+[a-z]*\s[A-Z]+[a-z]*.*$`
  - Matches: "John Smith", "Jane Doe", "A B"
  - Requires at least 2 capital-letter words
  - Accounts for names like "McDonald Smith" (mixed case)

- **`sortcode`**: `^[0-9]{2}-[0-9]{2}-[0-9]{2}$`
  - Matches: "12-34-56" (UK sort code format: 2-2-2 digits)
  - Exactly 6 digits with hyphens in the right places

- **`account_number`**: `^[0-9]{8}$`
  - Matches: "12345678" (UK account numbers are always 8 digits)
  - Exactly 8 digits, no more, no less

If a field doesn't match its pattern, extraction is marked as failed. With `vital=true`, the entire statement fails. This catches parsing errors early and prevents garbage data from reaching your output.

## Putting It Together: The Flow

Here's the complete account detection + extraction flow:

1. **Company detection succeeds** (Post #1) → Identified as HSBC_UK
2. **Account detection starts:**
   - Try HSBC_UK_CUR_STD: Search for "Bank Account" pattern on page 1
   - Pattern matches! Account type identified as HSBC_UK_CUR_STD
3. **Load account configuration:**
   - `account_type_key = 'CUR'` (current account)
   - `statement_type_key = 'HSBC_UK_CUR'` (use this extraction strategy)
4. **Extract balances** using HSBC_UK_CUR_ACCT_SUM table
   - Crop to [345,180] → [575,300]
   - Extract opening_balance from cell [1,1]: "5,000.00 D"
   - Apply numeric_modifier: convert to -5,000.00
   - Extract payments_in, payments_out, closing_balance similarly
5. **Extract account details** using HSBC_UK_CUR_ACCT_DET table
   - Extract account_name, sortcode, account_number
   - Validate against regex patterns
   - If all vital fields pass validation: success
6. **Continue to transaction extraction** (Post #3)

## Testing Your Config: Validation & Troubleshooting

The bank_statement_parser has built-in validation. Here's how to test your account detection:

```bash
python -m bank_statement_parser import path/to/HSBC_statement.pdf --debug
```

Expected output:
```
✓ Company detected: HSBC_UK
✓ Account type detected: HSBC_UK_CUR_STD
✓ Extracted opening_balance: -5000.00
✓ Extracted payments_in: 2500.00
✓ Extracted payments_out: 1200.50
✓ Extracted closing_balance: -6300.00
✓ Extracted account_name: John Smith
✓ Extracted sortcode: 12-34-56
✓ Extracted account_number: 12345678
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| "Account type not detected" | Adjust account pattern regex. Manual PDF inspection: find the exact account type text, refine the pattern. |
| "Coordinate error: Table not found" | Adjust top_left/bottom_right coordinates. Use the PDF viewer's pointer to measure where the table actually appears. |
| "Opening balance extraction failed" | Check numeric_modifier. For HSBC, suffix "D" should trigger multiplier -1. If the PDF uses a different notation, adjust. |
| "Sort code doesn't match pattern" | Your PDF might have a different sort code format (e.g., "12 34 56" instead of "12-34-56"). Update the regex pattern. |
| "Validation error: account_name" | The extracted text doesn't match the regex. Check the PDF—is the account name in a different format than expected? Adjust pattern. |

## Now It's Your Turn: Building Account Detection for Your Bank

Steps to implement for your bank:

1. **Download 3–5 statements from different account types** (if your bank offers them)
2. **Identify the account-type text:**
   - Current account: What unique text identifies it? ("Current Account", "Checking Account", etc.)
   - Savings account: What's unique? ("Savings Account", "High Interest Saver", etc.)
   - Write a distinct regex pattern for each
3. **Note the locations** (page, bounding box coordinates)
4. **Create `accounts.toml`** with one entry per account type
5. **Find the balance table on page 1:**
   - Note column positions (use pdfplumber or measure manually)
   - Identify which rows contain opening/closing balances
   - Create a `statement_tables.toml` entry for the summary table
6. **Find the account detail table:**
   - Account holder name, sort code, account number locations
   - Create another `statement_tables.toml` entry
7. **Test with 3–5 statements:**
   ```bash
   python -m bank_statement_parser import path/to/pdf.pdf --debug
   ```
8. **Adjust patterns, coordinates, and modifiers until all fields extract correctly**

In [Post #3](/blog/hsbc-extracting-transactions/), we tackle the complex case of transaction tables, where things get more interesting.

---

## Common Issues & Solutions

**Q: Why do some HSBC accounts have different balance table positions?**

A: Different account types (current vs savings vs credit card) have different PDF layouts. The balance table might be at different y-coordinates. Solution: use `try_shift_down` parameter to auto-adjust by a small amount if the first location fails.

**Q: What if the account name pattern doesn't match my account?**

A: Your account might have a different name format (titles, hyphens, etc.). Test the regex pattern against your actual PDF text, then adjust. The pattern `^[A-Z]+[a-z]*\s[A-Z]+[a-z]*.*$` is flexible, but modify it if needed.

**Q: How do I find the correct pixel coordinates?**

A: Use a PDF viewer with coordinate display, or use pdfplumber's Python API to programmatically find table positions. Trial and error is fine—test, check the output, adjust by 50 pixels, re-test. You'll converge quickly.

---

## See Also

- [How We Identified HSBC PDFs (Post #1)](/blog/hsbc-identifying-bank-statements/)
- [Parsing HSBC Transactions (Post #3)](/blog/hsbc-extracting-transactions/)
- [Bank Statement Parser Reference — Accounts](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/#step-6-define-accounts)
- [Bank Statement Parser Reference — Summary Tables](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/#summary-table-example)

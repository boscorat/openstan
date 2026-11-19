---
title: Parsing HSBC Transactions — Handling Multi-Row Transactions & Bookends
date: 2026-11-18
slug: hsbc-extracting-transactions
description: "Learn how to extract variable-length HSBC transactions from bank PDFs using bookend detection, pdfplumber column dividers, and multi-row grouping examples"
tags: [bank-statements, transaction-parsing, pdf-extraction, pdfplumber, hsbc]
categories: [how-to]
---

We've identified the bank and extracted account balances. Now comes the hardest part: transactions. HSBC packs each transaction into a table, but here's the problem: not every transaction is one row. Some transactions span 2–3 rows because the description wraps. Figuring out where one transaction ends and the next begins requires a clever technique called "bookend detection." Here's how we solved it.

<!-- more -->

# Parsing HSBC Transactions — Handling Multi-Row Transactions & Bookends

## The Multi-Row Transaction Problem

Let's look at what a real HSBC transaction table looks like (simplified):

```
Row 1:  01 Jan | FPI      | SALARY EMPLOYER      | —    | 2500.00 | 7500.00
Row 2:  03 Jan | CHQ      | TESCO CARDIFF        | 50.00| —       | 7450.00
Row 3:  —     | —        | Reference continues  | —    | —       | —
Row 4:  05 Jan | TRF      | WATER BILL PAYMENT   | 150.00| —      | 7300.00
Row 5:  08 Jan | DD       | ELECTRICITY CO       | 85.00| —       | 7215.00
Row 6:  —     | —        | Account number 999   | —    | —       | —
```

Here's the challenge:
- **Row 1:** One complete transaction (salary payment)
- **Rows 2–3:** One transaction that spans two rows (payment + continuation)
- **Row 4:** One complete transaction
- **Rows 5–6:** One transaction that spans two rows

Your parser needs to group these correctly:
- Transaction 1: Row 1 only
- Transaction 2: Rows 2 + 3 combined
- Transaction 3: Row 4 only
- Transaction 4: Rows 5 + 6 combined

How do you know when to merge rows and when to split? This is where **bookend detection** comes in.

## Understanding Transaction Table Concepts

Before we dive into the config, let's define some terminology:

**Transaction row** — A single complete transaction (might span 1 or more PDF rows)

**PDF row** — A single line in the pdfplumber-extracted table. For multi-row transactions, multiple PDF rows belong to one transaction row.

**Bookend** — A marker that identifies where a transaction starts or ends. For HSBC:
- **Start bookend:** A row where BOTH payment_type AND details have values (e.g., "CHQ" and "TESCO CARDIFF")
- **End bookend:** A row where EITHER paid_out OR paid_in has a value (the actual amount)

**Fill-forward fields** — Fields that repeat across multi-row transactions. The date and payment type usually only appear on the first row of a multi-row transaction; we propagate them to subsequent rows.

**Merge fields** — Fields that need to be combined across rows. If a description spans two rows ("TESCO CARDIFF" on row 1 and "Reference continues" on row 2), we merge them into one field.

## Introducing the Transaction Table Config

Here's HSBC's complete transaction table config. It's large, so we'll break it down piece by piece:

```toml
[HSBC_UK_CUR_TRANSACTIONS]
type = "transaction"
statement_table = 'Transactions'
table_columns = 6
locations = [
    {vertical_lines = [50, 100, 100, 130, 130, 320, 320, 400, 400, 480, 480, 555]},
]
fields = [
    {field = 'date', column = 0, vital=false, type = "string", string_pattern ='^[0-3][0-9]\s?[A-Z][a-z]{2}\s?[0-3][0-9]$'},
    {field = 'payment_type', column = 1, vital=false, type = "string", string_pattern ='(^[A-Z0-9]{1,3}$)|(^[)]{3}$)'},
    {field = 'details', column = 2, vital=true, type = "string", string_pattern ='.+', string_max_length = 100},
    {field = '£_paid_out', column = 3, vital=false, type = "currency"},
    {field = '£_paid_in', column = 4, vital=false, type = "currency"},
    {field = '£_balance', column = 5, vital=false, type = "currency", numeric_modifier = {suffix = "D", multiplier = -1.0000}},
]
delete_success_false = true
delete_cast_success_false = true
delete_rows_with_missing_vital_fields = true

[HSBC_UK_CUR_TRANSACTIONS.transaction_spec]
transaction_bookends = [
    {start_fields = ['payment_type','details'], min_non_empty_start = 2, end_fields = ['£_paid_out','£_paid_in'], min_non_empty_end = 1}
]
fill_forward_fields = ['date','payment_type']
merge_fields = {fields=['details'], separator=' | '}
```

That's a lot! Let's start with the basics.

## Finding Columns Using pdfplumber Coordinates

The `vertical_lines` parameter defines column boundaries:

```toml
vertical_lines = [50, 100, 100, 130, 130, 320, 320, 400, 400, 480, 480, 555]
```

These x-coordinates come in pairs:

| Column | Range | Meaning |
|--------|-------|---------|
| 0 | 50 → 100 | Date column (50 PDF points wide) |
| 1 | 100 → 130 | Payment type column (30 points wide) |
| 2 | 130 → 320 | Details column (190 points wide) |
| 3 | 320 → 400 | Paid out column (80 points wide) |
| 4 | 400 → 480 | Paid in column (80 points wide) |
| 5 | 480 → 555 | Balance column (75 points wide) |

The pair `[320, 320]` (identical x-coordinates) creates a zero-width boundary. This forces a hard column split, ensuring the Details column ends and the Paid Out column begins at exactly x=320, even if there's no visual gap.

**Why not let pdfplumber auto-detect columns?**

pdfplumber can automatically detect columns by looking for gaps in text, but PDF layouts are often imprecise. Explicit boundaries give you full control. If your bank's transaction table has inconsistent spacing, explicit lines ensure consistent extraction.

**How do you find these coordinates?**

Option 1: Use pdfplumber's visual debugging
```python
import pdfplumber

with pdfplumber.open("statement.pdf") as pdf:
    page = pdf.pages[0]
    table = page.extract_table()
    # Inspect page.width, table structure, etc.
```

Option 2: Manual measurement
- Open your PDF in a viewer
- Measure where each column starts/ends
- Trial and error: test, adjust, re-test

## Bookend Detection: Knowing Where Transactions Start & End

This is the core logic that handles multi-row transactions. Here's how it works:

```toml
transaction_bookends = [
    {start_fields = ['payment_type','details'], min_non_empty_start = 2, end_fields = ['£_paid_out','£_paid_in'], min_non_empty_end = 1}
]
```

A bookend definition has four parts:

**`start_fields`** — Fields that mark a transaction start. For HSBC: `['payment_type','details']`

**`min_non_empty_start`** — Minimum number of start_fields that must have values. For HSBC: `2`

This means: A transaction starts when BOTH payment_type AND details have values.

**`end_fields`** — Fields that mark a transaction end. For HSBC: `['£_paid_out','£_paid_in']`

**`min_non_empty_end`** — Minimum number of end_fields that must have values. For HSBC: `1`

This means: A transaction ends when EITHER paid_out OR paid_in has a value.

**Let's trace through our example:**

```
Row 1: date=01 Jan | type=FPI | details=SALARY  | out=—   | in=2500 | bal=7500
  → Starts? type≠empty, details≠empty → YES (2 of 2 start fields)
  → Ends? out=empty, in≠empty → YES (1 of 2 end fields)
  → Result: This is a 1-row transaction ✓
  → Extract: Transaction { date: 01 Jan, type: FPI, details: SALARY, in: 2500, bal: 7500 }

Row 2: date=03 Jan | type=CHQ | details=TESCO   | out=50  | in=—    | bal=7450
  → Starts? type≠empty, details≠empty → YES
  → Ends? out≠empty, in=empty → YES (1 of 2 end fields)
  → Result: This row starts a new transaction ✓

Row 3: date=—     | type=—   | details=contd... | out=—   | in=—    | bal=—
  → Starts? type=empty, details≠empty → NO (need BOTH; only have 1 of 2)
  → Ends? out=empty, in=empty → NO
  → Result: This row doesn't start or end a transaction
  → Conclusion: Row 3 continues the previous transaction (Row 2)
  → Merge with Row 2 ✓
  → Extract: Transaction { date: 03 Jan, type: CHQ, details: TESCO | contd..., out: 50, bal: 7450 }

Row 4: date=05 Jan | type=TRF | details=WATER   | out=150 | in=—    | bal=7300
  → Starts? type≠empty, details≠empty → YES
  → Ends? out≠empty → YES
  → Result: This is a 1-row transaction ✓
  → Extract: Transaction { date: 05 Jan, type: TRF, details: WATER, out: 150, bal: 7300 }

Row 5: date=08 Jan | type=DD  | details=ELEC    | out=85  | in=—    | bal=7215
  → Starts? type≠empty, details≠empty → YES

Row 6: date=—     | type=—   | details=Account | out=—   | in=—    | bal=—
  → Starts? type=empty → NO
  → Merge with Row 5 ✓
  → Extract: Transaction { date: 08 Jan, type: DD, details: ELEC | Account, out: 85, bal: 7215 }
```

Result: 4 transactions extracted correctly, with multi-row transactions merged.

**Why this strategy works:**

- Start fields (payment_type, details) only appear on the first line of a transaction
- Amount fields (paid_out, paid_in) only appear on the last line
- Continuation rows have empty values for these fields
- By checking these markers, we can identify transaction boundaries without hardcoding line counts

## Fill-Forward Fields: Repeating Values Across Rows

In multi-row transactions, the date and payment type only appear on the first row. Row 3 (the continuation of the transaction starting in Row 2) has empty date and payment type fields.

After extraction, we apply fill-forward:

```toml
fill_forward_fields = ['date','payment_type']
```

This propagates values down within each transaction:

```
Before fill-forward:
  Row 2: date=03 Jan, type=CHQ, details=TESCO, out=50
  Row 3: date=—, type=—, details=contd...

After fill-forward:
  Row 2: date=03 Jan, type=CHQ, details=TESCO, out=50
  Row 3: date=03 Jan, type=CHQ, details=contd...  ← Filled in
```

**Why this matters:**

Downstream systems expect every transaction to have a date and type. Without fill-forward, Row 3 would have empty date and type, which would cause validation errors or data corruption.

**Important:** Fill-forward is applied per-page. It doesn't carry across page boundaries. If a transaction spans two pages (rare), you might need to handle it separately.

## Merge Fields: Combining Multi-Row Text

```toml
merge_fields = {fields=['details'], separator=' | '}
```

This combines the details field across rows of the same transaction:

```
Raw extraction:
  Row 2: details="TESCO CARDIFF"
  Row 3: details="Reference continues"

After merge:
  details="TESCO CARDIFF | Reference continues"
```

The separator (' | ') joins them. You could use other separators: ' / ', ' — ', '\n', etc. The goal is to preserve all the text while making it clear there are multiple parts.

**Why this matters:**

Full context is preserved in a single field. When you export to Excel or CSV, each transaction is one row, with details intact.

## Field Validation & Regex Patterns

Each field in the transaction table has a regex pattern:

```toml
{field = 'date', column = 0, vital=false, type = "string", string_pattern ='^[0-3][0-9]\s?[A-Z][a-z]{2}\s?[0-3][0-9]$'},
```

Let's parse this pattern: `^[0-3][0-9]\s?[A-Z][a-z]{2}\s?[0-3][0-9]$`

- `^` — Start of string
- `[0-3][0-9]` — 1–31 (day): First digit 0–3, second digit 0–9
- `\s?` — Optional space
- `[A-Z][a-z]{2}` — 3-letter month: Capital letter followed by 2 lowercase letters (Jan, Feb, Mar, etc.)
- `\s?` — Optional space
- `[0-3][0-9]` — 1–31 (year abbreviated): 00–31
- `$` — End of string

This matches: "01 Jan 26", "1Jan26", "03 Feb 26", etc. Flexible but strict.

**Payment type pattern:** `(^[A-Z0-9]{1,3}$)|(^[)]{3}$)`

This is two alternatives:
- Either 1–3 uppercase alphanumeric chars (FPI, CHQ, TRF, DD) — standard payment types
- OR three parentheses ")" (a special case for certain HSBC transaction types)

**Details pattern:** `.+`

Simple: at least one character. Almost everything matches.

**Amount pattern:** No regex; it's `type = "currency"`, so it's parsed as a number.

**If a field doesn't match its pattern:**
- `vital=true`: The entire row is marked as a failure and deleted from output
- `vital=false`: The field is marked as empty, but the row is kept

For HSBC, most fields are `vital=false` except `details`. The logic: We can live with missing payment type or amount, but every transaction must have a description.

## Currency & Numeric Modifiers (Revisited from Post #2)

HSBC uses separate columns for paid_out and paid_in:

| Transaction | Paid Out | Paid In |
|-------------|----------|---------|
| Salary received | — | 2500.00 |
| ATM withdrawal | 100.00 | — |
| Transfer out | 50.00 | — |

Both are stored as positive values in the PDF. Downstream systems typically expect a single amount column with sign:
- Received £2500 → amount = +2500
- Spent £100 → amount = -100

HSBC doesn't use numeric_modifier on paid_in or paid_out (they're already positive/negative contextually). But the balance column uses it:

```toml
{field = '£_balance', column = 5, vital=false, type = "currency", numeric_modifier = {suffix = "D", multiplier = -1.0000}},
```

Same logic as Post #2: If balance ends with "D", it's inverted (multiply by -1).

## Processing Flags: Row Deletion & Cleanup

After extraction, three flags control which rows are kept:

```toml
delete_success_false = true
delete_cast_success_false = true
delete_rows_with_missing_vital_fields = true
```

**`delete_success_false = true`** — Remove rows where any field has success=false (extraction failed)

If the date pattern doesn't match (success=false for date field), and this flag is true, the entire row is deleted.

**`delete_cast_success_false = true`** — Remove rows where numeric casting failed

If an amount field can't be parsed as a number, the row is deleted.

**`delete_rows_with_missing_vital_fields = true`** — Remove rows with any vital field empty

If `details` is empty (and vital=true), the row is deleted.

These are safety nets: they catch malformed rows before reaching your output. Without them, corrupted data would leak through.

## Testing Your Transaction Config

Here's how to test extraction:

```bash
python -m bank_statement_parser import path/to/HSBC_statement.pdf --debug
```

Expected output:
```
Transaction 1: date=01 Jan, type=FPI, details=SALARY EMPLOYER, in=2500, balance=7500
Transaction 2: date=03 Jan, type=CHQ, details=TESCO CARDIFF | Reference, out=50, balance=7450
Transaction 3: date=05 Jan, type=TRF, details=WATER BILL, out=150, balance=7300
...
```

**Common issues and fixes:**

| Issue | Solution |
|-------|----------|
| "No transactions extracted" | Coordinates or vertical_lines are wrong. The parser can't find the table. Use pdfplumber to debug or manually measure PDF. |
| "Date field failing validation" | The date format in your PDF doesn't match the regex. Check the actual date format, adjust pattern. |
| "Transactions not merged correctly" | Bookend detection logic is wrong. Review start_fields, end_fields, min_non_empty_start/end. Test manually with your PDF. |
| "Details field cut off" | `string_max_length = 100` might be truncating. Increase if needed (but be careful with very long descriptions). |
| "Extra rows appearing in output" | The delete_* flags might be too lenient. Add validation or increase strictness. |

## Handling Variable PDF Layouts

One challenge: banks sometimes change their PDF layouts. If HSBC redesigned their transaction table tomorrow, your config would break.

Strategies to handle this:

1. **Multiple bookends:** Define multiple bookend rules for different layouts. The parser tries each until one works.
2. **Flexible regex patterns:** Use `\s+` (flexible whitespace) instead of exact spaces. Use `[A-Z0-9]{1,5}` instead of hardcoding lengths.
3. **Dynamic column detection:** Use `allow_text_failover = true` to fall back to pdfplumber's automatic column detection if explicit dividers fail.
4. **Versioning:** Keep old configs for old PDF versions. When users submit statements, the parser tries new config first, falls back to old if it fails.

HSBC has done `{vertical_lines = [...], allow_text_failover = true}`, combining explicit boundaries with automatic fallback.

## Now It's Your Turn: Adapting Multi-Row Transaction Extraction

Steps to implement for your bank:

1. **Download a 2–3 page statement** to study the transaction table layout
2. **Identify transaction boundaries:**
   - What fields mark a transaction start? (always filled on first row of transaction)
   - What fields mark a transaction end? (always filled on last row of transaction)
   - For HSBC, it's payment_type + details for start, amount for end
3. **Find column positions:**
   - Use pdfplumber or manual measurement
   - Build the vertical_lines array
4. **Define fields with regex patterns:**
   - Date format (how does your bank format dates?)
   - Payment type or description format
   - Amount format
5. **Create the transaction table config** in statement_tables.toml
6. **Define bookends:** Which fields mark start and end of transactions?
7. **Define fill-forward fields:** Which fields repeat across rows?
8. **Define merge fields:** Which fields need to be combined?
9. **Test with 10–20 transactions:**
   ```bash
   python -m bank_statement_parser import path/to/pdf.pdf --debug
   ```
10. **Refine patterns, coordinates, and logic until satisfied**

In [Post #4](/blog/hsbc-connecting-the-pieces/), we show how all these configs work together, and how to map raw fields to standardized output.

---

## Common Issues & Solutions

**Q: How do I find the exact pixel coordinates for columns?**

A: Use pdfplumber to programmatically extract table structure, or use a PDF viewer that shows coordinates. Trial and error works fine—test, check output, adjust by 10–50 points, re-test. You'll converge quickly.

**Q: Why are some transactions being merged when they shouldn't be?**

A: Your bookend detection is too loose. Review start_fields and end_fields. Make sure min_non_empty_start and min_non_empty_end are strict enough to distinguish real transaction starts/ends from continuation rows.

**Q: What if my bank's transaction table spans multiple pages?**

A: Good news: statement_tables.toml has `locations` without `page_number`, which means the same location is applied to every page. The parser automatically extracts transactions from all pages and combines them.

**Q: Can I extract additional fields (like transaction ID or reference number)?**

A: Yes! Add them to the `fields` array with appropriate column index and regex pattern. The extraction pipeline will handle them like any other field.

---

## See Also

- [How We Identified HSBC PDFs (Post #1)](/blog/hsbc-identifying-bank-statements/)
- [Extracting HSBC Account Details (Post #2)](/blog/hsbc-extracting-account-details/)
- [Connecting the Pieces (Post #4)](/blog/hsbc-connecting-the-pieces/)
- [Bank Statement Parser Reference — Transaction Tables](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/#transaction-table-example)
- [Bank Statement Parser Reference — Bookend Detection](https://boscorat.github.io/bank_statement_parser/latest/guides/new-bank-config/#transactionbookend)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)

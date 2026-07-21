# Testing Guide

## Quick Start

```bash
uv run pytest tests/ -v
```

This runs the full suite. Most tests are self-contained and don't need external data.
Integration tests (16 of 129) skip automatically when anonymised PDFs are unavailable.

---

## Test Categories

| Category | Location | PDFs needed? | Tests |
|---|---|---|---|
| **Unit** | `tests/unit/` | No | ~62 |
| **Contract** | `tests/test_bsp_contract.py` | No | 13 |
| **Serialisation** | `tests/test_pdf_result_serialisation.py` | No | 22 |
| **Integration** | `tests/test_integration.py` | Yes | 16 |

Unit, contract, and serialisation tests are fully self-contained — no external data required.

Integration tests compare the openstan pipeline output against a reference database
built from anonymised bank statements. They skip gracefully when the data isn't available.

### Running specific categories

```bash
# Unit tests only (fastest)
uv run pytest tests/unit/ -v

# BSP contract tests only
uv run pytest tests/test_bsp_contract.py -v

# Integration tests only (skips without PDFs)
uv run pytest tests/test_integration.py -v

# Or use the helper script
uv run python scripts/test_runner.py unit
uv run python scripts/test_runner.py contract
uv run python scripts/test_runner.py integration
```

---

## Testing Your Own PDFs

The easiest way to test your own bank statement PDFs is through the application itself:

1. Open openstan
2. Create or select a project
3. Import your PDF via the Statement Queue

This exercises the full parsing pipeline and provides detailed debugging output for any
extraction issues — no test infrastructure needed.

---

## Integration Tests with Anonymised PDFs

Integration tests require anonymised bank statement PDFs from the private
`bank-statement-data` repository. This is primarily for maintainers with SSH access.

### Setup (one-time)

```bash
git clone git@github.com:boscorat/bank-statement-data.git ../bank-statement-data

ln -s ../bank-statement-data/pdfs/good tests/fixtures/pdfs/anonymised_good
ln -s ../bank-statement-data/pdfs/bad tests/fixtures/pdfs/anonymised_bad
```

### Verify

```bash
uv run pytest tests/ -v 2>&1 | grep "PDF_FIXTURES"
# Should show: [PDF_FIXTURES] Mode: ANONYMISED
```

Without these symlinks, integration tests skip automatically. This is fine for
most development work.

---

## CI Behavior

When you open a pull request, GitHub Actions runs the full test suite:

1. If the `SSH_PRIVATE_KEY_TEST_DATA` secret is available, CI fetches anonymised
   PDFs from the private repository
2. All 129 tests run (integration tests included)
3. A dedicated cleanup job removes all fetched PDFs, symlinks, SSH keys, and
   cache directories — even if tests fail (security measure)

You don't need to do anything special — just open the PR and CI handles the rest.

---

## Pre-PR Checklist

```bash
# 1. Lint
uv run ruff check .

# 2. Format check
uv run ruff format --check .

# 3. Type check
uv run pyrefly check

# 4. Tests
uv run pytest tests/ -v
```

---

## Qt Headless Mode

Tests run headless on CI (no GUI). On Linux without a display, set:

```bash
export QT_QPA_PLATFORM=offscreen
```

This is set automatically in `conftest.py` on Linux CI.

---

## Troubleshooting

### Integration tests are skipping

This is expected when anonymised PDFs aren't available. The tests require real
(but anonymised) bank statement data to build a reference database for comparison.

### Tests are slow on first run

The first run builds the BSP reference project (processes ~45 PDFs). This takes
2-5 minutes. Subsequent runs reuse the cached project.

### Import errors

Reinstall dependencies:

```bash
uv sync
```

### Extra debugging output

```bash
# Show print statements
uv run pytest tests/ -v -s

# Stop on first failure
uv run pytest tests/ -x

# Verbose tracebacks
uv run pytest tests/ --tb=long
```

---

## Related Documentation

- **Security**: [SECURITY.md](./SECURITY.md)
- **BSP Documentation**: [bank_statement_parser](https://github.com/boscorat/bank_statement_parser)
- **Test Data**: Private repo [bank-statement-data](https://github.com/boscorat/bank-statement-data)

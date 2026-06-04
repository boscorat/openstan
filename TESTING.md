# Testing Guide

## Overview

This project contains integration tests that verify the complete openstan pipeline against real (anonymised) bank statement data. Tests require PDF fixtures and are most comprehensive with private repo access.

---

## Test Data Strategy

Tests use a tiered approach:

1. **Anonymised PDFs** (if available via symlinks): Full integration testing with real data structures
2. **Bundled PDFs** (fallback): Functional testing with pre-generated fixtures
3. **None**: Tests skip gracefully with helpful message

### Why Tiered?

- **Security**: Never commit real data to public repos
- **Completeness**: Developers with access get comprehensive testing
- **Accessibility**: All developers can run tests (fallback to bundled)

---

## Running Tests

### Option 1: Full Integration Tests with Anonymised PDFs

Requires SSH access to private `bank-statement-data` repo.

**Step 1: Set up symlinks (one-time)**

```bash
# See detailed setup guide:
# https://github.com/boscorat/bank-statement-data/blob/master/SYMLINK_SETUP.md

# Quick reference for Linux/macOS:
ln -s ~/repos/bank-statement-data/pdfs/good \
      ~/repos/openstan/tests/fixtures/pdfs/anonymised_good

ln -s ~/repos/bank-statement-data/pdfs/bad \
      ~/repos/openstan/tests/fixtures/pdfs/anonymised_bad
```

**Step 2: Verify symlinks**

```bash
ls -la tests/fixtures/pdfs/

# You should see:
# anonymised_good -> ~/repos/bank-statement-data/pdfs/good
# anonymised_bad -> ~/repos/bank-statement-data/pdfs/bad
```

**Step 3: Run tests**

```bash
# Run all tests (may take 2-5 minutes on first run)
uv run pytest tests/ -v

# Output should show:
# [PDF_FIXTURES] Mode: ANONYMISED
# [PDF_FIXTURES] Using ANONYMISED PDFs (symlinks detected)

# Run only integration tests
uv run pytest tests/test_integration.py -v

# Run specific test
uv run pytest tests/test_integration.py::TestImportResults::test_total_pdfs_processed -v
```

### Option 2: Standard Tests with Bundled PDFs

No setup required.

```bash
uv run pytest tests/ -v

# Output should show:
# [PDF_FIXTURES] Mode: BUNDLED
# [PDF_FIXTURES] Using BUNDLED PDFs from installed package
```

---

## Test Structure

```
tests/
├── fixtures/
│   └── pdfs/               # PDF test data (symlinked or bundled)
│       ├── anonymised_good -> ~/bank-statement-data/pdfs/good (if available)
│       ├── anonymised_bad  -> ~/bank-statement-data/pdfs/bad (if available)
│       └── .gitkeep        # Ensures directory exists in git
├── unit/
│   ├── conftest.py         # Unit test fixtures
│   ├── test_base_result_model.py
│   ├── test_paths.py
│   └── ... (other unit tests)
├── conftest.py             # Integration test fixtures
├── test_bsp_contract.py    # BSP API contract tests
├── test_integration.py     # Full pipeline integration tests
├── test_pdf_result_serialisation.py
└── ... (other tests)
```

---

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests for individual components:
```bash
uv run pytest tests/unit/ -v
```

No PDF fixtures required - use mocks.

### Contract Tests (`test_bsp_contract.py`)

Verify compatibility with `bank_statement_parser` API:
```bash
uv run pytest tests/test_bsp_contract.py -v
```

No PDF fixtures required.

### Integration Tests (`test_integration.py`)

Full pipeline tests requiring PDF fixtures:
```bash
uv run pytest tests/test_integration.py -v
```

**With anonymised PDFs**: Verifies complete data flow
**With bundled PDFs**: Verifies basic functionality
**Without PDFs**: Tests skip gracefully

---

## PDF Access

### How Tests Find PDFs

Tests automatically detect:
1. **Anonymised symlinks** (if you set them up) → Use real data
2. **Bundled PDFs** (from installed `bank_statement_parser` package) → Use fallback
3. **Neither** → Skip with helpful message

### Checking Which PDFs You're Using

```bash
uv run pytest tests/ -v 2>&1 | grep "PDF_FIXTURES"

# Example output:
# [PDF_FIXTURES] Mode: ANONYMISED
# [PDF_FIXTURES] Using ANONYMISED PDFs (symlinks detected)
# [PDF_FIXTURES] Location: /home/user/repos/bank-statement-data/pdfs/good
```

### If Tests Skip

```bash
# Check the skip message
uv run pytest tests/ -v -rs  # -rs shows skip reasons

# Example output:
# SKIPPED tests/test_integration.py::TestImportResults - No PDF fixtures available...
```

---

## Qt Headless Mode

Tests run headless on CI/CD (no GUI):

```bash
# This is set automatically in conftest.py on Linux
export QT_QPA_PLATFORM=offscreen

uv run pytest tests/ -v
```

On macOS/Windows, GUI is allowed (if running locally with display).

---

## CI/CD Behavior

When tests run in GitHub Actions:

1. **Fetch Phase**: If SSH key available, clones anonymised PDFs to `/tmp/`
2. **Test Phase**: Runs full integration with anonymised PDFs (if available)
3. **Cleanup Phase**: Removes all PDFs (security: prevent accidental commits)
4. **Fallback**: If SSH unavailable, uses bundled PDFs

---

## Before Submitting PR

```bash
# 1. Linting
uv run ruff check .

# 2. Format check
uv run ruff format --check .

# 3. Type checking (if available)
uv run pyrefly check

# 4. All tests pass
uv run pytest tests/ -v

# Optional: Run only unit tests (faster)
uv run pytest tests/unit/ -v
```

---

## Troubleshooting

### Q: Tests are skipping with "No PDF fixtures available"?

**A:** Tests can't find PDF data. Either:
- Set up symlinks to anonymised PDFs (see Option 1 above), OR
- Ignore it - tests will fall back to bundled PDFs automatically

```bash
# Check what's available
ls -la tests/fixtures/pdfs/
```

### Q: Tests are slow on first run?

**A:** First run builds BSP reference project (expensive). Subsequent runs reuse it. This is expected.

### Q: `QT_QPA_PLATFORM` errors on headless system?

**A:** Should be set automatically. If not:

```bash
export QT_QPA_PLATFORM=offscreen
uv run pytest tests/ -v
```

### Q: Import errors?

**A:** Reinstall dependencies:

```bash
uv sync
```

### Q: How do I run tests with extra debugging?

```bash
# Show print statements
uv run pytest tests/ -v -s

# Extra verbose
uv run pytest tests/ -vv

# Stop on first failure
uv run pytest tests/ -x

# Run with pdb debugger
uv run pytest tests/test_integration.py::TestImportResults -v --pdb
```

---

## Performance Notes

| Scenario | Time | Notes |
|----------|------|-------|
| Full integration suite (anonymised) | 2-5 min | First run builds BSP project (slow), later runs faster |
| Full integration suite (bundled) | 1-2 min | Uses pre-built BSP project |
| Unit tests only | <30 sec | No PDF processing |
| Single integration test | 30-60 sec | Depends on PDF count |

---

## Related Documentation

- **Setup Guide**: [SYMLINK_SETUP.md](https://github.com/boscorat/bank-statement-data/blob/master/SYMLINK_SETUP.md) (private repo)
- **Security**: [SECURITY.md](./SECURITY.md) (if available)
- **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md) (if available)
- **Test Data Hub**: Private repo [bank-statement-data](https://github.com/boscorat/bank-statement-data)
- **BSP Documentation**: [bank_statement_parser](https://github.com/boscorat/bank_statement_parser)

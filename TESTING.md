# Testing Guide for openstan

This guide explains how to run tests in openstan using pytest markers for different testing scenarios.

## Quick Start

### Run all tests
```bash
pytest tests/
```

### Run only synthetic PDF tests (fast, no private repo required)
```bash
pytest tests/ -m synthetic
```

### Run integration tests with BSP
```bash
pytest tests/ -m integration -v
```

### Run specific test file
```bash
pytest tests/test_integration.py -v
```

---

## Available Pytest Markers

### `@pytest.mark.synthetic`
Tests using **synthetic (completely fake) PDFs** committed to this repo.

**When to use**:
- Local development (fast, no setup required)
- CI/CD pipelines (safe, no sensitive data)
- Quick validation of openstan logic

**Example**:
```bash
pytest -m synthetic -v
```

### `@pytest.mark.anonymised`
Tests using **anonymised real PDFs** from the private `bank-statement-data` repo.

**When to use**:
- Validation against real bank statement structures
- Integration testing with actual bank formats
- Pre-release testing

**Requires**:
- SSH access to private `bank-statement-data` repo
- `SSH_PRIVATE_KEY_TEST_DATA` secret configured in CI

**Example**:
```bash
pytest -m anonymised -v
```

### `@pytest.mark.integration`
Tests that validate cross-process integration with bank_statement_parser.

**When to use**:
- Testing openstan's import pipeline
- Validating database output matches BSP
- End-to-end workflow testing

**Example**:
```bash
pytest -m integration -v
```

---

## Test Categories & Recommended Usage

### 1. Development (Local Machine)

Use **synthetic PDFs only** for fast iteration:

```bash
# Run all synthetic tests (fastest)
pytest tests/ -m synthetic -v

# Run specific test file
pytest tests/test_integration.py::test_import_workflow -m synthetic -v

# Run with coverage
pytest tests/ -m synthetic --cov=openstan --cov-report=html
```

**Why**: Synthetic tests are deterministic, fast, and need no SSH setup.

### 2. CI/CD (Pull Requests)

Uses **synthetic PDFs by default**, with optional anonymised PDFs:

```bash
# PR CI runs this (graceful fallback to synthetic if SSH unavailable)
pytest tests/ -v

# Both synthetic and anonymised if SSH secret available
pytest tests/ -m "synthetic or anonymised" -v
```

**Configuration**: See `.github/workflows/ci.yml`

### 3. Release Testing

Uses **both synthetic AND anonymised PDFs** for thorough validation:

```bash
# Run all tests (both synthetic and anonymised)
pytest tests/ -v

# Or explicitly require anonymised tests
pytest tests/ -m anonymised -v
```

**Requirement**: SSH secret `SSH_PRIVATE_KEY_TEST_DATA` must be available.

---

## Test Fixtures

All fixtures are defined in `tests/conftest.py`:

### `qt_app` (session scope)
Provides the global QApplication instance for the entire test session.

**Why**: Ensures view widgets can be instantiated in tests.

**Usage in tests**:
```python
def test_with_qt_widgets(qt_app):
    # Can create PySide6 widgets safely
    widget = MyWidget()
```

### `bsp_harness` (session scope)
Builds the BSP reference project using bundled anonymised PDFs.

**Provides**:
- `harness.db_path` - Path to project.db for comparison
- `harness.project_path` - Path to temporary BSP project
- `harness.batch` - StatementBatch with processing results

**Usage in tests**:
```python
def test_compare_with_bsp(bsp_harness):
    bsp_results = get_bsp_results(bsp_harness.db_path)
    openstan_results = get_openstan_results()
    assert bsp_results == openstan_results
```

### `openstan_env` (session scope, depends on bsp_harness)
Drives the complete openstan import pipeline.

**Provides**:
- `env.project_path` - Path to openstan project
- `env.project_id` - Project UUID
- `env.n_success` - Count of successful imports
- `env.n_review` - Count of CAB review required
- `env.n_failure` - Count of failures
- `env.bsp_n_success` - BSP success count for comparison
- `env.bsp_n_review` - BSP review count for comparison
- `env.processed_pdfs` - List of PdfResult objects

**Usage in tests**:
```python
def test_import_pipeline(openstan_env):
    # Validate openstan produced same results as BSP
    assert openstan_env.n_success == openstan_env.bsp_n_success
    assert openstan_env.n_review == openstan_env.bsp_n_review
```

### `synthetic_pdf_dir` (session scope)
Returns Path to synthetic PDFs committed to this repo.

**Usage in tests**:
```python
def test_with_synthetic_pdf(synthetic_pdf_dir):
    pdf = list((synthetic_pdf_dir / "good").glob("*.pdf"))[0]
    result = import_pdf(pdf)
    assert result.success
```

### `sample_pdf_for_import` (function scope)
Returns a random synthetic PDF for unit tests.

**Usage in tests**:
```python
def test_pdf_metadata_extraction(sample_pdf_for_import):
    if sample_pdf_for_import:
        metadata = extract_metadata(sample_pdf_for_import)
        assert metadata is not None
```

---

## Running Tests with Different Markers

### Combination Patterns

```bash
# Run synthetic OR integration tests
pytest tests/ -m "synthetic or integration" -v

# Run integration tests but not synthetic
pytest tests/ -m "integration and not synthetic" -v

# Run anonymised integration tests
pytest tests/ -m "anonymised and integration" -v

# Run everything except integration
pytest tests/ -m "not integration" -v
```

---

## Test Organization

Tests are organized by functionality:

```
tests/
├── conftest.py                           # Shared fixtures (bsp_harness, openstan_env, etc.)
├── test_integration.py                   # Integration tests (openstan ↔ BSP comparison)
├── test_pdf_result_serialisation.py      # Serialization tests
├── unit/                                 # Unit tests by component
│   ├── models/                           # Model tests
│   ├── presenters/                       # Presenter tests
│   └── ...
└── fixtures/                             # Test data directory
    └── pdfs/                             # Synthetic PDFs (pushed by bank-statement-data)
        ├── good/
        └── bad/
```

### Running by Category

**Integration tests** (BSP comparison):
```bash
pytest tests/test_integration.py -m integration -v
```

**Unit tests** (component-level):
```bash
pytest tests/unit/ -v
```

**Serialization tests**:
```bash
pytest tests/test_pdf_result_serialisation.py -v
```

**Contract validation tests** (BSP API):
```bash
pytest tests/test_bsp_contract.py -v
```

---

## BSP Contract Validation

### test_bsp_contract.py

Validates that BSP's API hasn't changed in breaking ways.

**Test categories**:
- Function existence (process_pdf_statement, update_db, etc.)
- Result types (Success, Review, Failure classes)
- Exception types (ProjectError, StatementError, etc.)
- Version compatibility (bsp==0.2.1b7)
- TestHarness API

**Why important**: Detects breaking changes in BSP at test time, not in production.

**Run contract tests**:
```bash
pytest tests/test_bsp_contract.py -v
```

**Expected output**:
```
test_process_pdf_statement_exists PASSED
test_update_db_exists PASSED
test_result_classes_exist PASSED
test_pdf_result_has_required_fields PASSED
test_expected_exceptions_exist PASSED
test_bsp_version_is_expected PASSED
test_test_harness_exists PASSED
test_test_harness_context_manager PASSED
test_test_harness_callable PASSED

======================== 9 passed in 0.04s =========================
```

---

## Continuous Integration

### Development/PR CI (.github/workflows/ci.yml)

Runs tests with synthetic PDFs; gracefully falls back if anonymised unavailable:

```yaml
- name: Fetch anonymised PDFs for testing (graceful fallback)
  continue-on-error: true
  if: secrets.SSH_PRIVATE_KEY_TEST_DATA != ''
  run: |
    # Attempts to clone private bank-statement-data repo
    # Falls back to synthetic if SSH key unavailable
    
- name: Test (pytest)
  run: uv run pytest tests/ -v
  env:
    QT_QPA_PLATFORM: offscreen
```

**Result**: ✅ PR passes even without anonymised PDFs.

### Release CI

Would enforce anonymised PDFs before release (future enhancement).

---

## Troubleshooting

### No tests collected (marker mismatch)

**Problem**: `pytest -m unknown_marker` collects 0 items

**Solution**: List available markers:
```bash
pytest --markers
```

Expected output includes:
```
@pytest.mark.synthetic: tests using synthetic PDFs (fast, CI-safe)
@pytest.mark.anonymised: comparison tests using anonymised PDFs (requires CI secret)
@pytest.mark.integration: cross-process tests with BSP
```

### Tests fail with "Qt platform plugin not found"

**Problem**: `Could not find the Qt platform plugin`

**Solution**: Set headless mode:
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/ -v
```

Or use uv (automatically sets this):
```bash
uv run pytest tests/ -v
```

### Tests fail with "No anonymised PDFs found"

**Problem**: Some tests require anonymised PDFs but they're not available

**Solution**: Use synthetic-only tests during development:
```bash
pytest tests/ -m synthetic -v
```

### Import errors

**Problem**: `ModuleNotFoundError: No module named 'openstan'`

**Solution**: Install dependencies:
```bash
uv sync --group dev
uv run pytest tests/ -v
```

### Database lock errors in openstan_env

**Problem**: `SQLite database is locked`

**Solution**: Ensure only one test session runs at a time:
```bash
# Don't use pytest-xdist with -n flag
pytest tests/ -v  # ✓ Correct

pytest tests/ -n 4  # ✗ Will cause lock errors
```

---

## Test Development Workflow

When writing new tests:

1. **Use `@pytest.mark.synthetic` by default** (fastest):
   ```python
   @pytest.mark.synthetic
   def test_new_feature(synthetic_pdf_dir):
       pdf = list((synthetic_pdf_dir / "good").glob("*.pdf"))[0]
       # Test new feature
   ```

2. **Use `@pytest.mark.integration`** for BSP comparison:
   ```python
   @pytest.mark.integration
   def test_import_matches_bsp(openstan_env):
       assert openstan_env.n_success == openstan_env.bsp_n_success
   ```

3. **Use `@pytest.mark.anonymised`** for real-world edge cases:
   ```python
   @pytest.mark.anonymised
   def test_edge_case_with_real_pdf(anonymised_pdf_dir):
       # Test with real bank statement structure
   ```

4. **Combine markers** if test should pass in all scenarios:
   ```python
   @pytest.mark.synthetic
   @pytest.mark.anonymised
   def test_core_import_logic(sample_pdf_for_import):
       # Works with any valid PDF
   ```

---

## Version Pinning

openstan is pinned to specific versions to prevent silent version drift:

- **bank_statement_parser**: `==0.2.1b7` (tight coupling for stability)
- **bank_statement_anonymiser**: `==0.1.1`

When BSP or anonymiser updates, both version pins must be updated and all tests must pass before release.

---

## Further Reading

- [pytest markers documentation](https://docs.pytest.org/en/stable/how-to.html#marking-whole-classes-or-modules)
- [Conftest.py guide](https://docs.pytest.org/en/stable/conftest.html)
- [Test fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [Central PDF strategy](../../bank-statement-data/README.md)
- [BSP Testing Guide](../bank_statement_parser/TESTING.md)
- [Anonymiser Testing Guide](../bank_statement_anonymiser/TESTING.md)

# Phase 3: Git Workflow Guide

## Branch Strategy Overview

This document outlines the exact Git workflow for Phase 3 implementation.

**Base branch:** `logging`  
**Final merge:** `logging` → `master`  
**Number of parts:** 7 (A, B, C, D, E, F, G)  
**Number of intermediate PRs:** 7 (one per part)  
**Final PR:** 1 (logging → master)

---

## Step-by-Step Workflow

### Setup (Before any part)

```bash
# Ensure you're on the logging branch
git checkout logging
git pull origin logging

# Verify logging branch is up to date
git log --oneline -5
```

---

### For Each Part (A through G)

#### 1. Create DEV Branch
```bash
# Replace <PART> with A, B, C, D, E, F, or G
git checkout -b logging-phase3-<PART>-DEV logging

# Verify you're on the new branch
git branch -v
```

#### 2. Implement Changes
- Follow the deliverables in `LOGGING_PLAN_PHASE_3.md` for that part
- Update the checkboxes in the plan document as you complete each deliverable
- Commit frequently with clear messages following [Conventional Commits](https://www.conventionalcommits.org/)

**Commit message format:**
```
<type>(<scope>): <description>

<type> options: feat, fix, docs, refactor, test, chore
<scope> examples: logging_manager, log_viewer_dialog, admin_presenter

Examples:
  feat(logging_manager): implement logger factory with verbosity levels
  feat(log_viewer_dialog): add privacy warning and 500-line truncation
  refactor(statement_result_presenter): replace print calls with logging
  test(logging): add integration tests for context switching
```

#### 3. Run Pre-PR Checks
```bash
# Lint
uv run ruff check .

# Format check (and auto-fix if needed)
uv run ruff format --check .
uv run ruff format .  # if needed

# Type check
uv run pyrefly check

# Tests
uv run pytest tests/ -v

# Verify all pass before proceeding!
```

#### 4. Create PR to `logging` Branch
```bash
# Make final commit if needed
git add .
git commit -m "final: complete part <PART>"

# Push to origin
git push origin logging-phase3-<PART>-DEV

# Create PR (via GitHub CLI or web interface)
gh pr create \
  --base logging \
  --head logging-phase3-<PART>-DEV \
  --title "feat: phase 3 part <PART> — <description>" \
  --body "Implements deliverables from LOGGING_PLAN_PHASE_3.md Part <PART>"
```

#### 5. Review & Address Feedback
- Wait for review (self-review is acceptable)
- Address any comments or requested changes
- Commit changes: `git commit -m "review: address feedback"`
- Push: `git push origin logging-phase3-<PART>-DEV`

#### 6. Merge to `logging`
```bash
# Option A: Merge via GitHub (recommended for visibility)
# Go to PR page, click "Merge pull request"

# Option B: Merge via CLI
git checkout logging
git pull origin logging
git merge logging-phase3-<PART>-DEV
git push origin logging
```

#### 7. Clean Up
```bash
# Delete local DEV branch
git branch -d logging-phase3-<PART>-DEV

# Delete remote DEV branch
git push origin --delete logging-phase3-<PART>-DEV
```

#### 8. Verify Merge
```bash
# Ensure you're back on logging
git checkout logging
git pull origin logging

# Verify the merge worked
git log --oneline -5
```

---

## Timeline Example

### Week 1: Part A
```bash
# Monday
git checkout -b logging-phase3-A-DEV logging
# ... implement logging_manager.py and log_viewer_dialog.py ...
uv run ruff check . && uv run ruff format . && uv run pyrefly check && uv run pytest tests/
gh pr create --base logging --head logging-phase3-A-DEV ...

# Wednesday (after review)
git checkout logging
git merge logging-phase3-A-DEV
git push origin logging
git push origin --delete logging-phase3-A-DEV
```

### Week 2: Part B
```bash
# Thursday
git checkout -b logging-phase3-B-DEV logging
# ... implement admin_view.py and admin_presenter.py ...
# ... [same commit/check/PR flow] ...
```

...and so on through Part G

---

## Final Integration: logging → master

After all 7 parts are merged into `logging`:

```bash
# Ensure logging is up to date
git checkout logging
git pull origin logging

# Verify all changes are present
git log --oneline logging ^master | head -20

# Create final PR
gh pr create \
  --base master \
  --head logging \
  --title "feat: phase 3 complete — openstan logging integration" \
  --body "Completes Phase 3: Integrates logging infrastructure, admin UI, and documentation.

  Includes 7 parts:
  - Part A: logging_manager and log_viewer_dialog
  - Part B: Admin UI extensions (View Logs, Logging Settings)
  - Part C: Context switching (app ↔ project logs)
  - Part D: Replace print() calls with logging
  - Part E: Verbosity cascade to library loggers
  - Part F: User documentation
  - Part G: Integration tests

  All intermediate PRs have been reviewed and merged to logging branch."
```

### Before Merging to Master
1. Review all commits: `git log --oneline logging ^master`
2. Run full test suite one more time: `uv run pytest tests/ -v`
3. Verify documentation is complete: `ls docs/admin/logging.md docs/troubleshooting.md`
4. Check all pre-PR items:
   - `uv run ruff check .` ✅
   - `uv run ruff format --check .` ✅
   - `uv run pyrefly check` ✅
   - `uv run pytest tests/ -v` ✅

### Merge to Master
```bash
# Via GitHub (recommended)
# Go to PR page, click "Merge pull request", confirm

# Via CLI
git checkout master
git pull origin master
git merge logging
git push origin master
```

---

## Troubleshooting

### "I accidentally committed to logging instead of logging-phase3-A-DEV"
```bash
# Create the DEV branch pointing to current location
git branch logging-phase3-A-DEV

# Reset logging to its previous state
git checkout logging
git reset --hard origin/logging

# Switch to DEV branch and continue
git checkout logging-phase3-A-DEV
```

### "My DEV branch is out of sync with logging"
```bash
git checkout logging-phase3-A-DEV
git fetch origin
git rebase origin/logging
git push --force-with-lease origin logging-phase3-A-DEV
```

### "I need to discard all changes on a DEV branch"
```bash
git checkout logging-phase3-A-DEV
git reset --hard origin/logging
```

### "How do I see what changed between my DEV branch and logging?"
```bash
git diff logging..logging-phase3-A-DEV
# or
git log logging..logging-phase3-A-DEV
```

---

## Key Reminders

1. ✅ **Always create a new DEV branch** from `logging` for each part
2. ✅ **Never commit directly to `logging`** (use DEV branches only)
3. ✅ **Run all checks** before each PR
4. ✅ **One PR per part** (7 PRs, then 1 final)
5. ✅ **Update LOGGING_PLAN_PHASE_3.md** checkboxes as you go
6. ✅ **Merge each PR before starting the next part** (keeps dependencies clean)
7. ✅ **Delete DEV branches after merging** (keeps repo clean)

---

## Command Cheat Sheet

```bash
# Create DEV branch
git checkout -b logging-phase3-<PART>-DEV logging

# View current branch
git branch -v

# Pre-PR checks
uv run ruff check . && uv run ruff format . && uv run pyrefly check && uv run pytest tests/

# Push and create PR
git push origin logging-phase3-<PART>-DEV
gh pr create --base logging --head logging-phase3-<PART>-DEV ...

# Merge to logging
git checkout logging && git merge logging-phase3-<PART>-DEV && git push origin logging

# Clean up
git branch -d logging-phase3-<PART>-DEV
git push origin --delete logging-phase3-<PART>-DEV

# Final PR to master
gh pr create --base master --head logging ...
```

---

Ready to start Part A? Let me know when you're ready, and I'll help you create the first DEV branch!

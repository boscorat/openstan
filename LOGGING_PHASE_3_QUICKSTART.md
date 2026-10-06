# Phase 3: Quick Start Guide

## You have two comprehensive documents to guide you:

### 📋 `LOGGING_PLAN_PHASE_3.md` (25 KB, 658 lines)
**Detailed implementation plan for all 7 parts (A-G)**

Contains:
- Design decisions (locked in)
- 15 detailed implementation steps grouped into 7 parts
- Each step includes: objective, deliverables, key methods, implementation notes, and PR title
- Execution order and timeline
- Success criteria and checkpoints
- Testing strategy

**Use this to:** Understand what needs to be built, follow step-by-step, track progress with checkboxes

---

### 🌳 `LOGGING_PHASE_3_GIT_WORKFLOW.md` (7.3 KB)
**Git workflow guide for the 7-PR approach**

Contains:
- Branch strategy overview
- Step-by-step workflow for each part (create branch → implement → check → PR → merge)
- Timeline example
- Final integration to master
- Troubleshooting commands
- Cheat sheet

**Use this to:** Execute the Git workflow, merge code, stay organized

---

## Quick Start: Part A (Foundation)

Ready to begin? Here's the 2-minute setup:

### Step 1: Set up DEV branch
```bash
cd <openstan-repo>
git checkout logging
git pull origin logging
git checkout -b logging-phase3-A-DEV logging
git branch -v  # Verify you're on the new branch
```

### Step 2: Open the implementation plan
```bash
cat LOGGING_PLAN_PHASE_3.md | grep -A 100 "Part A: Foundation"
```

### Step 3: Implement Part A (2 steps)

**A.1: Create `src/openstan/logging_manager.py`**
- Follow the detailed spec in LOGGING_PLAN_PHASE_3.md (section "Part A.1")
- Implement the logger factory, context switching, and cleanup logic
- Remember: cascade verbosity to library loggers!

**A.2: Create `src/openstan/dialogs/log_viewer_dialog.py`**
- Follow the detailed spec in LOGGING_PLAN_PHASE_3.md (section "Part A.2")
- Modal dialog with privacy warning, 500-line truncation, refresh/copy buttons

### Step 4: Run checks
```bash
uv run ruff check .
uv run ruff format --check . && uv run ruff format .  # if needed
uv run pyrefly check
uv run pytest tests/ -v
```

### Step 5: Create PR
```bash
git push origin logging-phase3-A-DEV
gh pr create \
  --base logging \
  --head logging-phase3-A-DEV \
  --title "feat: phase 3 part A — logging_manager and log_viewer_dialog" \
  --body "Implements Part A deliverables from LOGGING_PLAN_PHASE_3.md"
```

### Step 6: Merge when ready
```bash
# After review (or self-review)
git checkout logging
git pull origin logging
git merge logging-phase3-A-DEV
git push origin logging
git branch -d logging-phase3-A-DEV
git push origin --delete logging-phase3-A-DEV
```

---

## Current Status

**Phase 1:** ✅ COMPLETED (bank_statement_parser logging)
**Phase 2:** ✅ COMPLETED (uk-bank-statement-anonymiser logging)
**Phase 3:** 📋 READY FOR EXECUTION (this phase)
**Phase 4:** ⏳ PENDING (integration tests)

**Total effort remaining:** ~12-15 hours (code) + 2-3 hours (docs)

---

## Document Organization

All three planning documents are in the repo root:

```
<openstan-repo>/
├── LOGGING_PLAN.md                    # Overall plan (phases 1-4)
├── LOGGING_PLAN_PHASE_3.md            # Detailed Phase 3 spec ← USE THIS
├── LOGGING_PHASE_3_GIT_WORKFLOW.md    # Git workflow guide ← USE THIS
├── src/openstan/
│   ├── logging_manager.py             # (to create in Part A.1)
│   ├── views/
│   │   ├── log_viewer_dialog.py        # (created in Part A.2)
│   │   └── admin_view.py              # (to update in Part B.1)
│   ├── presenters/
│   │   ├── admin_presenter.py         # (to update in Part B.2)
│   │   ├── stan_presenter.py          # (to update in Part C.1)
│   │   └── statement_result_presenter.py # (to update in Part D.1)
│   └── main.py                        # (to update in Part C.2)
└── docs/
    ├── admin/
    │   └── logging.md                 # (to create in Part F.1)
    └── troubleshooting.md             # (to create in Part F.2)
```

---

## Need Help?

**Question about what to implement?**
→ Check LOGGING_PLAN_PHASE_3.md, find the relevant Part section

**Question about Git workflow?**
→ Check LOGGING_PHASE_3_GIT_WORKFLOW.md, find the relevant step

**Blocked or uncertain?**
→ Ask with the Part number and step number (e.g., "Help with Part A.1: logging_manager.py, specifically the cascade logic")

---

## Next Steps

1. **Read** `LOGGING_PLAN_PHASE_3.md` (5-10 min overview)
2. **Read** `LOGGING_PHASE_3_GIT_WORKFLOW.md` (3-5 min)
3. **Create DEV branch** for Part A
4. **Implement** Part A (logging_manager.py + log_viewer_dialog.py)
5. **Run checks** and **create PR**

**Ready to start?** Let me know and I'll provide any specific code templates or guidance you need!

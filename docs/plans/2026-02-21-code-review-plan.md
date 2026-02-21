# Code Review + Targeted Cleanup — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Thorough code review of all 38 source modules, then targeted fixes for anything genuinely worth changing.

**Architecture:** Two-phase approach. Phase 1 is pure review (read-only, produces findings report). Phase 2 implements fixes based on findings. Modules are reviewed in dependency order: core utilities → core modules → targets → commands → entry points.

**Tech Stack:** Python, pytest, TOML config

**Design doc:** `docs/plans/2026-02-21-code-review-design.md`

---

## Phase 1: Module-by-Module Review

Phase 1 is **read-only** — no code changes. Each task reviews a tier of modules and appends findings to the report file.

For each module, assess:
- Dead code / unused exports
- Actual duplication (not just structural similarity)
- Confusing or unnecessarily complex logic
- Inconsistencies (naming, patterns, error handling)
- Anything that would trip someone up reading it fresh

Classify each finding as:
- **Fix:** Genuinely needs changing
- **Consider:** Would improve clarity but not strictly necessary
- **Fine as-is:** Reviewed and acceptable (note briefly, don't belabor)

### Task 1: Create findings report skeleton

**Files:**
- Create: `docs/plans/2026-02-21-code-review-findings.md`

**Step 1: Create the report file**

```markdown
# Code Review Findings

**Date:** 2026-02-21
**Reviewer:** Claude
**Codebase:** kanibako v0.5.0 (38 source modules, 6,791 LOC)

## Tier 1 — Core Utilities

## Tier 2 — Core Modules

## Tier 3 — Targets

## Tier 4 — Commands

## Tier 5 — Entry Points

## Summary

### Fix (must change)

### Consider (user decision)

### Fine as-is
```

**Step 2: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Add code review findings skeleton"
```

---

### Task 2: Review Tier 1 — Core Utilities

**Files to review (read-only):**
- `src/kanibako/errors.py` — Exception hierarchy
- `src/kanibako/log.py` — Logging setup
- `src/kanibako/utils.py` — Utility functions
- `src/kanibako/registry.py` — OCI registry client
- `src/kanibako/containerfiles.py` — Containerfile resolution
- `src/kanibako/shellenv.py` — Environment file handling
- `src/kanibako/snapshots.py` — Vault snapshots
- `src/kanibako/git.py` — Git checks

**Step 1: Read each module end-to-end**

Read every line of each file. Check imports, exports, function signatures, error handling, naming.

**Step 2: Cross-reference with tests**

For each module, check corresponding test file(s) to see if any tested functions no longer exist or if any public functions lack tests.

**Step 3: Cross-reference with callers**

Grep for each public function/class to verify it's actually used. Flag anything that's exported but never imported elsewhere.

**Step 4: Write findings to report**

Append findings under `## Tier 1 — Core Utilities` in the findings report. For each module, write a 1-3 line summary. Only expand on items classified as Fix or Consider.

**Step 5: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Review tier 1: core utilities"
```

---

### Task 3: Review Tier 2 — Core Modules

**Files to review (read-only):**
- `src/kanibako/credentials.py` — Credential management
- `src/kanibako/config.py` — Configuration loading (311 LOC)
- `src/kanibako/workset.py` — Workset data model (271 LOC)
- `src/kanibako/paths.py` — Path resolution (854 LOC, second-largest)
- `src/kanibako/container.py` — Container runtime (266 LOC)
- `src/kanibako/freshness.py` — Image freshness checker

**Step 1: Read each module end-to-end**

Pay extra attention to `paths.py` (854 LOC) — assess whether it has a natural split point. Check for repeated init patterns across `_init_project()`, `_init_workset_project()`, `_init_decentralized_project()`.

**Step 2: Cross-reference with tests and callers**

Same as Task 2. Pay attention to `config.py` regex-based TOML key updates — check if they're fragile or well-tested.

**Step 3: Write findings to report**

Append under `## Tier 2 — Core Modules`.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Review tier 2: core modules"
```

---

### Task 4: Review Tier 3 — Targets

**Files to review (read-only):**
- `src/kanibako/targets/base.py` — Target ABC
- `src/kanibako/targets/claude.py` — Claude target
- `src/kanibako/targets/__init__.py` — Target discovery

**Step 1: Read each module end-to-end**

Check the ABC contract: are all methods implemented by ClaudeTarget? Are there default implementations that could be misleading?

**Step 2: Cross-reference with tests and callers**

Check `tests/test_targets/` for coverage of the target interface.

**Step 3: Write findings to report**

Append under `## Tier 3 — Targets`.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Review tier 3: targets"
```

---

### Task 5: Review Tier 4 — Commands

**Files to review (read-only):**
- `src/kanibako/commands/start.py` (336 LOC)
- `src/kanibako/commands/box.py` (1,070 LOC, largest file)
- `src/kanibako/commands/init.py`
- `src/kanibako/commands/status.py`
- `src/kanibako/commands/image.py` (317 LOC)
- `src/kanibako/commands/archive.py` (220 LOC)
- `src/kanibako/commands/stop.py`
- `src/kanibako/commands/clean.py`
- `src/kanibako/commands/restore.py` (290 LOC)
- `src/kanibako/commands/config_cmd.py`
- `src/kanibako/commands/vault_cmd.py`
- `src/kanibako/commands/env_cmd.py`
- `src/kanibako/commands/refresh_credentials.py`
- `src/kanibako/commands/workset_cmd.py` (248 LOC)
- `src/kanibako/commands/install.py`
- `src/kanibako/commands/remove.py`
- `src/kanibako/commands/upgrade.py`

**Step 1: Read each module end-to-end**

Pay extra attention to:
- `box.py` (1,070 LOC): Look for natural split points. Assess duplication across migrate/convert/duplicate helpers.
- `start.py` (336 LOC): Assess the 198-line `_run_container()` function. Is it actually hard to follow, or is it a clear sequential flow?
- `restore.py` (290 LOC): Check for duplication with `archive.py`.

**Step 2: Cross-reference with tests and callers**

Check for dead command handlers — functions registered in CLI but never dispatched.

**Step 3: Write findings to report**

Append under `## Tier 4 — Commands`. Be specific about `box.py` split recommendations if warranted.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Review tier 4: commands"
```

---

### Task 6: Review Tier 5 — Entry Points

**Files to review (read-only):**
- `src/kanibako/__init__.py` — Package version
- `src/kanibako/cli.py` — CLI parser and dispatcher
- `src/kanibako/__main__.py` — Entry point

**Step 1: Read each module end-to-end**

Check CLI parser for consistency: are all subcommands registered? Help text consistent? Flag casing correct per standing instructions (uppercase = agent flags, lowercase = container/project flags)?

**Step 2: Write findings to report**

Append under `## Tier 5 — Entry Points`.

**Step 3: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Review tier 5: entry points"
```

---

### Task 7: Write review summary

**Step 1: Compile summary sections**

Fill in the three summary sections at the bottom of the findings report:
- **Fix (must change):** Numbered list of all Fix items with module references
- **Consider (user decision):** Numbered list of all Consider items
- **Fine as-is:** Brief list of modules that passed review cleanly

**Step 2: Present findings to user**

Show the summary to the user and ask which "Consider" items (if any) they want to include in Phase 2.

**Step 3: Commit**

```bash
git add docs/plans/2026-02-21-code-review-findings.md
git commit -m "Complete code review findings"
```

---

## Phase 2: Targeted Fixes

Phase 2 tasks will be determined by Phase 1 findings. Each fix gets its own task following TDD discipline:

1. Write/update failing test (if behavior changes)
2. Verify test fails
3. Make the fix
4. Run full test suite: `~/.venv/bin/pytest tests/ -v`
5. Commit

Anticipated fix categories (to be confirmed by review):
- Dead code removal
- Duplication consolidation in `box.py` (possibly split into submodules)
- Function extraction in long functions
- Naming inconsistencies
- Unused imports/exports

**Important:** Phase 2 tasks are NOT pre-written. They emerge from Phase 1 findings. The review must complete before fixes begin.

---

## Verification

After all Phase 2 fixes:

```bash
# Full test suite
~/.venv/bin/pytest tests/ -v

# Integration tests
~/.venv/bin/pytest tests/ -v -m integration

# Verify no regressions
git diff --stat HEAD~N  # Review total scope of changes
```

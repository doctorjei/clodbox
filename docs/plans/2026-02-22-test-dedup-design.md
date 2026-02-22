# Test Deduplication Audit — Design

**Date:** 2026-02-22
**Goal:** Reduce test suite redundancy without removing any test coverage.

## Problem

The test suite (773 tests, 55 files, ~11,600 LOC) has two forms of redundancy:

1. **Duplicate fixtures** — `config`, `std`, and `project_dir` are defined identically in 4-5 files each instead of living in `conftest.py`.
2. **Base+extended file pairs** — 10 pairs exist where a `test_foo.py` and `test_foo_extended.py` both test the same source module. 7 of these are small enough to merge without creating unwieldy files.

## Approach

Two phases, fixtures first.

### Phase 1: Fixture Consolidation

Move three fixtures to `tests/conftest.py`:

| Fixture | Duplicated in | Implementation |
|---------|---------------|----------------|
| `config` | 4 files | `load_config(config_file)` — depends on existing `config_file` fixture |
| `std` | 5 files | `load_config(config_file)` then `load_std_paths(config)` — 3 files have an unused `tmp_home` param |
| `project_dir` | 3 files | `tmp_home / "project"` — depends on existing `tmp_home` fixture |

Files to clean up: `test_init_cmd.py`, `test_status.py`, `test_decentralized_paths.py`, `test_workset_paths.py`, `test_workset.py`

**Not consolidated:** `mock_runtime` in `test_stop.py` — intentionally different from conftest's version (mocks `stop`/`list_running` instead of `image_exists`/`pull`/`run`).

### Phase 2: File Merges (7 pairs)

Append extended file content into base file, deduplicate imports, delete extended file. Order by size:

| # | Base file | Extended file | Combined |
|---|-----------|---------------|----------|
| 1 | `test_commands/test_install.py` | `test_commands/test_install_extended.py` | ~88 lines |
| 2 | `test_commands/test_clean.py` | `test_commands/test_clean_extended.py` | ~210 lines |
| 3 | `test_config.py` | `test_config_extended.py` | ~220 lines |
| 4 | `test_credentials.py` | `test_credentials_extended.py` | ~269 lines |
| 5 | `test_commands/test_restore.py` | `test_commands/test_restore_extended.py` | ~289 lines |
| 6 | `test_commands/test_archive.py` | `test_commands/test_archive_extended.py` | ~304 lines |
| 7 | `test_commands/test_image.py` | `test_commands/test_image_extended.py` | ~308 lines |

### Keep Separate (3 pairs)

These exceed ~400 lines combined or test genuinely distinct dimensions:

- `test_container.py` + `test_container_extended.py` (~503 lines)
- `test_start.py` + `test_start_extended.py` (~527 lines)
- `test_paths.py` + `test_paths_extended.py` (~806 lines)

## Verification

- 773 tests before = 773 tests after
- Full test suite (`pytest tests/ -v`) passes after each step
- No test removal — only reorganization

## Constraints

- No changes to source code, only test files
- Preserve all existing test class names and structure
- Run tests after every change to catch breakage immediately

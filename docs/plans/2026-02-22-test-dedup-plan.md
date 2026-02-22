# Test Deduplication Audit — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce test suite redundancy by consolidating duplicate fixtures and merging 7 base+extended file pairs.

**Architecture:** Two phases. Phase 1 moves 3 duplicate fixtures to conftest.py and removes them from 5 files. Phase 2 merges 7 small extended test files into their base files and deletes the extended files. Tests run after every change.

**Tech Stack:** Python, pytest

**Design doc:** `docs/plans/2026-02-22-test-dedup-design.md`

---

## Phase 1: Fixture Consolidation

### Task 1: Consolidate duplicate fixtures into conftest.py

**Files:**
- Modify: `tests/conftest.py` (add 3 fixtures after existing `sample_config` fixture, ~line 68)
- Modify: `tests/test_init_cmd.py` (remove lines 18-31: `std`, `config`, `project_dir` fixtures)
- Modify: `tests/test_status.py` (remove lines 28-42: `std`, `config`, `project_dir` fixtures)
- Modify: `tests/test_decentralized_paths.py` (remove lines 22-38: `std`, `config`, `project_dir` fixtures)
- Modify: `tests/test_workset_paths.py` (remove lines 24-33: `std`, `config` fixtures)
- Modify: `tests/test_workset.py` (remove lines 28-31: `std` fixture)

**Step 1: Record baseline test count**

Run: `~/.venv/bin/pytest tests/ -v --co -q 2>&1 | tail -1`

Expected: "773 tests collected" (or current count — record the exact number)

**Step 2: Add fixtures to conftest.py**

Add after the `sample_config` fixture (~line 68), before `credentials_dir`:

```python
@pytest.fixture
def config(config_file):
    """Load config from the default kanibako.toml."""
    return load_config(config_file)


@pytest.fixture
def std(config_file):
    """Load standard paths from the default config."""
    from kanibako.paths import load_std_paths
    config = load_config(config_file)
    return load_std_paths(config)


@pytest.fixture
def project_dir(tmp_home):
    """Return the pre-existing project directory created by tmp_home."""
    return tmp_home / "project"
```

Note: The `std` fixture uses only `config_file`. Three files previously included an unused `tmp_home` param — the unified version drops it. The `load_std_paths` import is deferred to avoid importing `paths` at module level in conftest (matching the existing pattern where `credentials_dir` does a deferred import).

**Step 3: Remove duplicate fixtures from test_init_cmd.py**

Remove the entire Fixtures section (the `std`, `config`, and `project_dir` fixture definitions). Keep imports that are still used by tests — remove `load_config` and `load_std_paths` imports only if no test in the file uses them directly.

**Step 4: Remove duplicate fixtures from test_status.py**

Remove the `std`, `config`, and `project_dir` fixture definitions. The `initialized_project` fixture stays (it's local and different).

**Step 5: Remove duplicate fixtures from test_decentralized_paths.py**

Remove the `std`, `config`, and `project_dir` fixture definitions.

**Step 6: Remove duplicate fixtures from test_workset_paths.py**

Remove the `std` and `config` fixture definitions.

**Step 7: Remove duplicate fixture from test_workset.py**

Remove the `std` fixture definition.

**Step 8: Run tests**

Run: `~/.venv/bin/pytest tests/ -v`

Expected: Same test count as step 1, all passing.

**Step 9: Commit**

```bash
git add tests/conftest.py tests/test_init_cmd.py tests/test_status.py tests/test_decentralized_paths.py tests/test_workset_paths.py tests/test_workset.py
git commit -m "Consolidate config/std/project_dir fixtures into conftest.py"
```

---

## Phase 2: File Merges

For each merge: append the extended file's test classes and any unique imports into the base file, delete the extended file, run tests, commit. Preserve all test class names.

### Task 2: Merge test_install + test_install_extended

**Files:**
- Modify: `tests/test_commands/test_install.py`
- Delete: `tests/test_commands/test_install_extended.py`

**Step 1: Merge**

Add the `TestInstallExtended` class and its unique imports (`json`, `KanibakoConfig`, `write_global_config`, `MagicMock`) to `test_install.py`. The `_base_setup` helper stays as a method of `TestInstallExtended`.

**Step 2: Delete extended file**

```bash
git rm tests/test_commands/test_install_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_commands/test_install.py -v`

Expected: 3 tests passing.

**Step 4: Commit**

```bash
git add tests/test_commands/test_install.py
git commit -m "Merge test_install_extended into test_install (3 tests)"
```

---

### Task 3: Merge test_clean + test_clean_extended

**Files:**
- Modify: `tests/test_commands/test_clean.py`
- Delete: `tests/test_commands/test_clean_extended.py`

**Step 1: Merge**

Add `TestCleanExtended` and `TestCleanWorkset` classes to `test_clean.py`. Add unique imports: `resolve_workset_project` from `kanibako.paths`, `add_project`, `create_workset` from `kanibako.workset`.

**Step 2: Delete extended file**

```bash
git rm tests/test_commands/test_clean_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_commands/test_clean.py -v`

Expected: 10 tests passing (6 original + 4 extended).

**Step 4: Commit**

```bash
git add tests/test_commands/test_clean.py
git commit -m "Merge test_clean_extended into test_clean (10 tests)"
```

---

### Task 4: Merge test_config + test_config_extended

**Files:**
- Modify: `tests/test_config.py`
- Delete: `tests/test_config_extended.py`

**Step 1: Merge**

Add `TestFlattenToml` class and the extended `TestWriteProjectConfig` tests to `test_config.py`. The base already has a `TestWriteProjectConfig` class with `test_creates_new` and `test_updates_existing`. The extended file also has a `TestWriteProjectConfig` class — rename the extended one to `TestWriteProjectConfigExtended` to avoid collision (or merge its methods into the existing class if they don't overlap). Add unique import: `_flatten_toml`.

Check for method name conflicts between the two `TestWriteProjectConfig` classes before merging.

**Step 2: Delete extended file**

```bash
git rm tests/test_config_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_config.py -v`

Expected: 19 tests passing (13 original + 6 extended).

**Step 4: Commit**

```bash
git add tests/test_config.py
git commit -m "Merge test_config_extended into test_config (19 tests)"
```

---

### Task 5: Merge test_credentials + test_credentials_extended

**Files:**
- Modify: `tests/test_credentials.py`
- Delete: `tests/test_credentials_extended.py`

**Step 1: Merge**

Add `TestRefreshHostToProjectErrors`, `TestWriteback`, and `TestFilterSettingsExtended` classes. Add any unique imports from the extended file.

**Step 2: Delete extended file**

```bash
git rm tests/test_credentials_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_credentials.py -v`

Expected: 20 tests passing (5 original + 15 extended).

**Step 4: Commit**

```bash
git add tests/test_credentials.py
git commit -m "Merge test_credentials_extended into test_credentials (20 tests)"
```

---

### Task 6: Merge test_restore + test_restore_extended

**Files:**
- Modify: `tests/test_commands/test_restore.py`
- Delete: `tests/test_commands/test_restore_extended.py`

**Step 1: Merge**

Add `TestRestoreExtended` class and unique imports.

**Step 2: Delete extended file**

```bash
git rm tests/test_commands/test_restore_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_commands/test_restore.py -v`

Expected: 13 tests passing (2 original + 11 extended).

**Step 4: Commit**

```bash
git add tests/test_commands/test_restore.py
git commit -m "Merge test_restore_extended into test_restore (13 tests)"
```

---

### Task 7: Merge test_archive + test_archive_extended

**Files:**
- Modify: `tests/test_commands/test_archive.py`
- Delete: `tests/test_commands/test_archive_extended.py`

**Step 1: Merge**

Add `TestArchiveExtended` and `TestArchiveWorkset` classes and unique imports (e.g., `resolve_workset_project`, `add_project`, `create_workset`).

**Step 2: Delete extended file**

```bash
git rm tests/test_commands/test_archive_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_commands/test_archive.py -v`

Expected: 13 tests passing (2 original + 11 extended).

**Step 4: Commit**

```bash
git add tests/test_commands/test_archive.py
git commit -m "Merge test_archive_extended into test_archive (13 tests)"
```

---

### Task 8: Merge test_image + test_image_extended

**Files:**
- Modify: `tests/test_commands/test_image.py`
- Delete: `tests/test_commands/test_image_extended.py`

**Step 1: Merge**

Add `TestListRemotePackages` and `TestExtractGhcrOwnerExtended` classes and unique imports. Note: base already has `TestExtractGhcrOwner` — the extended `TestExtractGhcrOwnerExtended` has a different class name so no collision.

**Step 2: Delete extended file**

```bash
git rm tests/test_commands/test_image_extended.py
```

**Step 3: Run tests**

Run: `~/.venv/bin/pytest tests/test_commands/test_image.py -v`

Expected: 30 tests passing (19 original + 11 extended).

**Step 4: Commit**

```bash
git add tests/test_commands/test_image.py
git commit -m "Merge test_image_extended into test_image (30 tests)"
```

---

## Verification

### Task 9: Final verification

**Step 1: Run full test suite**

Run: `~/.venv/bin/pytest tests/ -v`

Expected: Same test count as Task 1 Step 1 baseline. All passing.

**Step 2: Confirm extended files are gone**

Run: `find tests/ -name '*_extended*'`

Expected: Only 3 files remain:
- `tests/test_container_extended.py`
- `tests/test_paths_extended.py`
- `tests/test_commands/test_start_extended.py`

**Step 3: Update future-work.md**

Mark item #2 (Test deduplication audit) as done in `~/.claude/projects/-home-agent-workspace/memory/future-work.md`.

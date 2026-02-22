# CI Test Automation Design

Date: 2026-02-22

## Goal

Run unit tests, lint, and type-checking on GitHub Actions for every push to
`main` and every pull request.

## Decisions

- **No integration tests in CI** -- they stay local-only (need container runtime,
  flaky on runners, 35 tests vs 738 unit tests)
- **Python 3.11 only** -- minimum supported version, no matrix
- **Single job, sequential steps** -- lint/mypy are fast; parallel jobs add
  more checkout+install overhead than they save
- **No pip caching** -- one runtime dep (`argcomplete`), install is fast
- **No coverage reporting** -- can add later if wanted

## Workflow

File: `.github/workflows/test.yml`

```yaml
name: Tests
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e '.[dev]'
      - run: ruff check src/ tests/
      - run: mypy src/kanibako/
      - run: pytest tests/ -v
```

## Pre-existing issues

`mypy src/kanibako/` currently reports 2 errors:

1. `workset_cmd.py:149` -- `str` assigned to `Path` variable
2. `vault_cmd.py:165` -- `float` assigned to `int` variable

These must be fixed before (or as part of) enabling CI, otherwise the
workflow will fail on first run.

## Implementation steps

1. Fix the 2 mypy errors
2. Create `.github/workflows/test.yml`
3. Verify locally: `ruff check src/ tests/ && mypy src/kanibako/ && pytest tests/ -v`

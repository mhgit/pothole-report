# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI tool (`report-pothole`) that batch-processes pothole photos: extracts GPS/datetime from EXIF, reverse-geocodes to a UK postcode via Nominatim, and prints a copy-paste-ready report bundle for manual submission to [Fill That Hole](https://www.fillthathole.org.uk/) (Cycling UK). One report per folder; GPS/datetime come from the earliest-dated image in that folder.

## Commands

```bash
uv sync                                                    # install deps
uv run report-pothole -f ./photos --depth gt50mm --edge sharp   # run
uv run report-pothole -f ./photos -i                        # interactive attribute prompts
uv run report-pothole setup                                 # store email in keyring (first run)
uv run report-pothole remove-keyring                        # remove stored email

uv run pytest                                                # all tests
uv run pytest tests/test_extract.py                          # single file
uv run pytest tests/test_extract.py::test_name -v             # single test
uv run pytest --cov=pothole_report --cov-report=term-missing  # with coverage
uv run ruff check src/ tests/ main.py                         # lint (CI-enforced)
uv run ruff format --check src/ tests/ main.py                # format check (CI-enforced)
uv run ruff format src/ tests/ main.py                        # apply formatting
```

CI (`.github/workflows/ci.yml`) runs on push/PR to `main`/`develop`: `uv sync --all-groups`, ruff check, ruff format check, pytest — in that order. Match this locally before pushing.

Requires **Python 3.14** (note: `except ValueError, TypeError:` in `extract.py` is valid 3.14 syntax — PEP 758 unparenthesized multi-exception `except`, not a typo).

## Architecture

Pipeline through `src/pothole_report/`, orchestrated by `cli.py:main()`:

1. **`scan.py`** — non-recursive folder scan for `.jpg`/`.jpeg`/`.png`, sorted by filename.
2. **`extract.py`** — per-image EXIF read via Pillow (`ExtractedData`: path, lat, lon, datetime_taken). Returns `None` (image skipped) if no GPS block present.
3. Across all extracted images, the **earliest by `datetime_taken`** (None sorts last) is chosen as the GPS/datetime source for the whole report — natural GPS drift between photos in one folder is expected and ignored.
4. **`geocode.py`** — reverse-geocodes the earliest image's coordinates via geopy's `Nominatim`, requires a postcode in the response or returns `None` (no report generated).
5. **`config.py`** — loads two independent YAML configs by search-path (project `conf/` first, then `~/.config/pothole-report/`), each overridable via `-c`:
   - `pothole-report.yaml` (required): `report_url`, `attributes` (category → value → description), `report_template` (placeholders like `{severity}`, `{depth_description}`), optional `attribute_phrases` (attribute-combination → phrase, used to derive severity and per-category description text) and `advice_for_reporters`. Email is **never** read from this file — it's fetched from keyring (service `pothole-report`, account from `keyring_account`, default `"email"`); missing email raises with setup instructions.
   - `pothole-checking.yaml` (optional): `check_sites` list of `{name, url}` templates (`{lat}`/`{lon}` or `{latitude}`/`{longitude}` placeholders) for the "existing reports" panel. Missing file → panel omitted with a warning; malformed file → `ValueError`, panel omitted, main report still runs.
6. **`cli.py`** — argument parsing (attribute flags are validated against the loaded config's `attributes`, not hardcoded choices), interactive mode, `_generate_report_text()` (fills `report_template` from `attribute_phrases`/`attributes` fallback, strips unfilled placeholders), builds a replayable command line for the record.
7. **`output.py`** — assembles `ReportRecord` and prints plain text (no rich boxes, intentionally copy-paste friendly) via `print_report()`.

Two subcommands (`setup`, `remove-keyring`) are dispatched manually at the top of `main()` by inspecting `sys.argv[1]` before the main `argparse` parser runs, rather than using argparse subparsers.

### Config-driven attributes

`depth`, `edge`, `width`, `location`, `visibility`, `surface` are not fixed enums — they're whatever categories/values the loaded YAML's `attributes` section defines. `location` and `visibility` support multi-select via comma-separated CLI values or comma-separated interactive input; other categories are single-value. When adding a new attribute category, no code change is needed — only config — unless it also needs multi-select behavior (currently hardcoded to `location`/`visibility` in `cli.py`).

### Error handling conventions

Per-image extraction/geocoding failures are non-fatal — the image is skipped (counted and reported in verbose/summary output) and processing continues; only a total absence of usable images/geocoding aborts the report. Config-loading failures (`FileNotFoundError`, `ValueError`) are fatal and exit with `SystemExit(1)`.

# Pothole Report

A CLI tool that batch-processes pothole photos, extracts GPS metadata, reverse-geocodes to UK postcodes, and outputs a report bundle ready for manual submission via [Fill That Hole](https://www.fillthathole.org.uk/) (Cycling UK). One site covers all UK councils.

Built for cyclists who encounter multiple road defects on a single ride: take photos and keep riding, then run this tool to generate a report bundle. **One report per folder.** GPS is taken from the earliest-dated image—ensure your first photo (by capture time) is the actual pothole.

## Tech Stack

- **Runtime:** Python 3.14
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Libraries:** Pillow (EXIF), geopy (Nominatim), rich (CLI output), PyYAML (config), keyring (macOS Keychain)

## Getting Started

### Prerequisites

- Python 3.14
- [uv](https://github.com/astral-sh/uv) (`brew install uv` on macOS)

### Install

```bash
uv sync
```

### Config

Create `conf/pothole-report.yaml` (or copy from `conf/pothole-report.example.yaml`):

```yaml
report_url: "https://www.fillthathole.org.uk"
# Email is stored in keyring (not in this file - safe to commit)

risk_levels:
  level_1_emergency:
    description: "An immediate threat to life and limb..."
    visual_indicators: "Deep 'crater' style hole..."
    report_template: >
      EMERGENCY: Immediate safety hazard...
  level_2_high_priority:
    description: "A significant hazard..."
    visual_indicators: "A deep pothole..."
    report_template: >
      HIGH RISK: Significant road defect...
  # ... (level_3_medium_hazard, level_4_developing_risk, level_5_monitoring_nuisance)
  # All five levels are required. You can add custom levels beyond these.

advice_for_reporters:
  key_phrases:
    - "Primary line of travel"
    - "Risk of ejection"
    # ... more phrases
  pro_tip: "Always include a photo with a common object for scale..."
```

Or place it at `~/.config/pothole-report/pothole-report.yaml`. The config must include all five required risk levels (`level_1_emergency` through `level_5_monitoring_nuisance`). Each level requires `description`, `visual_indicators`, and `report_template` fields. You can add custom risk levels beyond the required five.

### Store your email (first run)

Email is stored in macOS Keychain via keyring—never in config files:

```bash
uv run report-pothole setup
```

You’ll be prompted for your email. It is stored securely and not written to disk.

To remove the stored email (e.g. for cleanup):

```bash
uv run report-pothole remove-keyring
```

### Usage

```bash
uv run report-pothole -f /path/to/photos
uv run report-pothole -f ./photos -r level_1_emergency    # use specific risk level
uv run report-pothole -l                                  # list available risk levels
uv run report-pothole -f ./photos -c conf/pothole-report.yaml
uv run report-pothole setup -c conf/pothole-report.yaml   # store email (first run)
uv run report-pothole remove-keyring -c conf/pothole-report.yaml  # remove stored email
```

| Option | Description |
|--------|-------------|
| `-f`, `--folder` | Folder containing JPG/PNG photos (required unless `-l`) |
| `-l`, `--list-risk-levels` | List available risk levels with descriptions and visual indicators |
| `-r`, `--risk-level` | Risk level key for report (default: level_3_medium_hazard) |
| `-c`, `--config` | Path to config file (optional override) |
| `-v`, `--verbose` | Show which files were skipped (no GPS / geocode failed) |

### Output

One report per folder. The report includes:

- **Postcode** and address (from reverse geocoding)
- **Fill That Hole** and **Google Maps** (clickable cyan links in the report body)
- **Report Template** (the chosen risk level's report_template text, ready to copy-paste for council forms)
- **Advice for Reporters** section (includes description, visual indicators, key phrases, and pro tips)
- **Date/time** from the earliest-dated image (used for GPS)
- **Image listing** (3-column table of all images in the folder)

The report template text comes from the selected risk level's `report_template` field. The "Advice for Reporters" section helps you understand the defect characteristics and provides key phrases to use when submitting reports.

Images with slightly different GPS (natural GPS drift) are normal. The earliest image's coordinates are used.

## Development

```bash
uv run pytest
uv run pytest --cov=pothole_report --cov-report=term-missing
uv run ruff check src/
```

## License

See [License.md](License.md).

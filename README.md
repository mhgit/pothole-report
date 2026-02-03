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

attributes:
  depth:
    lt40mm: "Less than 40mm (sub-intervention)"
    gte40mm: "40mm or greater (meets intervention level)"
    gt50mm: "Greater than 50mm (emergency intervention)"
  edge:
    sharp: "Sharp, vertical shear edges"
    rounded: "Rounded edges"
  location:
    primary_cycle_line: "Primary cycle line / where cyclist expected"
    descent: "High-speed descent"
    # ... more attribute categories

report_template: >
  {severity}: {depth_description} road defect located {location_description}.
  {edge_description} edges {visibility_description}. {surface_description}.
  This defect presents a significant risk to vulnerable road users.

attribute_phrases:
  severity:
    gt50mm_sharp_primary_cycle_line: "EMERGENCY"
    gte40mm_primary_cycle_line: "HIGH RISK"
  depth_description:
    lt40mm: "less than 40mm deep"
    gte40mm: "40mm or greater"
  # ... more phrase mappings

advice_for_reporters:
  key_phrases:
    - "Primary line of travel"
    - "Risk of ejection"
    # ... more phrases
  pro_tip: "Always include a photo with a common object for scale..."
```

Or place it at `~/.config/pothole-report/pothole-report.yaml`. The config must include `attributes` (defining available values for each attribute category), `report_template` (a parameterized template with placeholders), and optionally `attribute_phrases` (mappings for generating report text from attribute combinations).

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
# Interactive mode - prompts for attribute values
uv run report-pothole -f /path/to/photos -i

# Command-line mode - specify attributes as flags
uv run report-pothole -f ./photos --depth gt50mm --edge sharp --location primary_cycle_line
uv run report-pothole -f ./photos --depth gte40mm --visibility obscured_water

# With custom config
uv run report-pothole -f ./photos -c conf/pothole-report.yaml --depth lt40mm

# Setup and cleanup
uv run report-pothole setup -c conf/pothole-report.yaml   # store email (first run)
uv run report-pothole remove-keyring -c conf/pothole-report.yaml  # remove stored email
```

| Option | Description |
|--------|-------------|
| `-f`, `--folder` | Folder containing JPG/PNG photos (required) |
| `-i`, `--interactive` | Interactive mode: prompt for attribute values |
| `--depth` | Depth category (e.g., lt40mm, gte40mm, gt50mm) |
| `--edge` | Edge type (e.g., sharp, rounded, gradual) |
| `--width` | Width/size (e.g., small, medium_fist, large_crater, clusters, longitudinal) |
| `--location` | Location context (e.g., primary_cycle_line, descent, braking_zone, junction_approach, general) |
| `--visibility` | Visibility (e.g., obscured_water, obscured_shadows, visible) |
| `--surface` | Surface condition (e.g., exposed_sub_base, loose_gravel, longitudinal_crack, hairline) |
| `-c`, `--config` | Path to config file (optional override) |
| `-v`, `--verbose` | Show which files were skipped (no GPS / geocode failed) |

### Output

One report per folder. The report includes:

- **Postcode** and address (from reverse geocoding)
- **Fill That Hole** and **Google Maps** (clickable cyan links in the report body)
- **Attributes** section (lists selected attributes with descriptions, e.g., "depth: gt50mm (Greater than 50mm)")
- **Generated Report** (dynamically generated text based on selected attributes, ready to copy-paste for council forms)
- **Command Line** (equivalent command that could be used to reproduce the same report)
- **Advice for Reporters** section (includes key phrases and pro tips)
- **Date/time** from the earliest-dated image (used for GPS)
- **Image listing** (3-column table of all images in the folder)

The report text is generated from the `report_template` using the selected attributes. The system looks up phrases from `attribute_phrases` based on attribute combinations to fill template placeholders. After generating a report interactively, the equivalent command-line flags are displayed so you can reproduce the same report later.

Images with slightly different GPS (natural GPS drift) are normal. The earliest image's coordinates are used.

## Development

```bash
uv run pytest
uv run pytest --cov=pothole_report --cov-report=term-missing
uv run ruff check src/
```

## License

See [License.md](License.md).

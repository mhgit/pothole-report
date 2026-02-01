# pothole-batcher

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

templates:
  high-risk: "This defect is located..."
  hidden: "This pothole is often obscured..."
  # Add your own; use with -r <key> or --report-name=<key>
```

Or place it at `~/.config/pothole-batcher/pothole-report.yaml`. Edit `templates` to add or change report description text.

### Store your email (first run)

Email is stored in macOS Keychain via keyring—never in config files:

```bash
uv run report-pothole setup
```

You’ll be prompted for your email. It is stored securely and not written to disk.

### Usage

```bash
uv run report-pothole -f /path/to/photos
uv run report-pothole -f ./photos -r hidden              # use 'hidden' template
uv run report-pothole -l                                 # list available templates
uv run report-pothole -f ./photos -c conf/pothole-report.yaml
uv run report-pothole setup -c conf/pothole-report.yaml # store email (first run)
```

| Option | Description |
|--------|-------------|
| `-f`, `--folder` | Folder containing JPG/PNG photos (required unless `-l`) |
| `-l`, `--list-reports` | List available report template names from config |
| `-r`, `--report-name` | Template key for report description (default: default) |
| `-c`, `--config` | Path to config file (optional override) |
| `-v`, `--verbose` | Show which files were skipped (no GPS / geocode failed) |

### Output

One report per folder. The report includes:

- **Postcode** and address (from reverse geocoding)
- **Fill That Hole** and **Google Maps** (clickable cyan links in the report body)
- **Description template** (copy-paste for council forms)
- **Date/time** from the earliest-dated image (used for GPS)
- **Image listing** (3-column table of all images in the folder)

Images with slightly different GPS (natural GPS drift) are normal. The earliest image’s coordinates are used.

## Development

```bash
uv run pytest
uv run pytest --cov=pothole_batcher --cov-report=term-missing
uv run ruff check src/
```

## License

See [License.md](License.md).

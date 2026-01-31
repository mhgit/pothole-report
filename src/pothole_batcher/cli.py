"""CLI entry point and orchestration."""

import argparse
import sys
from pathlib import Path

import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn
from rich.table import Table

from pothole_batcher.config import SERVICE_NAME, load_config
from pothole_batcher.extract import extract_all
from pothole_batcher.geocode import reverse_geocode
from pothole_batcher.output import build_report_record, print_report
from pothole_batcher.scan import scan_folder


def _run_setup(config_path: Path | None) -> None:
    """Store email in keyring. Prompts user for input."""
    console = Console()
    # Resolve keyring_account from config if it exists
    keyring_account = "email"
    if config_path and config_path.exists():
        import yaml
        with config_path.open() as f:
            data = yaml.safe_load(f) or {}
        keyring_account = str(data.get("keyring_account", "email"))
    email = console.input("[bold]Email for reporting:[/] ").strip()
    if not email:
        console.print("[red]Email cannot be empty.[/]")
        raise SystemExit(1)
    keyring.set_password(SERVICE_NAME, keyring_account, email)
    console.print("[green]Email stored in keyring.[/]")


def main() -> None:
    """Run the pothole reporter CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        sys.argv.pop(1)
        parser = argparse.ArgumentParser(description="Store email in keyring (macOS Keychain).")
        parser.add_argument("-c", "--config", type=Path, default=None, help="Path to config file")
        args = parser.parse_args()
        _run_setup(args.config)
        return

    parser = argparse.ArgumentParser(
        description="Batch-process pothole photos for UK Fill That Hole reporting.",
    )
    parser.add_argument(
        "-f",
        "--folder",
        type=Path,
        help="Folder containing JPG/PNG photos",
    )
    parser.add_argument(
        "-l",
        "--list-reports",
        action="store_true",
        help="List available report template names from config",
    )
    parser.add_argument(
        "-r",
        "--report-name",
        default="high-risk",
        help="Template key to use for report description (default: high-risk)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to config file (optional)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show stack traces on errors",
    )
    args = parser.parse_args()

    console = Console()

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e

    if args.list_reports:
        templates = config["templates"]
        table = Table(title="Available reports")
        table.add_column("Name", style="cyan")
        table.add_column("Preview", style="dim", max_width=60, overflow="ellipsis")
        for name, text in templates.items():
            preview = (text[:57] + "...") if len(text) > 60 else text
            table.add_row(name, preview)
        console.print(table)
        return

    if not args.folder:
        parser.error("-f/--folder is required (unless using --list-reports)")

    report_url = config["report_url"]
    email = config["email"]
    templates = config["templates"]
    description = templates.get(args.report_name)
    if description is None:
        console.print(f"[red]Error:[/] Unknown report name '{args.report_name}'. "
                      f"Use --list-reports to see available names.")
        raise SystemExit(1)

    # Scan folder
    try:
        paths = scan_folder(args.folder)
    except NotADirectoryError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e

    if not paths:
        console.print("[yellow]No JPG/PNG files found in folder.[/]")
        return

    # Extract from all images; use earliest-dated one for GPS
    extracted_list: list = []
    skipped_no_gps = 0

    with Progress(
        SpinnerColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(paths))
        for path in paths:
            extracted = extract_all(path)
            if extracted is None:
                skipped_no_gps += 1
                if args.verbose:
                    console.print(f"[dim]Skipped (no GPS): {path.name}[/]")
            else:
                extracted_list.append(extracted)
            progress.advance(task)

    if skipped_no_gps:
        console.print(f"[yellow]Skipped {skipped_no_gps} image(s) with no GPS data.[/]")

    if not extracted_list:
        console.print("[yellow]No reports generated (no images with GPS).[/]")
        return

    # Sort by datetime (earliest first); None datetimes go last
    def _sort_key(e):
        dt = e.datetime_taken or "9999-99-99 99:99"
        return (dt, e.path.name)

    extracted_list.sort(key=_sort_key)
    earliest = extracted_list[0]

    geocoded = reverse_geocode(earliest.lat, earliest.lon)
    if geocoded is None:
        console.print("[yellow]Geocoding failed; no report generated.[/]")
        return

    image_names = [p.name for p in paths]
    record = build_report_record(
        earliest,
        geocoded,
        report_url,
        email,
        description,
        image_names,
    )
    print_report(record, console)

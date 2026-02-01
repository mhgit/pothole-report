"""CLI entry point and orchestration."""

import argparse
import sys
from pathlib import Path

import keyring
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn

from pothole_report.config import SERVICE_NAME, load_config
from pothole_report.extract import extract_all
from pothole_report.geocode import reverse_geocode
from pothole_report.output import build_report_record, print_report
from pothole_report.scan import scan_folder


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


def _run_remove_keyring(config_path: Path | None) -> None:
    """Remove the stored email from keyring (for cleanup)."""
    console = Console()
    keyring_account = "email"
    if config_path and config_path.exists():
        import yaml
        with config_path.open() as f:
            data = yaml.safe_load(f) or {}
        keyring_account = str(data.get("keyring_account", "email"))
    try:
        keyring.delete_password(SERVICE_NAME, keyring_account)
        console.print("[green]Removed keyring entry.[/]")
    except keyring.errors.PasswordDeleteError:
        console.print("[dim]No keyring entry found (already removed or never set).[/]")


def main() -> None:
    """Run the pothole reporter CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        sys.argv.pop(1)
        parser = argparse.ArgumentParser(description="Store email in keyring (macOS Keychain).")
        parser.add_argument("-c", "--config", type=Path, default=None, help="Path to config file")
        args = parser.parse_args()
        _run_setup(args.config)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "remove-keyring":
        sys.argv.pop(1)
        parser = argparse.ArgumentParser(description="Remove stored email from keyring.")
        parser.add_argument("-c", "--config", type=Path, default=None, help="Path to config file")
        args = parser.parse_args()
        _run_remove_keyring(args.config)
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
        "--list-risk-levels",
        action="store_true",
        help="List available risk levels from config",
    )
    parser.add_argument(
        "-r",
        "--risk-level",
        default="level_3_medium_hazard",
        help="Risk level key to use for report (default: level_3_medium_hazard)",
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
        help="Show verbose output including inputs and processing details",
    )
    args = parser.parse_args()

    console = Console()

    # Show verbose inputs
    if args.verbose:
        console.print("[dim]Verbose mode enabled[/]")
        if args.config:
            console.print(f"[dim]Config file:[/] {args.config}")
        else:
            from pothole_report.config import _config_paths
            paths = _config_paths(None)
            console.print("[dim]Config search paths:[/]")
            for p in paths:
                exists = "✓" if p.exists() else "✗"
                console.print(f"[dim]  {exists} {p}[/]")
        console.print(f"[dim]Folder:[/] {args.folder if args.folder else '(not set)'}")
        console.print(f"[dim]Risk level:[/] {args.risk_level}")
        console.print("")

    # Load config (email not required for listing risk levels)
    require_email = not args.list_risk_levels
    try:
        config = load_config(args.config, require_email=require_email)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e

    if args.verbose:
        loaded_from = config.get("_loaded_from", "unknown")
        if loaded_from != "unknown":
            console.print(f"[dim]Loaded config from:[/] {loaded_from}")
        console.print(f"[dim]Report URL:[/] {config['report_url']}")
        email = config.get('email')
        if email:
            keyring_service = config.get("_keyring_service", "pothole-report")
            keyring_account = config.get("_keyring_account", "email")
            console.print(f"[dim]Email:[/] {email} (from keyring: service='{keyring_service}', account='{keyring_account}')")
        else:
            console.print("[dim]Email:[/] (not required for this operation)")
        console.print(f"[dim]Risk levels available:[/] {len(config['risk_levels'])}")
        console.print("")

    if args.list_risk_levels:
        risk_levels = config["risk_levels"]
        # Build box-style output with level, description, and visual_indicators
        content_lines = []
        for level_key in sorted(risk_levels.keys()):
            level_data = risk_levels[level_key]
            content_lines.append(f"[bold cyan]{level_key}[/]")
            content_lines.append(f"  [bold]Description:[/] {level_data['description']}")
            content_lines.append(f"  [bold]Visual Indicators:[/] {level_data['visual_indicators']}")
            content_lines.append("")  # blank line between levels
        
        content_text = "\n".join(content_lines).strip()
        panel = Panel(content_text, title="Available Risk Levels", border_style="blue")
        console.print(panel)
        return

    if not args.folder:
        parser.error("-f/--folder is required (unless using --list-risk-levels)")

    # Email is required for report generation
    email = config.get("email")
    if not email:
        console.print("[red]Error:[/] Email not found in keyring. Run 'report-pothole setup' to store your email.")
        raise SystemExit(1)

    report_url = config["report_url"]
    risk_levels = config["risk_levels"]
    selected_level = risk_levels.get(args.risk_level)
    if selected_level is None:
        console.print(f"[red]Error:[/] Unknown risk level '{args.risk_level}'. "
                      f"Use --list-risk-levels to see available levels.")
        raise SystemExit(1)
    
    if args.verbose:
        console.print(f"[dim]Selected risk level:[/] {args.risk_level}")
        console.print(f"[dim]  Description:[/] {selected_level['description'][:60]}...")
        console.print("")
    
    advice_for_reporters = config.get("advice_for_reporters", {})

    # Scan folder
    try:
        paths = scan_folder(args.folder)
    except NotADirectoryError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e

    if not paths:
        console.print("[yellow]No JPG/PNG files found in folder.[/]")
        return

    if args.verbose:
        console.print(f"[dim]Found {len(paths)} image file(s) in folder[/]")
        for path in paths:
            console.print(f"[dim]  - {path.name}[/]")
        console.print("")

    # Extract from all images; use earliest-dated one for GPS
    extracted_list: list = []
    skipped_no_gps = 0
    skipped_unreadable = 0

    with Progress(
        SpinnerColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Image Processing Progress", total=len(paths))
        for path in paths:
            try:
                extracted = extract_all(path)
            except Exception:
                skipped_unreadable += 1
                if args.verbose:
                    console.print(f"[dim]Skipped (unreadable): {path.name}[/]")
                progress.advance(task)
                continue
            if extracted is None:
                skipped_no_gps += 1
                if args.verbose:
                    console.print(f"[dim]Skipped (no GPS): {path.name}[/]")
            else:
                extracted_list.append(extracted)
            progress.advance(task)
    
    # Progress bar clears when done, so print completion message
    console.print(f"[dim]Image Processing Progress: 100% ({len(paths)} image(s) processed)[/]")

    if skipped_unreadable:
        console.print(f"[yellow]Skipped {skipped_unreadable} unreadable image(s).[/]")
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

    if args.verbose:
        console.print(f"[dim]Using earliest image for GPS:[/] {earliest.path.name}")
        console.print(f"[dim]  Coordinates:[/] {earliest.lat:.6f}, {earliest.lon:.6f}")
        console.print(f"[dim]  Date/time:[/] {earliest.datetime_taken or '(not available)'}")
        console.print("")

    geocoded = reverse_geocode(earliest.lat, earliest.lon)
    if geocoded is None:
        console.print("[yellow]Geocoding failed; no report generated.[/]")
        return

    if args.verbose:
        console.print(f"[dim]Geocoded to:[/] {geocoded.postcode} - {geocoded.address}")
        console.print("")

    image_names = [p.name for p in paths]
    record = build_report_record(
        earliest,
        geocoded,
        report_url,
        email,
        selected_level["report_template"],
        selected_level["description"],
        selected_level["visual_indicators"],
        advice_for_reporters,
        image_names,
    )
    print_report(record, console)

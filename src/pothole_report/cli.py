"""CLI entry point and orchestration."""

import argparse
import re
import sys
from pathlib import Path

import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn

from pothole_report.config import SERVICE_NAME, expand_check_url, load_check_config, load_config
from pothole_report.extract import extract_all
from pothole_report.geocode import reverse_geocode
from pothole_report.output import build_report_record, print_report
from pothole_report.scan import scan_folder


def _generate_report_text(attributes: dict, config: dict) -> str:
    """Generate report text from attributes using template and phrase lookup.
    
    Args:
        attributes: Dict mapping attribute names to selected values (e.g., {"depth": "gt50mm"})
                   For location and visibility, values can be comma-separated strings (e.g., "primary_cycle_line,descent")
        config: Config dict containing report_template and attribute_phrases
    
    Returns:
        Generated report text with placeholders filled
    """
    template = config["report_template"]
    phrases = config.get("attribute_phrases", {})
    attrs = config["attributes"]
    
    # Helper to parse comma-separated values
    def _parse_value(value: str) -> list[str]:
        """Parse attribute value, handling comma-separated lists."""
        if isinstance(value, str) and "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value] if value else []
    
    # Build a lookup key for severity based on attribute combinations
    # Priority order: depth, edge, location (for severity determination)
    severity_key_parts = []
    for key in ["depth", "edge", "location"]:
        if key in attributes and attributes[key]:
            # For location, use first value for severity lookup
            loc_values = _parse_value(attributes[key])
            if loc_values:
                severity_key_parts.append(loc_values[0])
    
    # Look up severity from attribute_phrases
    severity = "MEDIUM RISK"  # default
    if severity_key_parts:
        severity_key = "_".join(severity_key_parts)
        if "severity" in phrases:
            severity = phrases["severity"].get(severity_key, severity)
    
    # Build phrase lookups for each attribute category
    replacements = {"severity": severity}
    
    # For each attribute category, look up the phrase
    for attr_name in ["depth", "edge", "width", "location", "visibility", "surface"]:
        if attr_name in attributes and attributes[attr_name]:
            attr_value = attributes[attr_name]
            phrase_key = f"{attr_name}_description"
            
            # Handle multi-select for location and visibility
            if attr_name in ["location", "visibility"]:
                values = _parse_value(attr_value)
                descriptions = []
                for val in values:
                    # Look for phrase in attribute_phrases
                    if phrase_key in phrases and val in phrases[phrase_key]:
                        descriptions.append(phrases[phrase_key][val])
                    elif attr_name in attrs and val in attrs[attr_name]:
                        descriptions.append(attrs[attr_name][val])
                    else:
                        descriptions.append(val)
                # Join multiple descriptions with " and "
                replacements[phrase_key] = " and ".join(descriptions) if len(descriptions) > 1 else descriptions[0] if descriptions else ""
            else:
                # Single value attributes
                if phrase_key in phrases and attr_value in phrases[phrase_key]:
                    replacements[phrase_key] = phrases[phrase_key][attr_value]
                else:
                    # Fallback to description from attributes
                    if attr_name in attrs and attr_value in attrs[attr_name]:
                        replacements[phrase_key] = attrs[attr_name][attr_value]
                    else:
                        replacements[phrase_key] = attr_value
    
    # Fill template placeholders
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(f"{{{placeholder}}}", str(value))
    
    # Handle any remaining placeholders (optional attributes not provided)
    # Remove placeholders that weren't filled
    result = re.sub(r"\{[^}]+\}", "", result)
    # Clean up extra whitespace (multiple spaces/newlines)
    result = re.sub(r"\s+", " ", result).strip()
    
    return result


def _run_interactive_mode(config: dict, console: Console) -> dict:
    """Run interactive mode to prompt user for attribute values.
    
    Args:
        config: Config dict containing attributes
        console: Rich console for output
    
    Returns:
        Dict mapping attribute names to selected values (comma-separated for location/visibility)
    """
    attributes = {}
    attrs_config = config["attributes"]
    
    console.print("[bold cyan]Interactive Attribute Selection[/]")
    console.print("[dim]Press Enter to skip an attribute[/]")
    console.print("[dim]For location and visibility, enter multiple numbers separated by commas (e.g., 1,5)[/]\n")
    
    for attr_name in sorted(attrs_config.keys()):
        attr_values = attrs_config[attr_name]
        choices = list(attr_values.keys())
        
        # Build choice display
        choice_lines = []
        for i, choice_key in enumerate(choices, 1):
            desc = attr_values[choice_key]
            choice_lines.append(f"  {i}. {choice_key}: {desc}")
        
        console.print(f"[bold]{attr_name.capitalize()}:[/]")
        console.print("\n".join(choice_lines))
        
        # Check if this attribute supports multi-select
        is_multi_select = attr_name in ["location", "visibility"]
        prompt_suffix = f" (1-{len(choices)}" + (", comma-separated for multiple" if is_multi_select else "") + " or Enter to skip)"
        
        while True:
            user_input = console.input(f"\n[bold]Select {attr_name}[/]{prompt_suffix}: ").strip()
            if not user_input:
                # User skipped this attribute
                break
            
            if is_multi_select and "," in user_input:
                # Multi-select: parse comma-separated numbers
                try:
                    indices = [int(x.strip()) - 1 for x in user_input.split(",")]
                    if all(0 <= idx < len(choices) for idx in indices):
                        selected_keys = [choices[idx] for idx in indices]
                        attributes[attr_name] = ",".join(selected_keys)
                        console.print(f"[green]Selected:[/] {', '.join(selected_keys)}\n")
                        break
                    else:
                        console.print(f"[red]Invalid choice(s). Enter numbers 1-{len(choices)} separated by commas.[/]")
                except ValueError:
                    console.print(f"[red]Invalid input. Enter numbers 1-{len(choices)} separated by commas.[/]")
            else:
                # Single select
                try:
                    choice_idx = int(user_input) - 1
                    if 0 <= choice_idx < len(choices):
                        selected_key = choices[choice_idx]
                        attributes[attr_name] = selected_key
                        console.print(f"[green]Selected:[/] {selected_key}\n")
                        break
                    else:
                        console.print(f"[red]Invalid choice. Enter 1-{len(choices)} or press Enter to skip.[/]")
                except ValueError:
                    console.print(f"[red]Invalid input. Enter a number 1-{len(choices)} or press Enter to skip.[/]")
    
    return attributes


def _build_command_line(folder: Path, attributes: dict) -> str:
    """Build command line string from folder and attributes with backslash line breaks.
    
    Args:
        folder: Path to photo folder
        attributes: Dict mapping attribute names to selected values (comma-separated for multi-select)
    
    Returns:
        Command line string with backslash line breaks for long commands
        (e.g., "uv run report-pothole -f /path \\\n  --depth gt50mm \\\n  --location primary_cycle_line,descent")
    """
    cmd_parts = ["uv", "run", "report-pothole", "-f", str(folder)]
    
    for attr_name in sorted(attributes.keys()):
        if attributes[attr_name]:
            # For multi-select values, keep them as comma-separated in the command line
            cmd_parts.extend([f"--{attr_name}", attributes[attr_name]])
    
    # Join with backslashes for line breaks (every 2-3 arguments or when line gets long)
    # Start with base command, then add flags with backslashes
    base_cmd = " ".join(cmd_parts[:3])  # "uv run report-pothole"
    remaining = cmd_parts[3:]
    
    if not remaining:
        return base_cmd
    
    # Group remaining args into pairs (flag + value) and add backslashes
    lines = [base_cmd]
    i = 0
    while i < len(remaining):
        if i + 1 < len(remaining):
            # Pair: flag and value
            line = f"  {remaining[i]} {remaining[i+1]}"
            i += 2
        else:
            # Single remaining arg
            line = f"  {remaining[i]}"
            i += 1
        
        # Add backslash if more args remain
        if i < len(remaining):
            line += " \\"
        lines.append(line)
    
    return " \\\n".join(lines)


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
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode: prompt for attribute values",
    )
    # Attribute flags - choices will be populated from config, but we define them here
    # The actual choices will be validated later
    parser.add_argument(
        "--depth",
        help="Depth category (e.g., lt40mm, gte40mm, gt50mm)",
    )
    parser.add_argument(
        "--edge",
        help="Edge type (e.g., sharp, rounded, gradual)",
    )
    parser.add_argument(
        "--width",
        help="Width/size (e.g., small, medium_fist, large_crater, clusters, longitudinal)",
    )
    parser.add_argument(
        "--location",
        help="Location context (e.g., primary_cycle_line, descent, braking_zone, junction_approach, general). Multiple values comma-separated (e.g., primary_cycle_line,descent)",
    )
    parser.add_argument(
        "--visibility",
        help="Visibility (e.g., obscured_water, obscured_shadows, visible). Multiple values comma-separated (e.g., obscured_water,obscured_shadows)",
    )
    parser.add_argument(
        "--surface",
        help="Surface condition (e.g., exposed_sub_base, loose_gravel, longitudinal_crack, hairline)",
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
        console.print(f"[dim]Interactive mode:[/] {args.interactive}")
        console.print("")

    # Load config
    try:
        config = load_config(args.config)
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
        console.print(f"[dim]Attributes available:[/] {len(config['attributes'])} categories")
        console.print("")

    if not args.folder:
        parser.error("-f/--folder is required")

    # Validate folder and scan for images early — before interactive prompts
    # so the user doesn't waste time if the path is wrong.
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

    # Collect attributes from CLI flags or interactive mode
    attributes = {}
    if args.interactive:
        attributes = _run_interactive_mode(config, console)
    else:
        # Collect from CLI flags
        attrs_config = config["attributes"]
        for attr_name in ["depth", "edge", "width", "location", "visibility", "surface"]:
            attr_value = getattr(args, attr_name, None)
            if attr_value:
                # Validate attribute value exists in config
                if attr_name not in attrs_config:
                    console.print(f"[yellow]Warning:[/] Attribute '{attr_name}' not defined in config. Ignoring.")
                    continue
                
                # Handle multi-select for location and visibility (comma-separated values)
                if attr_name in ["location", "visibility"] and "," in attr_value:
                    values = [v.strip() for v in attr_value.split(",") if v.strip()]
                    invalid_values = [v for v in values if v not in attrs_config[attr_name]]
                    if invalid_values:
                        console.print(f"[red]Error:[/] Invalid value(s) '{', '.join(invalid_values)}' for attribute '{attr_name}'. "
                                    f"Valid values: {', '.join(attrs_config[attr_name].keys())}")
                        raise SystemExit(1)
                    attributes[attr_name] = attr_value  # Keep as comma-separated string
                else:
                    # Single value validation
                    if attr_value not in attrs_config[attr_name]:
                        console.print(f"[red]Error:[/] Invalid value '{attr_value}' for attribute '{attr_name}'. "
                                    f"Valid values: {', '.join(attrs_config[attr_name].keys())}")
                        raise SystemExit(1)
                    attributes[attr_name] = attr_value
    
    if not attributes:
        console.print("[yellow]No attributes specified. Use --interactive or provide attribute flags.[/]")
        console.print("[dim]Example:[/] uv run report-pothole -f /path --depth gt50mm --edge sharp")
        raise SystemExit(1)
    
    if args.verbose:
        console.print("[dim]Selected attributes:[/]")
        for attr_name, attr_value in sorted(attributes.items()):
            # Handle multi-select values
            if attr_name in ["location", "visibility"] and "," in attr_value:
                values = [v.strip() for v in attr_value.split(",")]
                descs = [config["attributes"][attr_name].get(v, v) for v in values]
                console.print(f"[dim]  {attr_name}: {attr_value} ({', '.join(descs)})[/]")
            else:
                desc = config["attributes"][attr_name].get(attr_value, "")
                console.print(f"[dim]  {attr_name}: {attr_value} ({desc})[/]")
        console.print("")
    
    # Generate report text from attributes
    generated_report_text = _generate_report_text(attributes, config)
    
    if args.verbose:
        console.print(f"[dim]Generated report text:[/] {generated_report_text[:100]}...")
        console.print("")
    
    # Build command line for display
    command_line = _build_command_line(args.folder, attributes)
    
    email = config.get("email")
    report_url = config["report_url"]
    advice_for_reporters = config.get("advice_for_reporters", {})

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

    # Build attribute descriptions dict for display
    attribute_descriptions = {}
    for attr_name, attr_value in attributes.items():
        if attr_name in config["attributes"]:
            # Handle multi-select for location and visibility
            if attr_name in ["location", "visibility"] and "," in attr_value:
                values = [v.strip() for v in attr_value.split(",")]
                descs = [config["attributes"][attr_name].get(v, v) for v in values]
                attribute_descriptions[attr_name] = ", ".join(descs)
            elif attr_value in config["attributes"][attr_name]:
                attribute_descriptions[attr_name] = config["attributes"][attr_name][attr_value]
    
    image_names = [p.name for p in paths]
    record = build_report_record(
        earliest,
        geocoded,
        report_url,
        email,
        attributes,
        attribute_descriptions,
        generated_report_text,
        command_line,
        advice_for_reporters,
        image_names,
    )

    # Load check sites for "Existing pothole reports" panel
    check_links: list[tuple[str, str]] = []
    try:
        check_sites = load_check_config()
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        check_sites = []

    if not check_sites:
        console.print(
            "[yellow]Warning:[/] No check sites configured. "
            "See README.md for how to set up conf/pothole-checking.yaml."
        )
    else:
        check_links = [
            (entry["name"], expand_check_url(entry["url"], record.lat, record.lon))
            for entry in check_sites
        ]

    print_report(record, console, check_links=check_links)

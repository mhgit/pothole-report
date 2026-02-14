"""Rich-formatted output for report bundles."""

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pothole_report.extract import ExtractedData
from pothole_report.geocode import GeocodedResult


@dataclass
class ReportRecord:
    """One report bundle ready for output."""

    path: Path
    datetime_taken: str | None
    postcode: str
    address: str
    lat: float
    lon: float
    fill_that_hole_url: str
    google_maps_url: str
    attributes: dict
    attribute_descriptions: dict
    generated_report_text: str
    command_line: str
    advice_for_reporters_text: str
    email: str
    image_names: list[str]


def build_report_record(
    extracted: ExtractedData,
    geocoded: GeocodedResult,
    report_url: str,
    email: str,
    attributes: dict,
    attribute_descriptions: dict,
    generated_report_text: str,
    command_line: str,
    advice_for_reporters: dict,
    image_names: list[str],
) -> ReportRecord:
    """Build a ReportRecord from extracted and geocoded data."""
    base = report_url.rstrip("/")
    lat = round(extracted.lat, 6)
    lon = round(extracted.lon, 6)
    fth_url = f"{base}/around?lat={lat}&lon={lon}&zoom=4"
    gm_url = f"https://www.google.com/maps?q={lat},{lon}"

    # Build advice_for_reporters text from key phrases and pro tip
    advice_lines = []

    key_phrases = advice_for_reporters.get("key_phrases", [])
    if key_phrases:
        phrases_str = ", ".join(key_phrases)
        advice_lines.append(f"[bold]Key Phrases:[/] {phrases_str}")

    pro_tip = advice_for_reporters.get("pro_tip", "")
    if pro_tip:
        advice_lines.append(f"[bold]Pro Tip:[/] {pro_tip}")

    advice_text = "\n".join(advice_lines) if advice_lines else ""

    return ReportRecord(
        path=extracted.path,
        datetime_taken=extracted.datetime_taken,
        postcode=geocoded.postcode,
        address=geocoded.address,
        lat=extracted.lat,
        lon=extracted.lon,
        fill_that_hole_url=fth_url,
        google_maps_url=gm_url,
        attributes=attributes,
        attribute_descriptions=attribute_descriptions,
        generated_report_text=generated_report_text,
        command_line=command_line,
        advice_for_reporters_text=advice_text,
        email=email,
        image_names=image_names,
    )


def _image_table(image_names: list[str]) -> Table:
    """Build a 3-column table of image names, wrapping every third image."""
    table = Table(show_header=False)
    table.add_column(style="cyan")
    table.add_column(style="cyan")
    table.add_column(style="cyan")
    for i in range(0, len(image_names), 3):
        row = image_names[i : i + 3]
        while len(row) < 3:
            row.append("")
        table.add_row(*row)
    return table


def print_report(
    record: ReportRecord,
    console: Console | None = None,
    check_links: list[tuple[str, str]] | None = None,
) -> None:
    """Print one report bundle as a Rich panel.

    Args:
        record: The report data to display.
        console: Rich console (defaults to a new Console).
        check_links: Optional list of (name, url) tuples for existing-reports
            panel.  When non-empty an "Existing pothole reports" panel is
            printed *above* the main report.
    """
    c = console or Console()

    # --- "Existing pothole reports" panel (printed first, if any) ----------
    if check_links:
        link_lines = []
        for name, url in check_links:
            link_lines.append(
                f"[bold]{name}:[/] [bold cyan][link={url}]{url}[/link][/]"
            )
        check_body = Text.from_markup("\n".join(link_lines))
        c.print(
            Panel(
                check_body,
                title="Existing pothole reports",
                border_style="green",
            )
        )
        c.print()  # blank line between panels

    # --- Main report panel -------------------------------------------------
    dt = record.datetime_taken if record.datetime_taken else "—"
    fth_link = f"[bold cyan][link={record.fill_that_hole_url}]Fill That Hole[/link][/]"
    gm_link = f"[bold cyan][link={record.google_maps_url}]Google Maps[/link][/]"

    # Build attributes section
    attr_lines = []
    for attr_name in sorted(record.attributes.keys()):
        desc = record.attribute_descriptions.get(attr_name, "")
        if desc:
            # Show only descriptions without keys for all attributes
            attr_lines.append(f"  {attr_name}: ({desc})")
        else:
            # Fallback: show key if no description available
            attr_value = record.attributes[attr_name]
            attr_lines.append(f"  {attr_name}: {attr_value}")
    attributes_text = "\n".join(attr_lines) if attr_lines else "  (none)"

    body_text = (
        f"[bold]File:[/] {record.path.name}\n"
        f"[bold]Date/Time taken:[/] {dt}\n"
        f"[bold]Postcode:[/] {record.postcode}\n"
        f"[bold]Address:[/] {record.address}\n"
        f"[bold]Coordinates:[/] {record.lat:.4f}, {record.lon:.4f}\n\n"
        f"[bold]Fill That Hole:[/] {fth_link}\n\n"
        f"[bold]Google Maps:[/] {gm_link}\n\n"
        f"[bold]Attributes:[/]\n{attributes_text}\n\n"
        f"[bold]Report:[/]\n{record.generated_report_text}\n\n"
        f"[bold]Report as:[/] {record.email}\n\n"
    )

    # Advice for reporters section (above image listing)
    advice_panel = None
    if record.advice_for_reporters_text:
        advice_panel = Panel(
            Text.from_markup(record.advice_for_reporters_text),
            title="Advice for Reporters",
            border_style="yellow",
        )

    img_table = _image_table(record.image_names)

    # Build content group (without command line - it goes outside the box)
    content_parts = [Text.from_markup(body_text.strip())]
    if advice_panel:
        content_parts.append(advice_panel)
    content_parts.append(img_table)

    content = Group(*content_parts)
    c.print(Panel(content, title=f"Report: {record.path.name}", border_style="blue"))

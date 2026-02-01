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
    description: str
    email: str
    image_names: list[str]


def build_report_record(
    extracted: ExtractedData,
    geocoded: GeocodedResult,
    report_url: str,
    email: str,
    description: str,
    image_names: list[str],
) -> ReportRecord:
    """Build a ReportRecord from extracted and geocoded data."""
    base = report_url.rstrip("/")
    lat = round(extracted.lat, 6)
    lon = round(extracted.lon, 6)
    fth_url = f"{base}/around?lat={lat}&lon={lon}&zoom=4"
    gm_url = f"https://www.google.com/maps?q={lat},{lon}"
    return ReportRecord(
        path=extracted.path,
        datetime_taken=extracted.datetime_taken,
        postcode=geocoded.postcode,
        address=geocoded.address,
        lat=extracted.lat,
        lon=extracted.lon,
        fill_that_hole_url=fth_url,
        google_maps_url=gm_url,
        description=description,
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


def print_report(record: ReportRecord, console: Console | None = None) -> None:
    """Print one report bundle as a Rich panel."""
    c = console or Console()
    dt = record.datetime_taken if record.datetime_taken else "—"
    fth_link = f"[bold cyan][link={record.fill_that_hole_url}]Fill That Hole[/link][/]"
    gm_link = f"[bold cyan][link={record.google_maps_url}]Google Maps[/link][/]"
    body_text = (
        f"[bold]File:[/] {record.path.name}\n"
        f"[bold]Date/Time taken:[/] {dt}\n"
        f"[bold]Postcode:[/] {record.postcode}\n"
        f"[bold]Address:[/] {record.address}\n"
        f"[bold]Coordinates:[/] {record.lat:.4f}, {record.lon:.4f}\n\n"
        f"[bold]Fill That Hole:[/] {fth_link}\n\n"
        f"[bold]Google Maps:[/] {gm_link}\n\n"
        f"[bold]Description:[/]\n{record.description}\n\n"
        f"[bold]Report as:[/] {record.email}\n\n"
    )
    img_table = _image_table(record.image_names)
    content = Group(Text.from_markup(body_text.strip()), img_table)
    c.print(Panel(content, title=f"Report: {record.path.name}", border_style="blue"))

"""Terminal output for report bundles (plain text, copy-paste friendly)."""

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

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
        advice_lines.append(f"Key Phrases: {phrases_str}")

    pro_tip = advice_for_reporters.get("pro_tip", "")
    if pro_tip:
        advice_lines.append(f"Pro Tip: {pro_tip}")

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


def _format_image_list(image_names: list[str]) -> str:
    """Format image names as an indented list."""
    if not image_names:
        return "  (none)"
    return "\n".join(f"  {name}" for name in image_names)


def print_report(
    record: ReportRecord,
    console: Console | None = None,
    check_links: list[tuple[str, str]] | None = None,
) -> None:
    """Print one report bundle as plain text (no box borders).

    Args:
        record: The report data to display.
        console: Rich console (defaults to a new Console).
        check_links: Optional list of (name, url) tuples for existing-reports
            links.  When non-empty an "Existing pothole reports" section is
            printed above the main report.
    """
    c = console or Console()
    lines: list[str] = []

    if check_links:
        lines.append("Existing pothole reports")
        lines.append("")
        for name, url in check_links:
            lines.append(f"{name}: {url}")
        lines.append("")

    dt = record.datetime_taken if record.datetime_taken else "n/a"

    attr_lines = []
    for attr_name in sorted(record.attributes.keys()):
        desc = record.attribute_descriptions.get(attr_name, "")
        if desc:
            attr_lines.append(f"  {attr_name}: ({desc})")
        else:
            attr_value = record.attributes[attr_name]
            attr_lines.append(f"  {attr_name}: {attr_value}")
    attributes_text = "\n".join(attr_lines) if attr_lines else "  (none)"

    lines.extend(
        [
            f"Report: {record.path.name}",
            "",
            f"File: {record.path.name}",
            f"Date/Time taken: {dt}",
            f"Postcode: {record.postcode}",
            f"Address: {record.address}",
            f"Coordinates: {record.lat:.4f}, {record.lon:.4f}",
            "",
            f"Fill That Hole: {record.fill_that_hole_url}",
            f"Google Maps: {record.google_maps_url}",
            "",
            "Attributes:",
            attributes_text,
            "",
            "Report:",
            record.generated_report_text,
            "",
            f"Report as: {record.email}",
        ]
    )

    if record.advice_for_reporters_text:
        lines.extend(
            [
                "",
                "Advice for Reporters",
                "",
                record.advice_for_reporters_text,
            ]
        )

    lines.extend(
        [
            "",
            "Images:",
            _format_image_list(record.image_names),
        ]
    )

    c.print("\n".join(lines))

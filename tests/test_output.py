"""Tests for output module."""

from pathlib import Path

from pothole_report.extract import ExtractedData
from pothole_report.geocode import GeocodedResult
from pothole_report.output import build_report_record, print_report, ReportRecord


def test_build_report_record_uses_attributes() -> None:
    """Build report uses provided attributes and generated report text."""
    extracted = ExtractedData(
        path=Path("IMG_001.jpg"),
        lat=51.5,
        lon=-0.1,
        datetime_taken="2025-01-15 14:32",
    )
    geocoded = GeocodedResult(postcode="GU1 4RB", address="High Street, Guildford")
    attributes = {"depth": "gt50mm", "edge": "sharp"}
    attribute_descriptions = {"depth": "Greater than 50mm", "edge": "Sharp edges"}
    generated_report_text = "EMERGENCY: Exceeds 50mm defect"
    command_line = "uv run report-pothole -f /path --depth gt50mm --edge sharp"
    advice_for_reporters = {
        "key_phrases": ["phrase1", "phrase2"],
        "pro_tip": "Test pro tip",
    }
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://www.fillthathole.org.uk",
        email="test@example.com",
        attributes=attributes,
        attribute_descriptions=attribute_descriptions,
        generated_report_text=generated_report_text,
        command_line=command_line,
        advice_for_reporters=advice_for_reporters,
        image_names=["IMG_001.jpg"],
    )
    assert record.postcode == "GU1 4RB"
    assert record.email == "test@example.com"
    assert record.attributes == attributes
    assert record.attribute_descriptions == attribute_descriptions
    assert record.generated_report_text == generated_report_text
    assert record.command_line == command_line
    assert "phrase1" in record.advice_for_reporters_text
    assert "phrase2" in record.advice_for_reporters_text
    assert "Test pro tip" in record.advice_for_reporters_text
    assert "51.5" in record.fill_that_hole_url
    assert "-0.1" in record.fill_that_hole_url
    assert "around?lat=" in record.fill_that_hole_url
    assert "51.5" in record.google_maps_url
    assert record.datetime_taken == "2025-01-15 14:32"


def test_build_report_record_with_none_datetime() -> None:
    """Build report handles None datetime_taken."""
    extracted = ExtractedData(
        path=Path("IMG_001.jpg"),
        lat=51.5,
        lon=-0.1,
        datetime_taken=None,
    )
    geocoded = GeocodedResult(postcode="SW1A 1AA", address="Downing St")
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://example.com",
        email="a@b.com",
        attributes={"depth": "lt40mm"},
        attribute_descriptions={"depth": "Less than 40mm"},
        generated_report_text="Test report",
        command_line="uv run report-pothole -f /path --depth lt40mm",
        advice_for_reporters={"key_phrases": [], "pro_tip": ""},
        image_names=["IMG_001.jpg"],
    )
    assert record.generated_report_text == "Test report"
    assert record.datetime_taken is None


def test_build_report_record_strips_trailing_slash() -> None:
    """Report URL trailing slash is stripped before building FTH URL."""
    extracted = ExtractedData(path=Path("x.jpg"), lat=0.0, lon=0.0, datetime_taken=None)
    geocoded = GeocodedResult(postcode="X", address="Y")
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://fillthathole.org.uk/",
        email="e@e.com",
        attributes={"depth": "gte40mm"},
        attribute_descriptions={"depth": "40mm or greater"},
        generated_report_text="Test report",
        command_line="uv run report-pothole -f /path --depth gte40mm",
        advice_for_reporters={"key_phrases": [], "pro_tip": ""},
        image_names=["x.jpg"],
    )
    assert (
        record.fill_that_hole_url
        == "https://fillthathole.org.uk/around?lat=0.0&lon=0.0&zoom=4"
    )


def test_print_report_no_crash() -> None:
    """print_report runs without error (output captured)."""
    from io import StringIO

    from rich.console import Console

    record = ReportRecord(
        path=Path("test.jpg"),
        datetime_taken="2025-01-01 12:00",
        postcode="XX1 1XX",
        address="Test Rd",
        lat=51.0,
        lon=0.0,
        fill_that_hole_url="https://example.com",
        google_maps_url="https://maps.example.com",
        attributes={"depth": "gt50mm"},
        attribute_descriptions={"depth": "Greater than 50mm"},
        generated_report_text="Test report text",
        command_line="uv run report-pothole -f /path --depth gt50mm",
        advice_for_reporters_text="Test advice",
        email="t@t.com",
        image_names=["test.jpg", "other.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    assert "test.jpg" in out
    assert "XX1 1XX" in out


def test_print_report_includes_image_table() -> None:
    """print_report includes image names in a table (4 images => 2 rows)."""
    from io import StringIO

    from rich.console import Console

    record = ReportRecord(
        path=Path("a.jpg"),
        datetime_taken="2025-01-01 12:00",
        postcode="XX1 1XX",
        address="A",
        lat=51.0,
        lon=0.0,
        fill_that_hole_url="https://a.com",
        google_maps_url="https://m.com",
        attributes={"depth": "lt40mm"},
        attribute_descriptions={"depth": "Less than 40mm"},
        generated_report_text="Test report",
        command_line="uv run report-pothole -f /path --depth lt40mm",
        advice_for_reporters_text="Advice",
        email="e@e.com",
        image_names=["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    assert "img1.jpg" in out
    assert "img2.jpg" in out
    assert "img3.jpg" in out
    assert "img4.jpg" in out


def test_print_report_includes_attributes() -> None:
    """print_report includes attributes section with descriptions."""
    from io import StringIO

    from rich.console import Console

    record = ReportRecord(
        path=Path("test.jpg"),
        datetime_taken="2025-01-01 12:00",
        postcode="XX1 1XX",
        address="Test Rd",
        lat=51.0,
        lon=0.0,
        fill_that_hole_url="https://example.com",
        google_maps_url="https://maps.example.com",
        attributes={"depth": "gt50mm", "edge": "sharp"},
        attribute_descriptions={"depth": "Greater than 50mm", "edge": "Sharp edges"},
        generated_report_text="Test report text",
        command_line="uv run report-pothole -f /path --depth gt50mm --edge sharp",
        advice_for_reporters_text="[bold]Key Phrases:[/] phrase1, phrase2\n[bold]Pro Tip:[/] Test tip",
        email="t@t.com",
        image_names=["test.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    # Should include attributes section with descriptions
    assert "Attributes:" in out
    assert "depth:" in out
    assert "Greater than 50mm" in out
    assert "Sharp edges" in out
    # Should include generated report text
    assert "Test report text" in out


def test_print_report_includes_advice_section() -> None:
    """print_report includes Advice for Reporters section when present."""
    from io import StringIO

    from rich.console import Console

    record = ReportRecord(
        path=Path("test.jpg"),
        datetime_taken="2025-01-01 12:00",
        postcode="XX1 1XX",
        address="Test Rd",
        lat=51.0,
        lon=0.0,
        fill_that_hole_url="https://example.com",
        google_maps_url="https://maps.example.com",
        attributes={"depth": "gte40mm"},
        attribute_descriptions={"depth": "40mm or greater"},
        generated_report_text="Test report",
        command_line="uv run report-pothole -f /path --depth gte40mm",
        advice_for_reporters_text="[bold]Key Phrases:[/] phrase1, phrase2\n[bold]Pro Tip:[/] Test tip",
        email="t@t.com",
        image_names=["test.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    # Should include advice section content
    assert "phrase1" in out or "phrase2" in out
    assert "Test tip" in out


# ---------------------------------------------------------------------------
# Tests for "Existing pothole reports" panel (check_links)
# ---------------------------------------------------------------------------


def _make_record(**overrides) -> ReportRecord:
    """Helper to build a minimal ReportRecord for tests."""
    defaults = {
        "path": Path("test.jpg"),
        "datetime_taken": "2025-01-01 12:00",
        "postcode": "XX1 1XX",
        "address": "Test Rd",
        "lat": 51.0,
        "lon": 0.0,
        "fill_that_hole_url": "https://example.com",
        "google_maps_url": "https://maps.example.com",
        "attributes": {"depth": "gt50mm"},
        "attribute_descriptions": {"depth": "Greater than 50mm"},
        "generated_report_text": "Test report text",
        "command_line": "uv run report-pothole -f /path --depth gt50mm",
        "advice_for_reporters_text": "",
        "email": "t@t.com",
        "image_names": ["test.jpg"],
    }
    defaults.update(overrides)
    return ReportRecord(**defaults)


def test_print_report_with_check_links() -> None:
    """print_report shows 'Existing pothole reports' panel when check_links provided."""
    from io import StringIO

    from rich.console import Console

    record = _make_record()
    check_links = [
        (
            "Fill That Hole",
            "https://www.fillthathole.org.uk/around?lat=51.0&lon=0.0&zoom=16",
        ),
        (
            "Surrey (Tell Us)",
            "https://tellus.surreycc.gov.uk/reports/Surrey?lat=51.0&lon=0.0",
        ),
    ]
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console, check_links=check_links)
    out = console.file.getvalue()
    assert "Existing pothole reports" in out
    assert "Fill That Hole" in out
    assert "Surrey" in out
    assert "fillthathole.org.uk" in out


def test_print_report_no_check_links() -> None:
    """print_report omits 'Existing pothole reports' panel when check_links is None."""
    from io import StringIO

    from rich.console import Console

    record = _make_record()
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console, check_links=None)
    out = console.file.getvalue()
    assert "Existing pothole reports" not in out


def test_print_report_empty_check_links() -> None:
    """print_report omits 'Existing pothole reports' panel when check_links is empty."""
    from io import StringIO

    from rich.console import Console

    record = _make_record()
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console, check_links=[])
    out = console.file.getvalue()
    assert "Existing pothole reports" not in out

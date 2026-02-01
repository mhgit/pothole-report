"""Tests for output module."""

from pathlib import Path

from pothole_report.extract import ExtractedData
from pothole_report.geocode import GeocodedResult
from pothole_report.output import build_report_record, print_report, ReportRecord


def test_build_report_record_uses_report_template() -> None:
    """Build report uses provided report_template as main text."""
    extracted = ExtractedData(
        path=Path("IMG_001.jpg"),
        lat=51.5,
        lon=-0.1,
        datetime_taken="2025-01-15 14:32",
    )
    geocoded = GeocodedResult(postcode="GU1 4RB", address="High Street, Guildford")
    report_template = "Test report template text"
    description = "Test description"
    visual_indicators = "Test visual indicators"
    advice_for_reporters = {
        "key_phrases": ["phrase1", "phrase2"],
        "pro_tip": "Test pro tip",
    }
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://www.fillthathole.org.uk",
        email="test@example.com",
        report_template=report_template,
        description=description,
        visual_indicators=visual_indicators,
        advice_for_reporters=advice_for_reporters,
        image_names=["IMG_001.jpg"],
    )
    assert record.postcode == "GU1 4RB"
    assert record.email == "test@example.com"
    assert record.report_template == report_template
    assert record.description == description
    assert record.visual_indicators == visual_indicators
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
        report_template="Template",
        description="Desc",
        visual_indicators="Indicators",
        advice_for_reporters={"key_phrases": [], "pro_tip": ""},
        image_names=["IMG_001.jpg"],
    )
    assert record.report_template == "Template"
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
        report_template="Test template",
        description="Test description",
        visual_indicators="Test indicators",
        advice_for_reporters={"key_phrases": [], "pro_tip": ""},
        image_names=["x.jpg"],
    )
    assert record.fill_that_hole_url == "https://fillthathole.org.uk/around?lat=0.0&lon=0.0&zoom=4"


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
        report_template="Test template",
        description="Test desc",
        visual_indicators="Test indicators",
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
        report_template="Template",
        description="D",
        visual_indicators="V",
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


def test_print_report_includes_advice_section() -> None:
    """print_report includes Advice for Reporters section above image listing."""
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
        report_template="Test template text",
        description="Test description",
        visual_indicators="Test visual indicators",
        advice_for_reporters_text="[bold]Description:[/] Test description\n[bold]Visual Indicators:[/] Test visual indicators\n[bold]Key Phrases:[/] phrase1, phrase2\n[bold]Pro Tip:[/] Test tip",
        email="t@t.com",
        image_names=["test.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    # Should include report_template in main body
    assert "Test template text" in out
    # Should include advice section content
    assert "Test description" in out
    assert "Test visual indicators" in out
    assert "phrase1" in out or "phrase2" in out
    assert "Test tip" in out


def test_print_report_uses_report_template() -> None:
    """print_report uses report_template as main body text, not description."""
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
        report_template="This is the report template text",
        description="This is the description (should be in advice section)",
        visual_indicators="Visual indicators",
        advice_for_reporters_text="[bold]Description:[/] This is the description (should be in advice section)",
        email="t@t.com",
        image_names=["test.jpg"],
    )
    console = Console(file=StringIO(), force_terminal=False)
    print_report(record, console=console)
    out = console.file.getvalue()
    # report_template should appear in "Report Template:" section
    assert "Report Template:" in out
    assert "This is the report template text" in out

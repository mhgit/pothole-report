"""Tests for output module."""

from pathlib import Path

from pothole_batcher.extract import ExtractedData
from pothole_batcher.geocode import GeocodedResult
from pothole_batcher.config import DEFAULT_TEMPLATES
from pothole_batcher.output import build_report_record, print_report, ReportRecord


def test_build_report_record_high_risk() -> None:
    """Build report uses provided description."""
    extracted = ExtractedData(
        path=Path("IMG_001.jpg"),
        lat=51.5,
        lon=-0.1,
        datetime_taken="2025-01-15 14:32",
    )
    geocoded = GeocodedResult(postcode="GU1 4RB", address="High Street, Guildford")
    desc = DEFAULT_TEMPLATES["default"]
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://www.fillthathole.org.uk",
        email="test@example.com",
        description=desc,
        image_names=["IMG_001.jpg"],
    )
    assert record.postcode == "GU1 4RB"
    assert record.email == "test@example.com"
    assert record.description == desc
    assert "51.5" in record.fill_that_hole_url
    assert "-0.1" in record.fill_that_hole_url
    assert "around?lat=" in record.fill_that_hole_url
    assert "51.5" in record.google_maps_url
    assert record.datetime_taken == "2025-01-15 14:32"


def test_build_report_record_hidden_template() -> None:
    """Build report uses provided description."""
    extracted = ExtractedData(
        path=Path("IMG_001.jpg"),
        lat=51.5,
        lon=-0.1,
        datetime_taken=None,
    )
    geocoded = GeocodedResult(postcode="SW1A 1AA", address="Downing St")
    desc = DEFAULT_TEMPLATES["default"]
    record = build_report_record(
        extracted,
        geocoded,
        report_url="https://example.com",
        email="a@b.com",
        description=desc,
        image_names=["IMG_001.jpg"],
    )
    assert record.description == desc
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
        description="Test description",
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
        description="Test desc",
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
        description="D",
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

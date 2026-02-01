"""Tests for extract module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from pothole_report.extract import (
    ExtractedData,
    extract,
    extract_all,
    extract_datetime,
)


def test_extract_returns_none_for_image_without_gps(tmp_path: Path) -> None:
    """Extract returns None when image has no GPS EXIF."""
    from PIL import Image

    img_path = tmp_path / "no_gps.jpg"
    img = Image.new("RGB", (5, 5), color="red")
    img.save(img_path, "JPEG")
    assert extract(img_path) is None


def test_extract_datetime_returns_none_for_image_without_exif(tmp_path: Path) -> None:
    """Extract datetime returns None when no EXIF datetime."""
    from PIL import Image

    img_path = tmp_path / "no_exif.jpg"
    img = Image.new("RGB", (5, 5), color="red")
    img.save(img_path, "JPEG")
    assert extract_datetime(img_path) is None


def test_extract_all_returns_none_for_no_gps(tmp_path: Path) -> None:
    """extract_all returns None when no GPS data."""
    from PIL import Image

    img_path = tmp_path / "no_gps.jpg"
    img = Image.new("RGB", (5, 5), color="red")
    img.save(img_path, "JPEG")
    assert extract_all(img_path) is None


@patch("pothole_report.extract.Image")
def test_extract_returns_none_when_dms_has_fewer_than_3_elements(
    mock_image: MagicMock, tmp_path: Path
) -> None:
    """Extract returns None when GPS DMS arrays have fewer than 3 elements (avoids IndexError)."""
    gps_ifd = {
        1: "N",
        2: ((51, 1), (30, 1)),  # only 2 elements - malformed
        3: "W",
        4: ((0, 1), (6, 1), (0, 1)),
    }
    exif_mock = MagicMock()
    exif_mock.get_ifd.return_value = gps_ifd

    img_mock = MagicMock()
    img_mock.getexif.return_value = exif_mock

    cm = MagicMock()
    cm.__enter__.return_value = img_mock
    cm.__exit__.return_value = False
    mock_image.open.return_value = cm

    img_path = tmp_path / "malformed.jpg"
    img_path.touch()
    assert extract(img_path) is None


@patch("pothole_report.extract.Image")
def test_extract_returns_coords_when_gps_present(mock_image: MagicMock, tmp_path: Path) -> None:
    """Extract returns (lat, lon) when GPS EXIF is present."""
    # GPS: 51°30'0"N, 0°6'0"W -> 51.5, -0.1
    gps_ifd = {
        1: "N",   # GPSLatitudeRef
        2: ((51, 1), (30, 1), (0, 1)),  # GPSLatitude (51, 30, 0)
        3: "W",   # GPSLongitudeRef
        4: ((0, 1), (6, 1), (0, 1)),    # GPSLongitude (0, 6, 0)
    }
    exif_mock = MagicMock()
    exif_mock.get_ifd.return_value = gps_ifd

    img_mock = MagicMock()
    img_mock.getexif.return_value = exif_mock

    cm = MagicMock()
    cm.__enter__.return_value = img_mock
    cm.__exit__.return_value = False
    mock_image.open.return_value = cm

    img_path = tmp_path / "gps.jpg"
    img_path.touch()
    result = extract(img_path)
    assert result is not None
    lat, lon = result
    assert abs(lat - 51.5) < 0.001
    assert abs(lon - (-0.1)) < 0.001


@patch("pothole_report.extract.Image")
def test_extract_datetime_parses_exif_format(mock_image: MagicMock, tmp_path: Path) -> None:
    """Extract datetime parses EXIF DateTimeOriginal format."""
    exif_mock = MagicMock()
    exif_mock.get.side_effect = lambda tag: "2025:01:15 14:32:00" if tag == 36867 else None

    img_mock = MagicMock()
    img_mock.getexif.return_value = exif_mock

    cm = MagicMock()
    cm.__enter__.return_value = img_mock
    cm.__exit__.return_value = False
    mock_image.open.return_value = cm

    img_path = tmp_path / "with_dt.jpg"
    img_path.touch()
    result = extract_datetime(img_path)
    assert result == "2025-01-15 14:32"


@patch("pothole_report.extract.Image")
def test_extract_all_returns_extracted_data(mock_image: MagicMock, tmp_path: Path) -> None:
    """extract_all returns ExtractedData when GPS present."""
    gps_ifd = {
        1: "N",
        2: ((51, 1), (0, 1), (0, 1)),
        3: "W",
        4: ((0, 1), (0, 1), (0, 1)),
    }
    exif_mock = MagicMock()
    exif_mock.get_ifd.return_value = gps_ifd
    exif_mock.get.side_effect = lambda tag: "2025:06:01 09:00:00" if tag in (36867, 306) else None

    img_mock = MagicMock()
    img_mock.getexif.return_value = exif_mock

    cm = MagicMock()
    cm.__enter__.return_value = img_mock
    cm.__exit__.return_value = False
    mock_image.open.return_value = cm

    img_path = tmp_path / "full.jpg"
    img_path.touch()
    result = extract_all(img_path)
    assert result is not None
    assert isinstance(result, ExtractedData)
    assert result.path == img_path
    assert result.lat == 51.0
    assert result.lon == -0.0
    assert result.datetime_taken == "2025-06-01 09:00"

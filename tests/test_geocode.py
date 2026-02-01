"""Tests for geocode module."""

from unittest.mock import MagicMock, patch

from geopy.location import Location

from pothole_report.geocode import GeocodedResult, reverse_geocode


@patch("pothole_report.geocode._get_geolocator")
def test_reverse_geocode_returns_result_when_postcode_present(
    mock_get_geolocator: MagicMock,
) -> None:
    """Reverse geocode returns GeocodedResult when location has postcode."""
    location = MagicMock(spec=Location)
    location.raw = {
        "address": {"postcode": "GU1 4RB"},
    }
    location.address = "High Street, Guildford GU1 4RB, UK"

    geolocator = MagicMock()
    geolocator.reverse.return_value = location
    mock_get_geolocator.return_value = geolocator

    result = reverse_geocode(51.5, -0.1)
    assert result is not None
    assert isinstance(result, GeocodedResult)
    assert result.postcode == "GU1 4RB"
    assert result.address == "High Street, Guildford GU1 4RB, UK"


@patch("pothole_report.geocode._get_geolocator")
def test_reverse_geocode_returns_none_when_no_postcode(
    mock_get_geolocator: MagicMock,
) -> None:
    """Reverse geocode returns None when address has no postcode."""
    location = MagicMock(spec=Location)
    location.raw = {"address": {}}
    location.address = "Somewhere"

    geolocator = MagicMock()
    geolocator.reverse.return_value = location
    mock_get_geolocator.return_value = geolocator

    result = reverse_geocode(0.0, 0.0)
    assert result is None


@patch("pothole_report.geocode._get_geolocator")
def test_reverse_geocode_returns_none_when_location_none(
    mock_get_geolocator: MagicMock,
) -> None:
    """Reverse geocode returns None when geolocator returns None."""
    geolocator = MagicMock()
    geolocator.reverse.return_value = None
    mock_get_geolocator.return_value = geolocator

    result = reverse_geocode(51.5, -0.1)
    assert result is None


@patch("pothole_report.geocode._get_geolocator")
def test_reverse_geocode_returns_none_when_postcode_not_string(
    mock_get_geolocator: MagicMock,
) -> None:
    """Reverse geocode returns None when postcode is None or non-string (avoids AttributeError)."""
    location = MagicMock(spec=Location)
    location.raw = {"address": {"postcode": None}}
    location.address = "Somewhere"

    geolocator = MagicMock()
    geolocator.reverse.return_value = location
    mock_get_geolocator.return_value = geolocator

    result = reverse_geocode(51.5, -0.1)
    assert result is None


@patch("pothole_report.geocode._get_geolocator")
def test_reverse_geocode_returns_none_on_exception(
    mock_get_geolocator: MagicMock,
) -> None:
    """Reverse geocode returns None when geolocator raises."""
    geolocator = MagicMock()
    geolocator.reverse.side_effect = Exception("Network error")
    mock_get_geolocator.return_value = geolocator

    result = reverse_geocode(51.5, -0.1)
    assert result is None

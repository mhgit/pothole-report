"""Reverse geocode coordinates to UK postcode and address via geopy."""

from dataclasses import dataclass

from geopy.geocoders import Nominatim
from geopy.location import Location


def _get_geolocator() -> Nominatim:
    return Nominatim(user_agent="pothole-batcher/0.1.0")


@dataclass
class GeocodedResult:
    """Result of reverse geocoding."""

    postcode: str
    address: str


def reverse_geocode(lat: float, lon: float) -> GeocodedResult | None:
    """Reverse geocode (lat, lon) to UK postcode and address. Returns None on failure."""
    geolocator = _get_geolocator()
    try:
        location: Location | None = geolocator.reverse(f"{lat}, {lon}")
        if location is None:
            return None
        raw = location.raw.get("address") if location.raw else {}
        if not isinstance(raw, dict):
            raw = {}
        postcode = raw.get("postcode")
        postcode = (postcode or "").strip() if isinstance(postcode, str) else ""
        if not postcode:
            return None
        return GeocodedResult(postcode=postcode, address=location.address or "")
    except Exception:
        return None

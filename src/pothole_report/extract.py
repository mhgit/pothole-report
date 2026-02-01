"""Extract GPS coordinates and datetime from image EXIF via Pillow."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

# EXIF tag IDs
GPS_INFO = 34853  # GPSInfo
DATE_TIME_ORIGINAL = 36867
DATE_TIME = 306


def _to_float(v: int | float | tuple[int, int]) -> float:
    """Convert EXIF Rational (numerator, denominator) or int to float."""
    if isinstance(v, tuple) and len(v) == 2:
        return v[0] / v[1] if v[1] else 0.0
    return float(v)


def _dms_to_decimal(dms: tuple[float, float, float], ref: str) -> float:
    """Convert degrees, minutes, seconds to decimal degrees."""
    d, m, s = dms
    decimal = d + (m / 60) + (s / 3600)
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _parse_exif_datetime(value: str | None) -> str | None:
    """Parse EXIF datetime to YYYY-MM-DD HH:MM format. Returns None if invalid."""
    if not value or not isinstance(value, str):
        return None
    try:
        # EXIF format: "YYYY:MM:DD HH:MM:SS"
        dt = datetime.strptime(value.strip()[:19], "%Y:%m:%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None


def extract(path: Path) -> tuple[float, float] | None:
    """Extract (lat, lon) from image EXIF. Returns None if no GPS data."""
    with Image.open(path) as img:
        exif = img.getexif()
        if not exif:
            return None
        gps = exif.get_ifd(GPS_INFO)
        if not gps:
            return None
        lat_data = gps.get(2)  # GPSLatitude
        lat_ref = gps.get(1)   # GPSLatitudeRef
        lon_data = gps.get(4)  # GPSLongitude
        lon_ref = gps.get(3)   # GPSLongitudeRef
        if not all([lat_data, lat_ref, lon_data, lon_ref]):
            return None
        if len(lat_data) != 3 or len(lon_data) != 3:
            return None
        lat = _dms_to_decimal(
            (_to_float(lat_data[0]), _to_float(lat_data[1]), _to_float(lat_data[2])),
            str(lat_ref),
        )
        lon = _dms_to_decimal(
            (_to_float(lon_data[0]), _to_float(lon_data[1]), _to_float(lon_data[2])),
            str(lon_ref),
        )
        return (lat, lon)


def extract_datetime(path: Path) -> str | None:
    """Extract photo taken datetime from EXIF. Returns YYYY-MM-DD HH:MM or None."""
    with Image.open(path) as img:
        exif = img.getexif()
        if not exif:
            return None
        value = exif.get(DATE_TIME_ORIGINAL) or exif.get(DATE_TIME)
        return _parse_exif_datetime(value)


@dataclass
class ExtractedData:
    """Result of EXIF extraction for one image."""

    path: Path
    lat: float
    lon: float
    datetime_taken: str | None


def extract_all(path: Path) -> ExtractedData | None:
    """Extract GPS and datetime. Returns None if no GPS (skip this image)."""
    coords = extract(path)
    if coords is None:
        return None
    lat, lon = coords
    dt = extract_datetime(path)
    return ExtractedData(path=path, lat=lat, lon=lon, datetime_taken=dt)

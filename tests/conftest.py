"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file (no email - from keyring) and return its path."""
    config_path = tmp_path / "pothole-report.yaml"
    config_path.write_text(
        'report_url: "https://example.fillthathole.org"\n',
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def temp_photo_dir(tmp_path: Path) -> Path:
    """Create a temp dir with a minimal image (no GPS) for scan tests."""
    img_path = tmp_path / "photo.jpg"
    # Create minimal 1x1 JPEG using Pillow
    from PIL import Image

    img = Image.new("RGB", (1, 1), color="red")
    img.save(img_path, "JPEG")
    return tmp_path



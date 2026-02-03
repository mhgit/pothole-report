"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file (no email - from keyring) and return its path."""
    config_path = tmp_path / "pothole-report.yaml"
    config_content = '''report_url: "https://example.fillthathole.org"
attributes:
  depth:
    lt40mm: "Less than 40mm (sub-intervention)"
    gte40mm: "40mm or greater (meets intervention level)"
    gt50mm: "Greater than 50mm (emergency intervention)"
  edge:
    sharp: "Sharp, vertical shear edges"
    rounded: "Rounded edges"
  location:
    primary_cycle_line: "Primary cycle line / where cyclist expected"
    general: "General route"
report_template: "{severity}: {depth_description} defect located {location_description}."
attribute_phrases:
  severity:
    gt50mm_sharp_primary_cycle_line: "EMERGENCY"
    gte40mm_primary_cycle_line: "HIGH RISK"
  depth_description:
    lt40mm: "less than 40mm deep"
    gte40mm: "40mm or greater"
    gt50mm: "exceeds 50mm"
  location_description:
    primary_cycle_line: "in the primary line of travel"
    general: "on a general route"
advice_for_reporters:
  key_phrases:
    - "Test phrase 1"
    - "Test phrase 2"
  pro_tip: "Test pro tip"
'''
    config_path.write_text(config_content, encoding="utf-8")
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



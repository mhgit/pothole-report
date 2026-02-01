"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file (no email - from keyring) and return its path."""
    config_path = tmp_path / "pothole-report.yaml"
    config_content = '''report_url: "https://example.fillthathole.org"
risk_levels:
  level_1_emergency:
    description: "Emergency level description"
    visual_indicators: "Emergency visual indicators"
    report_template: "Emergency report template"
  level_2_high_priority:
    description: "High priority description"
    visual_indicators: "High priority visual indicators"
    report_template: "High priority report template"
  level_3_medium_hazard:
    description: "Medium hazard description"
    visual_indicators: "Medium hazard visual indicators"
    report_template: "Medium hazard report template"
  level_4_developing_risk:
    description: "Developing risk description"
    visual_indicators: "Developing risk visual indicators"
    report_template: "Developing risk report template"
  level_5_monitoring_nuisance:
    description: "Monitoring nuisance description"
    visual_indicators: "Monitoring nuisance visual indicators"
    report_template: "Monitoring nuisance report template"
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



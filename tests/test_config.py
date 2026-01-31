"""Tests for config module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pothole_batcher.config import load_config


@patch("pothole_batcher.config._get_email_from_keyring")
def test_load_config_valid(mock_keyring: object, temp_config: Path) -> None:
    """Load valid config returns report_url, email, and templates."""
    mock_keyring.return_value = "test@example.com"
    config = load_config(temp_config)
    assert config["report_url"] == "https://example.fillthathole.org"
    assert config["email"] == "test@example.com"
    assert "templates" in config
    assert "high-risk" in config["templates"]


@patch("pothole_batcher.config._get_email_from_keyring")
def test_load_config_raises_when_email_missing(mock_keyring: object, temp_config: Path) -> None:
    """Load config raises ValueError when keyring has no email."""
    mock_keyring.return_value = None
    with pytest.raises(ValueError) as exc_info:
        load_config(temp_config)
    assert "Email not found in keyring" in str(exc_info.value)


def test_load_config_missing_file() -> None:
    """Missing config raises FileNotFoundError with helpful message."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_config(Path("/nonexistent/pothole-batcher.yaml"))
    assert "Config not found" in str(exc_info.value)
    assert "pothole-batcher.yaml" in str(exc_info.value)


@patch("pothole_batcher.config._get_email_from_keyring")
def test_load_config_empty_file(mock_keyring: object, tmp_path: Path) -> None:
    """Empty config returns defaults and email from keyring."""
    mock_keyring.return_value = "from@keyring.com"
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("", encoding="utf-8")
    config = load_config(config_path)
    assert config["report_url"] == "https://www.fillthathole.org.uk"
    assert config["email"] == "from@keyring.com"
    assert "high-risk" in config["templates"]


@patch("pothole_batcher.config._get_email_from_keyring")
def test_load_config_partial(mock_keyring: object, tmp_path: Path) -> None:
    """Partial config uses defaults for missing keys."""
    mock_keyring.return_value = "custom@test.com"
    config_path = tmp_path / "partial.yaml"
    config_path.write_text("", encoding="utf-8")
    config = load_config(config_path)
    assert config["report_url"] == "https://www.fillthathole.org.uk"
    assert config["email"] == "custom@test.com"
    assert "templates" in config


@patch("pothole_batcher.config._get_email_from_keyring")
def test_load_config_templates_from_yaml(mock_keyring: object, tmp_path: Path) -> None:
    """Custom templates in YAML override defaults."""
    mock_keyring.return_value = "u@example.com"
    config_path = tmp_path / "with_templates.yaml"
    config_path.write_text(
        'report_url: "https://x.org"\ntemplates:\n  my-report: "Custom text here."\n',
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config["templates"]["my-report"] == "Custom text here."

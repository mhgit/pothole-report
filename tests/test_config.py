"""Tests for config module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pothole_report.config import _config_paths, _find_project_root, load_config


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_valid(mock_keyring: object, temp_config: Path) -> None:
    """Load valid config returns report_url, email, risk_levels, and advice_for_reporters."""
    mock_keyring.return_value = "test@example.com"
    config = load_config(temp_config)
    assert config["report_url"] == "https://example.fillthathole.org"
    assert config["email"] == "test@example.com"
    assert "risk_levels" in config
    assert "level_1_emergency" in config["risk_levels"]
    assert "level_3_medium_hazard" in config["risk_levels"]
    assert "advice_for_reporters" in config
    assert "key_phrases" in config["advice_for_reporters"]
    assert "pro_tip" in config["advice_for_reporters"]


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_raises_when_email_missing(mock_keyring: object, temp_config: Path) -> None:
    """Load config raises ValueError when keyring has no email."""
    mock_keyring.return_value = None
    with pytest.raises(ValueError) as exc_info:
        load_config(temp_config)
    assert "Email not found in keyring" in str(exc_info.value)


def test_load_config_missing_file() -> None:
    """Missing config raises FileNotFoundError with helpful message."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_config(Path("/nonexistent/pothole-report.yaml"))
    assert "Config not found" in str(exc_info.value)
    assert "pothole-report.yaml" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_missing_risk_levels(mock_keyring: object, tmp_path: Path) -> None:
    """Config without risk_levels raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_risk_levels.yaml"
    config_path.write_text('report_url: "https://x.org"\n', encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "risk_levels" in str(exc_info.value).lower()


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_risk_levels_not_dict(mock_keyring: object, tmp_path: Path) -> None:
    """Config with risk_levels as non-dict raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_risk_levels.yaml"
    config_path.write_text(
        'report_url: "https://x.org"\nrisk_levels: "not a dict"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a dictionary" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_missing_required_level(mock_keyring: object, tmp_path: Path) -> None:
    """Config missing a required risk level raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "missing_level.yaml"
    config_content = '''report_url: "https://x.org"
risk_levels:
  level_1_emergency:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_2_high_priority:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_3_medium_hazard:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_4_developing_risk:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
'''
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "Missing required risk levels" in str(exc_info.value)
    assert "level_5_monitoring_nuisance" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_extra_levels_allowed(mock_keyring: object, tmp_path: Path) -> None:
    """Config with extra risk levels beyond required ones is valid."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "extra_levels.yaml"
    config_content = '''report_url: "https://x.org"
risk_levels:
  level_1_emergency:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_2_high_priority:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_3_medium_hazard:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_4_developing_risk:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_5_monitoring_nuisance:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_6_custom:
    description: "Custom level"
    visual_indicators: "Custom indicators"
    report_template: "Custom template"
'''
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "level_6_custom" in config["risk_levels"]
    assert config["risk_levels"]["level_6_custom"]["description"] == "Custom level"


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_advice_for_reporters_optional(mock_keyring: object, tmp_path: Path) -> None:
    """Config without advice_for_reporters still loads successfully."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_advice.yaml"
    config_content = '''report_url: "https://x.org"
risk_levels:
  level_1_emergency:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_2_high_priority:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_3_medium_hazard:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_4_developing_risk:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
  level_5_monitoring_nuisance:
    description: "Test"
    visual_indicators: "Test"
    report_template: "Test"
'''
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "advice_for_reporters" in config
    assert config["advice_for_reporters"]["key_phrases"] == []
    assert config["advice_for_reporters"]["pro_tip"] == ""


def test_find_project_root_finds_pyproject_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_project_root finds project root by looking for pyproject.toml."""
    # Create a mock project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("", encoding="utf-8")
    (project_root / "conf").mkdir()
    subdir = project_root / "conf" / "subdir"
    subdir.mkdir(parents=True)
    
    # Change to subdirectory
    monkeypatch.chdir(subdir)
    root = _find_project_root()
    assert root == project_root


def test_config_paths_uses_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_config_paths finds config relative to project root, not cwd."""
    # Create a mock project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("", encoding="utf-8")
    (project_root / "conf").mkdir()
    (project_root / "conf" / "pothole-report.yaml").write_text("test: true", encoding="utf-8")
    subdir = project_root / "conf" / "subdir"
    subdir.mkdir(parents=True)
    
    # Change to subdirectory (simulating running from conf/subdir)
    monkeypatch.chdir(subdir)
    paths = _config_paths(None)
    # Should find conf/pothole-report.yaml relative to project root, not subdir
    assert paths[0] == project_root / "conf" / "pothole-report.yaml"
    assert paths[0].exists()

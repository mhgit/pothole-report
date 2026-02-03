"""Tests for config module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pothole_report.config import _config_paths, _find_project_root, load_config


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_valid(mock_keyring: object, temp_config: Path) -> None:
    """Load valid config returns report_url, email, attributes, report_template, and advice_for_reporters."""
    mock_keyring.return_value = "test@example.com"
    config = load_config(temp_config)
    assert config["report_url"] == "https://example.fillthathole.org"
    assert config["email"] == "test@example.com"
    assert "attributes" in config
    assert "depth" in config["attributes"]
    assert "lt40mm" in config["attributes"]["depth"]
    assert "report_template" in config
    assert "attribute_phrases" in config
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
def test_load_config_missing_attributes(mock_keyring: object, tmp_path: Path) -> None:
    """Config without attributes raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_attributes.yaml"
    config_path.write_text('report_url: "https://x.org"\n', encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "attributes" in str(exc_info.value).lower()


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_attributes_not_dict(mock_keyring: object, tmp_path: Path) -> None:
    """Config with attributes as non-dict raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_attributes.yaml"
    config_path.write_text(
        'report_url: "https://x.org"\nattributes: "not a dict"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a dictionary" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_missing_report_template(mock_keyring: object, tmp_path: Path) -> None:
    """Config without report_template raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_template.yaml"
    config_content = '''report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
'''
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "report_template" in str(exc_info.value).lower()


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_report_template_not_string(mock_keyring: object, tmp_path: Path) -> None:
    """Config with report_template as non-string raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_template.yaml"
    config_content = '''report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: 123
'''
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a string" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_attribute_phrases_optional(mock_keyring: object, tmp_path: Path) -> None:
    """Config without attribute_phrases still loads successfully (defaults to empty dict)."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_phrases.yaml"
    config_content = '''report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: "{severity}: {description}"
'''
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "attribute_phrases" in config
    assert config["attribute_phrases"] == {}


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_advice_for_reporters_optional(mock_keyring: object, tmp_path: Path) -> None:
    """Config without advice_for_reporters still loads successfully."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_advice.yaml"
    config_content = '''report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: "{severity}: {description}"
'''
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "advice_for_reporters" in config
    assert config["advice_for_reporters"]["key_phrases"] == []
    assert config["advice_for_reporters"]["pro_tip"] == ""


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_attribute_value_not_dict(mock_keyring: object, tmp_path: Path) -> None:
    """Config with attribute value as non-dict raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_attribute_value.yaml"
    config_content = '''report_url: "https://x.org"
attributes:
  depth: "not a dict"
report_template: "{severity}: {description}"
'''
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a dictionary" in str(exc_info.value)


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

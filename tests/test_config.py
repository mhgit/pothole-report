"""Tests for config module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pothole_report.config import (
    _check_config_paths,
    _config_paths,
    _find_project_root,
    expand_check_url,
    load_check_config,
    load_config,
)


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
def test_load_config_raises_when_email_missing(
    mock_keyring: object, temp_config: Path
) -> None:
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
def test_load_config_missing_report_template(
    mock_keyring: object, tmp_path: Path
) -> None:
    """Config without report_template raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_template.yaml"
    config_content = """report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
"""
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "report_template" in str(exc_info.value).lower()


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_report_template_not_string(
    mock_keyring: object, tmp_path: Path
) -> None:
    """Config with report_template as non-string raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_template.yaml"
    config_content = """report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: 123
"""
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a string" in str(exc_info.value)


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_attribute_phrases_optional(
    mock_keyring: object, tmp_path: Path
) -> None:
    """Config without attribute_phrases still loads successfully (defaults to empty dict)."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_phrases.yaml"
    config_content = """report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: "{severity}: {description}"
"""
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "attribute_phrases" in config
    assert config["attribute_phrases"] == {}


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_advice_for_reporters_optional(
    mock_keyring: object, tmp_path: Path
) -> None:
    """Config without advice_for_reporters still loads successfully."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "no_advice.yaml"
    config_content = """report_url: "https://x.org"
attributes:
  depth:
    lt40mm: "Less than 40mm"
report_template: "{severity}: {description}"
"""
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)
    assert "advice_for_reporters" in config
    assert config["advice_for_reporters"]["key_phrases"] == []
    assert config["advice_for_reporters"]["pro_tip"] == ""


@patch("pothole_report.config._get_email_from_keyring")
def test_load_config_attribute_value_not_dict(
    mock_keyring: object, tmp_path: Path
) -> None:
    """Config with attribute value as non-dict raises ValueError."""
    mock_keyring.return_value = "test@example.com"
    config_path = tmp_path / "bad_attribute_value.yaml"
    config_content = """report_url: "https://x.org"
attributes:
  depth: "not a dict"
report_template: "{severity}: {description}"
"""
    config_path.write_text(config_content, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        load_config(config_path)
    assert "must be a dictionary" in str(exc_info.value)


def test_find_project_root_finds_pyproject_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_config_paths_uses_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_config_paths finds config relative to project root, not cwd."""
    # Create a mock project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("", encoding="utf-8")
    (project_root / "conf").mkdir()
    (project_root / "conf" / "pothole-report.yaml").write_text(
        "test: true", encoding="utf-8"
    )
    subdir = project_root / "conf" / "subdir"
    subdir.mkdir(parents=True)

    # Change to subdirectory (simulating running from conf/subdir)
    monkeypatch.chdir(subdir)
    paths = _config_paths(None)
    # Should find conf/pothole-report.yaml relative to project root, not subdir
    assert paths[0] == project_root / "conf" / "pothole-report.yaml"
    assert paths[0].exists()


# ---------------------------------------------------------------------------
# Tests for pothole-checking.yaml (load_check_config / expand_check_url)
# ---------------------------------------------------------------------------


def test_check_config_paths_override(tmp_path: Path) -> None:
    """_check_config_paths returns only the override when provided."""
    override = tmp_path / "custom-check.yaml"
    assert _check_config_paths(override) == [override]


def test_check_config_paths_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_check_config_paths returns project and home paths when no override."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(project_root)
    paths = _check_config_paths(None)
    assert len(paths) == 2
    assert paths[0] == project_root / "conf" / "pothole-checking.yaml"
    assert "pothole-checking.yaml" in str(paths[1])


def test_load_check_config_valid(tmp_path: Path) -> None:
    """Valid pothole-checking.yaml returns list of site dicts."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text(
        "check_sites:\n"
        '  - name: "Site A"\n'
        '    url: "https://a.example.com?lat={lat}&lon={lon}"\n'
        '  - name: "Site B"\n'
        '    url: "https://b.example.com"\n',
        encoding="utf-8",
    )
    sites = load_check_config(config_path)
    assert len(sites) == 2
    assert sites[0]["name"] == "Site A"
    assert "{lat}" in sites[0]["url"]
    assert sites[1]["name"] == "Site B"


def test_load_check_config_missing_file_returns_empty(tmp_path: Path) -> None:
    """When file does not exist, return empty list."""
    missing = tmp_path / "nonexistent.yaml"
    assert load_check_config(missing) == []


def test_load_check_config_empty_check_sites(tmp_path: Path) -> None:
    """File exists but check_sites is empty list → return []."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text("check_sites: []\n", encoding="utf-8")
    assert load_check_config(config_path) == []


def test_load_check_config_missing_check_sites_key(tmp_path: Path) -> None:
    """File exists but has no check_sites key → return []."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text("some_other_key: true\n", encoding="utf-8")
    assert load_check_config(config_path) == []


def test_load_check_config_invalid_yaml(tmp_path: Path) -> None:
    """Broken YAML raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text("check_sites:\n  - name: [unbalanced", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_check_config(config_path)


def test_load_check_config_check_sites_not_list(tmp_path: Path) -> None:
    """check_sites is not a list → raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text('check_sites: "not a list"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="must be a list"):
        load_check_config(config_path)


def test_load_check_config_entry_missing_name(tmp_path: Path) -> None:
    """Entry without name → raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text(
        'check_sites:\n  - url: "https://example.com"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing a valid 'name'"):
        load_check_config(config_path)


def test_load_check_config_entry_missing_url(tmp_path: Path) -> None:
    """Entry without url → raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text(
        'check_sites:\n  - name: "Site A"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing a valid 'url'"):
        load_check_config(config_path)


def test_load_check_config_entry_not_dict(tmp_path: Path) -> None:
    """Entry that is a plain string → raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text(
        'check_sites:\n  - "just a string"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be a mapping"):
        load_check_config(config_path)


def test_load_check_config_file_not_mapping(tmp_path: Path) -> None:
    """File whose root is not a mapping → raises ValueError."""
    config_path = tmp_path / "pothole-checking.yaml"
    config_path.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_check_config(config_path)


def test_expand_check_url_basic() -> None:
    """Placeholders {lat} and {lon} are replaced."""
    url = expand_check_url("https://x.com?lat={lat}&lon={lon}", 51.123456, -0.654321)
    assert "51.123456" in url
    assert "-0.654321" in url
    assert "{lat}" not in url
    assert "{lon}" not in url


def test_expand_check_url_aliases() -> None:
    """Aliases {latitude} and {longitude} are also replaced."""
    url = expand_check_url(
        "https://x.com?latitude={latitude}&longitude={longitude}",
        51.5,
        -0.1,
    )
    assert "51.5" in url
    assert "-0.1" in url
    assert "{latitude}" not in url
    assert "{longitude}" not in url


def test_expand_check_url_rounds_to_six_decimals() -> None:
    """Coordinates are rounded to 6 decimal places."""
    url = expand_check_url("https://x.com?lat={lat}", 51.1234567890, 0.0)
    assert "51.123457" in url


def test_expand_check_url_no_placeholders() -> None:
    """Plain URL with no placeholders is returned unchanged."""
    original = "https://example.com/reports"
    assert expand_check_url(original, 51.0, -0.1) == original

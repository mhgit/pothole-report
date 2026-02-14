"""Load configuration from YAML file and keyring."""

from pathlib import Path

import keyring
import yaml

SERVICE_NAME = "pothole-report"


def _find_project_root() -> Path:
    """Find project root by looking for pyproject.toml, walking up from cwd."""
    cwd = Path.cwd()
    current = cwd
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # If pyproject.toml not found, return cwd as fallback
    return cwd


def _config_paths(override: Path | None) -> list[Path]:
    """Return search order for config file."""
    if override is not None:
        return [override]
    project_root = _find_project_root()
    return [
        project_root / "conf" / "pothole-report.yaml",
        Path.home() / ".config" / "pothole-report" / "pothole-report.yaml",
    ]


def _get_email_from_keyring(account: str) -> str | None:
    """Fetch email from keyring. Returns None if not set."""
    value = keyring.get_password(SERVICE_NAME, account)
    return value.strip() if value else None


def _validate_attributes(attributes: dict) -> None:
    """Validate attributes structure. Raises ValueError if invalid."""
    if not isinstance(attributes, dict):
        raise ValueError(
            f"attributes must be a dictionary. Got {type(attributes).__name__}."
        )

    # Each attribute category should be a dict of value -> description
    for attr_name, attr_values in attributes.items():
        if not isinstance(attr_values, dict):
            raise ValueError(
                f"Attribute '{attr_name}' must be a dictionary mapping values to descriptions."
            )
        for value_key, description in attr_values.items():
            if not isinstance(description, str):
                raise ValueError(
                    f"Attribute '{attr_name}' value '{value_key}' must have a string description."
                )


def load_config(config_path: Path | None = None) -> dict:
    """Load config from YAML and keyring. Raises FileNotFoundError or ValueError if invalid.

    Args:
        config_path: Optional path to config file. If None, searches default locations.
    """
    for path in _config_paths(config_path):
        if path.exists():
            with path.open() as f:
                data = yaml.safe_load(f) or {}
            report_url = str(data.get("report_url", "https://www.fillthathole.org.uk"))
            keyring_account = str(data.get("keyring_account", "email"))
            email = _get_email_from_keyring(keyring_account)
            if not email:
                raise ValueError(
                    f"Email not found in keyring. Run:\n"
                    f"  report-pothole setup\n"
                    f"Or store manually:\n"
                    f'  keyring set {SERVICE_NAME} {keyring_account} "your@email.com"'
                )

            # Load and validate attributes
            raw_attributes = data.get("attributes")
            if raw_attributes is None:
                raise ValueError(
                    "Config must contain 'attributes' section defining available attribute values."
                )
            _validate_attributes(raw_attributes)

            # Normalize attributes: ensure all keys and values are strings
            attributes = {}
            for attr_name, attr_values in raw_attributes.items():
                if not isinstance(attr_values, dict):
                    continue
                attributes[str(attr_name)] = {
                    str(k): str(v) for k, v in attr_values.items()
                }

            # Load report_template (required)
            report_template = data.get("report_template")
            if report_template is None:
                raise ValueError(
                    "Config must contain 'report_template' section with a parameterized template."
                )
            if not isinstance(report_template, str):
                raise ValueError(
                    f"report_template must be a string. Got {type(report_template).__name__}."
                )

            # Load attribute_phrases (optional, defaults to empty dict)
            raw_phrases = data.get("attribute_phrases", {})
            if not isinstance(raw_phrases, dict):
                raw_phrases = {}
            attribute_phrases = {}
            for phrase_key, phrase_values in raw_phrases.items():
                if isinstance(phrase_values, dict):
                    attribute_phrases[str(phrase_key)] = {
                        str(k): str(v) for k, v in phrase_values.items()
                    }
                else:
                    attribute_phrases[str(phrase_key)] = str(phrase_values)

            # Load advice_for_reporters (optional)
            raw_advice = data.get("advice_for_reporters", {})
            if not isinstance(raw_advice, dict):
                raw_advice = {}
            advice_for_reporters = {
                "key_phrases": (
                    [str(item) for item in raw_advice.get("key_phrases", [])]
                    if isinstance(raw_advice.get("key_phrases"), list)
                    else []
                ),
                "pro_tip": str(raw_advice.get("pro_tip", "")),
            }

            result = {
                "report_url": report_url,
                "email": email,
                "attributes": attributes,
                "report_template": report_template,
                "attribute_phrases": attribute_phrases,
                "advice_for_reporters": advice_for_reporters,
                "_loaded_from": str(path),
                "_keyring_service": SERVICE_NAME,
                "_keyring_account": keyring_account,
            }
            return result
    paths = _config_paths(config_path)
    path_list = "\n".join(f"  - {p}" for p in paths)
    raise FileNotFoundError(
        f"Config not found. Create one of:\n{path_list}\n"
        f"With content:\n"
        '  report_url: "https://www.fillthathole.org.uk"\n'
        '  keyring_account: "email"  # optional, default "email"\n'
        '  attributes:\n    depth:\n      lt40mm: "Less than 40mm"\n  report_template: "{severity}: {description}"\n  attribute_phrases:\n    severity:\n      gt50mm_sharp: "EMERGENCY"'
    )


# ---------------------------------------------------------------------------
# Check-config (pothole-checking.yaml) – separate file for existing reports
# ---------------------------------------------------------------------------


def _check_config_paths(override: Path | None) -> list[Path]:
    """Return search order for pothole-checking.yaml."""
    if override is not None:
        return [override]
    project_root = _find_project_root()
    return [
        project_root / "conf" / "pothole-checking.yaml",
        Path.home() / ".config" / "pothole-report" / "pothole-checking.yaml",
    ]


def load_check_config(config_path: Path | None = None) -> list[dict]:
    """Load check sites from pothole-checking.yaml.

    Returns:
        List of dicts with ``name`` and ``url`` keys, or ``[]`` when the
        file is missing or ``check_sites`` is absent / empty.

    Raises:
        ValueError: When the file exists but contains invalid YAML or an
            invalid ``check_sites`` structure.
    """
    for path in _check_config_paths(config_path):
        if path.exists():
            with path.open() as f:
                try:
                    data = yaml.safe_load(f)
                except yaml.YAMLError as exc:
                    raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

            if not isinstance(data, dict):
                raise ValueError(
                    f"Invalid pothole-checking.yaml ({path}): "
                    "file must contain a YAML mapping."
                )

            raw_sites = data.get("check_sites")
            if raw_sites is None or raw_sites == []:
                return []

            if not isinstance(raw_sites, list):
                raise ValueError(
                    f"Invalid pothole-checking.yaml ({path}): "
                    "check_sites must be a list."
                )

            sites: list[dict] = []
            for idx, entry in enumerate(raw_sites):
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"Invalid pothole-checking.yaml ({path}): "
                        f"check_sites[{idx}] must be a mapping with 'name' and 'url'."
                    )
                name = entry.get("name")
                url = entry.get("url")
                if not isinstance(name, str) or not name.strip():
                    raise ValueError(
                        f"Invalid pothole-checking.yaml ({path}): "
                        f"check_sites[{idx}] is missing a valid 'name' string."
                    )
                if not isinstance(url, str) or not url.strip():
                    raise ValueError(
                        f"Invalid pothole-checking.yaml ({path}): "
                        f"check_sites[{idx}] is missing a valid 'url' string."
                    )
                sites.append({"name": name.strip(), "url": url.strip()})
            return sites

    # No file found at any search path
    return []


def expand_check_url(template: str, lat: float, lon: float) -> str:
    """Replace ``{lat}``, ``{lon}`` (and aliases) in a URL template.

    Coordinates are rounded to 6 decimal places.
    """
    lat_str = str(round(lat, 6))
    lon_str = str(round(lon, 6))
    return (
        template.replace("{lat}", lat_str)
        .replace("{lon}", lon_str)
        .replace("{latitude}", lat_str)
        .replace("{longitude}", lon_str)
    )

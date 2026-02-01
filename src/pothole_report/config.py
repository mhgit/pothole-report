"""Load configuration from YAML file and keyring."""

from pathlib import Path

import keyring
import yaml

SERVICE_NAME = "pothole-report"

# Required minimum risk levels that must be present in config
REQUIRED_RISK_LEVELS = {
    "level_1_emergency",
    "level_2_high_priority",
    "level_3_medium_hazard",
    "level_4_developing_risk",
    "level_5_monitoring_nuisance",
}


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


def _validate_risk_levels(risk_levels: dict) -> None:
    """Validate that all required risk levels are present. Raises ValueError if any are missing."""
    if not isinstance(risk_levels, dict):
        raise ValueError(
            f"risk_levels must be a dictionary. Got {type(risk_levels).__name__}."
        )
    
    present_keys = set(str(k) for k in risk_levels.keys())
    missing = REQUIRED_RISK_LEVELS - present_keys
    
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"Missing required risk levels: {missing_list}. "
            f"Config must contain all five required levels: {', '.join(sorted(REQUIRED_RISK_LEVELS))}"
        )
    
    # Validate each required level has the required fields
    for level_key in REQUIRED_RISK_LEVELS:
        level_data = risk_levels.get(level_key)
        if not isinstance(level_data, dict):
            raise ValueError(
                f"Risk level '{level_key}' must be a dictionary with description, visual_indicators, and report_template."
            )
        required_fields = {"description", "visual_indicators", "report_template"}
        level_fields = set(level_data.keys())
        missing_fields = required_fields - level_fields
        if missing_fields:
            raise ValueError(
                f"Risk level '{level_key}' is missing required fields: {', '.join(sorted(missing_fields))}"
            )


def load_config(config_path: Path | None = None, require_email: bool = True) -> dict:
    """Load config from YAML and keyring. Raises FileNotFoundError or ValueError if invalid.
    
    Args:
        config_path: Optional path to config file. If None, searches default locations.
        require_email: If True, raises ValueError when email is not in keyring. If False,
                      email will be None when not found (useful for listing risk levels).
    """
    for path in _config_paths(config_path):
        if path.exists():
            with path.open() as f:
                data = yaml.safe_load(f) or {}
            report_url = str(data.get("report_url", "https://www.fillthathole.org.uk"))
            keyring_account = str(data.get("keyring_account", "email"))
            email = _get_email_from_keyring(keyring_account)
            if require_email and not email:
                raise ValueError(
                    f"Email not found in keyring. Run:\n"
                    f"  report-pothole setup\n"
                    f"Or store manually:\n"
                    f'  keyring set {SERVICE_NAME} {keyring_account} "your@email.com"'
                )
            
            # Load and validate risk_levels
            raw_risk_levels = data.get("risk_levels")
            if raw_risk_levels is None:
                raise ValueError(
                    "Config must contain 'risk_levels' section. "
                    f"Required levels: {', '.join(sorted(REQUIRED_RISK_LEVELS))}"
                )
            _validate_risk_levels(raw_risk_levels)
            
            # Normalize risk_levels keys to strings and validate structure
            # After validation, all required levels are guaranteed to be dicts,
            # but we still check to handle any extra levels that might not be dicts
            risk_levels = {}
            for k, v in raw_risk_levels.items():
                if not isinstance(v, dict):
                    continue
                risk_levels[str(k)] = {
                    "description": str(v.get("description", "")),
                    "visual_indicators": str(v.get("visual_indicators", "")),
                    "report_template": str(v.get("report_template", "")),
                }
            
            # Verify all required levels are present after normalization
            # (defensive check in case normalization somehow skipped a required level)
            present_keys = set(risk_levels.keys())
            missing = REQUIRED_RISK_LEVELS - present_keys
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(
                    f"Required risk levels missing after normalization: {missing_list}. "
                    f"This should not happen - please report this bug."
                )
            
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
                "risk_levels": risk_levels,
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
        '  risk_levels:\n    level_1_emergency:\n      description: "..."\n      visual_indicators: "..."\n      report_template: "..."'
    )

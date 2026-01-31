"""Load configuration from YAML file and keyring."""

from pathlib import Path

import keyring
import yaml

SERVICE_NAME = "pothole-batcher"


def _config_paths(override: Path | None) -> list[Path]:
    """Return search order for config file."""
    if override is not None:
        return [override]
    cwd = Path.cwd()
    return [
        cwd / "conf" / "pothole-batcher.yaml",
        Path.home() / ".config" / "pothole-batcher" / "pothole-batcher.yaml",
    ]


def _get_email_from_keyring(account: str) -> str | None:
    """Fetch email from keyring. Returns None if not set."""
    value = keyring.get_password(SERVICE_NAME, account)
    return value.strip() if value else None


DEFAULT_TEMPLATES = {
    "high-risk": (
        "This defect is located in the primary line of travel for cyclists. "
        "Due to its depth, it presents a significant risk of ejection. "
        "It is currently forcing cyclists to swerve into the path of motor traffic to avoid it. "
        "Please treat as an urgent safety hazard."
    ),
    "hidden": (
        "This pothole is often obscured by shadows or standing water, "
        "making it invisible to cyclists until impact. "
        "As it sits directly where a rider is expected to be, "
        "it represents a high risk of a serious incident."
    ),
}


def load_config(config_path: Path | None = None) -> dict:
    """Load config from YAML and keyring. Raises FileNotFoundError or ValueError if invalid."""
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
            raw_templates = data.get("templates") or {}
            templates = {
                str(k): str(v)
                for k, v in raw_templates.items()
                if isinstance(v, str)
            }
            if not templates:
                templates = dict(DEFAULT_TEMPLATES)
            return {"report_url": report_url, "email": email, "templates": templates}
    paths = _config_paths(config_path)
    path_list = "\n".join(f"  - {p}" for p in paths)
    raise FileNotFoundError(
        f"Config not found. Create one of:\n{path_list}\n"
        f"With content:\n"
        '  report_url: "https://www.fillthathole.org.uk"\n'
        '  keyring_account: "email"  # optional, default "email"'
    )

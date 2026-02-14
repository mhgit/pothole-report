"""Tests for CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pothole_report.cli import main


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_requires_folder(_mock_keyring: object, temp_config: Path) -> None:
    """CLI exits with error when -f/--folder is missing."""
    with patch.object(sys, "argv", ["report-pothole", "-c", str(temp_config)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_cli_config_not_found(tmp_path: Path) -> None:
    """CLI exits when config file is missing."""
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(tmp_path),
            "-c",
            str(tmp_path / "nonexistent.yaml"),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_not_a_directory(
    _mock_keyring: object, tmp_path: Path, temp_config: Path
) -> None:
    """CLI exits when folder is not a directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(file_path),
            "-c",
            str(temp_config),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_empty_folder(
    _mock_keyring: object, tmp_path: Path, temp_config: Path
) -> None:
    """CLI prints message and returns when folder has no images."""
    mock_console = MagicMock()
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(tmp_path),
            "-c",
            str(temp_config),
            "--depth",
            "lt40mm",
        ],
    ):
        with patch("pothole_report.cli.Console", return_value=mock_console):
            main()
    mock_console.print.assert_called()
    calls = [str(c) for c in mock_console.print.call_args_list]
    assert any("No JPG/PNG" in str(c) for c in calls)


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_skips_unreadable_images(
    _mock_keyring: object,
    tmp_path: Path,
    temp_config: Path,
) -> None:
    """CLI skips corrupted/unreadable images without crashing."""
    bad_img = tmp_path / "corrupt.jpg"
    bad_img.write_text("not an image")
    mock_console = MagicMock()
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(tmp_path),
            "-c",
            str(temp_config),
            "--depth",
            "lt40mm",
            "-v",
        ],
    ):
        with patch("pothole_report.cli.Console", return_value=mock_console):
            main()
    out = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "unreadable" in out or "Skipped" in out


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_processes_photos(
    _mock_keyring: object,
    tmp_path: Path,
    temp_config: Path,
    temp_photo_dir: Path,
) -> None:
    """CLI runs pipeline; with no GPS in images, skips and reports."""
    mock_console = MagicMock()
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(temp_photo_dir),
            "-c",
            str(temp_config),
            "--depth",
            "lt40mm",
        ],
    ):
        with patch("pothole_report.cli.Console", return_value=mock_console):
            main()
    mock_console.print.assert_called()
    calls = [str(c) for c in mock_console.print.call_args_list]
    assert any("Skipped" in str(c) or "No reports" in str(c) for c in calls)


@patch("pothole_report.config._get_email_from_keyring", return_value=None)
def test_cli_exits_when_email_not_in_keyring(
    _mock_keyring: object,
    tmp_path: Path,
    temp_config: Path,
) -> None:
    """CLI exits with error when email is not stored in keyring."""
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(tmp_path),
            "-c",
            str(temp_config),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_invalid_attribute_value(
    _mock_keyring: object, temp_config: Path, temp_photo_dir: Path
) -> None:
    """CLI exits when attribute value does not match config."""
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(temp_photo_dir),
            "-c",
            str(temp_config),
            "--depth",
            "invalid",
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_no_attributes_provided(
    _mock_keyring: object, temp_config: Path, temp_photo_dir: Path
) -> None:
    """CLI exits when no attributes are provided (neither flags nor interactive)."""
    with patch.object(
        sys,
        "argv",
        ["report-pothole", "-f", str(temp_photo_dir), "-c", str(temp_config)],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_multi_select_location(
    _mock_keyring: object, temp_config: Path, temp_photo_dir: Path
) -> None:
    """CLI accepts comma-separated values for location (multi-select)."""
    mock_console = MagicMock()
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(temp_photo_dir),
            "-c",
            str(temp_config),
            "--location",
            "primary_cycle_line,general",
            "--depth",
            "lt40mm",
        ],
    ):
        with patch("pothole_report.cli.Console", return_value=mock_console):
            # Should not raise an error
            try:
                main()
            except SystemExit:
                pass  # Expected if no GPS/images, but validation should pass
    # Check that validation passed (no error about invalid location values)
    calls = [str(c) for c in mock_console.print.call_args_list]
    assert not any(
        "Invalid value" in str(c) and "location" in str(c).lower() for c in calls
    )


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_multi_select_visibility(
    _mock_keyring: object, temp_config: Path, temp_photo_dir: Path
) -> None:
    """CLI accepts comma-separated values for visibility (multi-select)."""
    mock_console = MagicMock()
    with patch.object(
        sys,
        "argv",
        [
            "report-pothole",
            "-f",
            str(temp_photo_dir),
            "-c",
            str(temp_config),
            "--visibility",
            "obscured_water,obscured_shadows",
            "--depth",
            "lt40mm",
        ],
    ):
        with patch("pothole_report.cli.Console", return_value=mock_console):
            # Should not raise an error
            try:
                main()
            except SystemExit:
                pass  # Expected if no GPS/images, but validation should pass
    # Check that validation passed (no error about invalid visibility values)
    calls = [str(c) for c in mock_console.print.call_args_list]
    assert not any(
        "Invalid value" in str(c) and "visibility" in str(c).lower() for c in calls
    )


@patch("pothole_report.cli.keyring.set_password")
def test_cli_setup_stores_email(mock_set_password: object) -> None:
    """Setup subcommand stores email in keyring."""
    with patch.object(sys, "argv", ["report-pothole", "setup"]):
        with patch("pothole_report.cli.Console") as mock_console_cls:
            mock_console = MagicMock()
            mock_console.input.return_value = "user@example.com"
            mock_console_cls.return_value = mock_console
            main()
    mock_set_password.assert_called_once()
    call_args = mock_set_password.call_args[0]
    assert call_args[0] == "pothole-report"
    assert call_args[1] == "email"
    assert call_args[2] == "user@example.com"


@patch("pothole_report.cli.keyring.delete_password")
def test_cli_remove_keyring_calls_delete(mock_delete_password: object) -> None:
    """remove-keyring subcommand deletes the current keyring entry."""
    with patch.object(sys, "argv", ["report-pothole", "remove-keyring"]):
        with patch("pothole_report.cli.Console") as mock_console_cls:
            mock_console_cls.return_value = MagicMock()
            main()
    mock_delete_password.assert_called_once_with("pothole-report", "email")


@patch("pothole_report.cli.keyring.delete_password")
def test_cli_remove_keyring_handles_missing(mock_delete_password: object) -> None:
    """remove-keyring does not crash when the entry is already gone."""
    import keyring.errors

    mock_delete_password.side_effect = keyring.errors.PasswordDeleteError()
    with patch.object(sys, "argv", ["report-pothole", "remove-keyring"]):
        with patch("pothole_report.cli.Console") as mock_console_cls:
            mock_console_cls.return_value = MagicMock()
            main()  # should not raise

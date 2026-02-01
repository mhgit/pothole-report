"""Tests for CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pothole_report.cli import main


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_requires_folder(_mock_keyring: object, temp_config: Path) -> None:
    """CLI exits with error when -f/--folder is missing (and not --list-risk-levels)."""
    with patch.object(sys, "argv", ["report-pothole", "-c", str(temp_config)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_cli_config_not_found(tmp_path: Path) -> None:
    """CLI exits when config file is missing."""
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(tmp_path),
        "-c", str(tmp_path / "nonexistent.yaml"),
    ]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_not_a_directory(_mock_keyring: object, tmp_path: Path, temp_config: Path) -> None:
    """CLI exits when folder is not a directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(file_path),
        "-c", str(temp_config),
    ]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_empty_folder(_mock_keyring: object, tmp_path: Path, temp_config: Path) -> None:
    """CLI prints message and returns when folder has no images."""
    mock_console = MagicMock()
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(tmp_path),
        "-c", str(temp_config),
    ]):
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
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(tmp_path),
        "-c", str(temp_config),
        "-v",
    ]):
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
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(temp_photo_dir),
        "-c", str(temp_config),
    ]):
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
    with patch.object(sys, "argv", [
        "report-pothole",
        "-f", str(tmp_path),
        "-c", str(temp_config),
    ]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_unknown_risk_level(
    _mock_keyring: object, temp_config: Path, temp_photo_dir: Path
) -> None:
    """CLI exits when --risk-level does not match a risk level."""
    # Create an image with GPS (mocked) - we need extract to succeed to reach the risk-level check
    from unittest.mock import patch as mock_patch

    with mock_patch("pothole_report.cli.extract_all") as mock_extract:
        from pothole_report.extract import ExtractedData

        mock_extract.return_value = ExtractedData(
            path=temp_photo_dir / "photo.jpg",
            lat=51.5,
            lon=-0.1,
            datetime_taken="2025-01-01 12:00",
        )
        with mock_patch("pothole_report.cli.reverse_geocode") as mock_geocode:
            from pothole_report.geocode import GeocodedResult

            mock_geocode.return_value = GeocodedResult(
                postcode="XX1 1XX", address="Test St"
            )
            with mock_patch.object(
                sys, "argv",
                ["report-pothole", "-f", str(temp_photo_dir), "-c", str(temp_config), "--risk-level", "nosuch"],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
            assert exc_info.value.code == 1


@patch("pothole_report.config._get_email_from_keyring", return_value="test@example.com")
def test_cli_list_risk_levels(_mock_keyring: object, temp_config: Path) -> None:
    """--list-risk-levels displays available risk levels with description and visual_indicators."""
    from io import StringIO

    from rich.console import Console

    console = Console(file=StringIO(), force_terminal=False)
    with patch.object(sys, "argv", ["report-pothole", "--list-risk-levels", "-c", str(temp_config)]):
        with patch("pothole_report.cli.Console", return_value=console):
            main()
    out = console.file.getvalue()
    # Should include level keys
    assert "level_1_emergency" in out
    assert "level_3_medium_hazard" in out
    # Should include descriptions
    assert "Description:" in out
    assert "Visual Indicators:" in out
    # Should NOT include report_template
    assert "report_template" not in out
    assert "Emergency report template" not in out


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

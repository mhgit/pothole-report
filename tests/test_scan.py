"""Tests for scan module."""

from pathlib import Path

import pytest

from pothole_report.scan import scan_folder


def test_scan_folder_finds_jpg_png(temp_photo_dir: Path) -> None:
    """Scan finds JPG and PNG files."""
    paths = scan_folder(temp_photo_dir)
    assert len(paths) == 1
    assert paths[0].name == "photo.jpg"


def test_scan_folder_ignores_other_extensions(tmp_path: Path) -> None:
    """Scan ignores non-image files."""
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.txt").touch()
    (tmp_path / "c.png").touch()
    (tmp_path / "d.pdf").touch()
    paths = scan_folder(tmp_path)
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert names == {"a.jpg", "c.png"}


def test_scan_folder_sorted_by_name(tmp_path: Path) -> None:
    """Scan returns paths sorted by filename."""
    (tmp_path / "z.jpg").touch()
    (tmp_path / "a.jpeg").touch()
    (tmp_path / "m.png").touch()
    paths = scan_folder(tmp_path)
    assert [p.name for p in paths] == ["a.jpeg", "m.png", "z.jpg"]


def test_scan_folder_not_a_directory(tmp_path: Path) -> None:
    """Scan raises NotADirectoryError for file path."""
    file_path = tmp_path / "file.txt"
    file_path.touch()
    with pytest.raises(NotADirectoryError) as exc_info:
        scan_folder(file_path)
    assert "Not a directory" in str(exc_info.value)


def test_scan_folder_empty(tmp_path: Path) -> None:
    """Scan returns empty list for empty folder."""
    paths = scan_folder(tmp_path)
    assert paths == []

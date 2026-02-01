"""Discover JPG/PNG image files in a folder."""

from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".png"}
EXTENSIONS_LOWER = {e.lower() for e in EXTENSIONS}


def scan_folder(folder: Path) -> list[Path]:
    """Return sorted list of JPG/PNG file paths in folder (non-recursive)."""
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")
    paths: list[Path] = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in EXTENSIONS_LOWER:
            paths.append(p)
    return sorted(paths, key=lambda x: x.name)

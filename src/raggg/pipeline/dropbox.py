from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from raggg.loaders.user_file_loader import SUPPORTED_USER_EXTENSIONS


@dataclass(frozen=True)
class DropboxImportReport:
    imported: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Too many files share the same name near {path}")


def _supported_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() in SUPPORTED_USER_EXTENSIONS else []
    if not source.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_USER_EXTENSIONS:
            files.append(path)
    return files


def copy_to_dropbox(paths: list[Path], dropbox_root: Path) -> DropboxImportReport:
    dropbox_root.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []
    skipped: list[Path] = []
    for source in paths:
        files = _supported_files(source)
        if not files:
            skipped.append(source)
            continue
        for file_path in files:
            try:
                if source.is_dir():
                    relative = file_path.relative_to(source)
                    target = dropbox_root / source.name / relative
                else:
                    target = dropbox_root / file_path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target = _unique_path(target)
                shutil.copy2(file_path, target)
                imported.append(target)
            except OSError:
                skipped.append(file_path)
    return DropboxImportReport(imported=imported, skipped=skipped)

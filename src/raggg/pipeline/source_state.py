from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from raggg.config import Settings


@dataclass(frozen=True)
class SourceSnapshot:
    digest: str
    file_count: int


def source_state_path(settings: Settings) -> Path:
    return settings.data_dir / "source_state.json"


def compute_source_snapshot(settings: Settings) -> SourceSnapshot:
    records: list[str] = []
    for root, patterns in _source_roots(settings):
        if not root.exists():
            continue
        for pattern in patterns:
            for path in sorted(root.rglob(pattern)):
                if not path.is_file():
                    continue
                if any(part.startswith(".") for part in path.relative_to(root).parts):
                    continue
                stat = path.stat()
                rel = path.relative_to(root).as_posix()
                records.append(f"{root.resolve()}|{rel}|{stat.st_size}|{stat.st_mtime_ns}")
    digest = hashlib.sha256("\n".join(sorted(records)).encode("utf-8")).hexdigest()
    return SourceSnapshot(digest=digest, file_count=len(records))


def write_source_state(settings: Settings) -> SourceSnapshot:
    snapshot = compute_source_snapshot(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    source_state_path(settings).write_text(
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snapshot


def load_source_state(settings: Settings) -> SourceSnapshot | None:
    path = source_state_path(settings)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SourceSnapshot(digest=str(data["digest"]), file_count=int(data["file_count"]))


def has_source_changes(settings: Settings) -> bool:
    saved = load_source_state(settings)
    if saved is None:
        return True
    return compute_source_snapshot(settings) != saved


def _source_roots(settings: Settings) -> list[tuple[Path, tuple[str, ...]]]:
    roots: list[tuple[Path, tuple[str, ...]]] = [
        (settings.waveda_help_root, ("*.html", "*.htm")),
        (settings.obsidian_vault_root, ("*.md",)),
    ]
    roots.extend((root, ("*.md",)) for root in settings.extra_markdown_roots)
    return roots

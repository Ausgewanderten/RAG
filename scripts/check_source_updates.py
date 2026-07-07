from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from raggg.config import load_settings
from raggg.pipeline.source_state import compute_source_snapshot, has_source_changes, load_source_state


def main() -> int:
    settings = load_settings()
    current = compute_source_snapshot(settings)
    saved = load_source_state(settings)
    changed = has_source_changes(settings)
    print(f"changed={str(changed).lower()}")
    print(f"current_files={current.file_count}")
    if saved is None:
        print("saved_files=missing")
    else:
        print(f"saved_files={saved.file_count}")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def load_env_files(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def load_default_env() -> None:
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parent
    load_env_files(
        [
            repo_root / ".env",
            base_dir / ".env",
            base_dir / ".env.local",
        ]
    )

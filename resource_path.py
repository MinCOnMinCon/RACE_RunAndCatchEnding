from __future__ import annotations

import sys
import shutil
import tempfile
from pathlib import Path


class ResourcePath:
    @staticmethod
    def get(relative_path: str) -> Path:
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base_path / relative_path

    @staticmethod
    def get_mediapipe_model_path(relative_path: str) -> str:
        source_path = ResourcePath.get(relative_path)
        source_text = str(source_path)
        if source_text.isascii():
            return source_text

        cache_dir = Path(tempfile.gettempdir()) / "RACE_RunAndCatchEnding"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cached_path = cache_dir / source_path.name
        if (
            not cached_path.exists()
            or cached_path.stat().st_size != source_path.stat().st_size
            or cached_path.stat().st_mtime < source_path.stat().st_mtime
        ):
            shutil.copy2(source_path, cached_path)

        return str(cached_path)

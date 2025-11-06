# storybook/repositories/story_repo_file.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class StoryFileRepository:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[2] / "data" / "stories"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, payload: Dict[str, Any]) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = self.base_dir / f"story_{ts}.json"
        with fn.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(fn)

    def list_files(self) -> list[str]:
        return [str(p) for p in sorted(self.base_dir.glob("story_*.json"))]

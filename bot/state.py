"""Персистентное состояние планировщика (интервал, running, статистика)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BotState:
    running: bool = True
    interval_hours: float = 2.0
    last_sync: str | None = None
    last_sync_count: int = 0
    last_error: str | None = None

    @classmethod
    def load(cls, path: Path, default_interval: float) -> BotState:
        if not path.exists():
            return cls(interval_hours=default_interval)
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                running=bool(raw.get("running", True)),
                interval_hours=float(raw.get("interval_hours", default_interval)),
                last_sync=raw.get("last_sync"),
                last_sync_count=int(raw.get("last_sync_count", 0)),
                last_error=raw.get("last_error"),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls(interval_hours=default_interval)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def mark_sync_ok(self, count: int) -> None:
        self.last_sync = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.last_sync_count = count
        self.last_error = None

    def mark_sync_error(self, error: str) -> None:
        self.last_error = error[:500]

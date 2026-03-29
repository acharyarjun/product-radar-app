"""Lightweight JSON memory for deduplication across runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryState:
    seen_source_urls: set[str] = field(default_factory=set)
    last_run: str | None = None
    total_runs: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryState:
        seen = d.get("seen_source_urls") or d.get("products") or []
        if isinstance(seen, list):
            urls = {str(x) for x in seen}
        else:
            urls = set(seen) if seen else set()
        return cls(
            seen_source_urls=urls,
            last_run=d.get("last_run"),
            total_runs=int(d.get("total_runs") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "seen_source_urls": sorted(self.seen_source_urls),
            "last_run": self.last_run,
            "total_runs": self.total_runs,
        }


def load_memory(path: Path) -> MemoryState:
    if not path.is_file():
        return MemoryState()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return MemoryState(seen_source_urls=set(data))
    return MemoryState.from_dict(data)


def save_memory(path: Path, state: MemoryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)


def stable_key(source_url: str) -> str:
    return source_url.split("?")[0].strip().lower()


def mark_run(state: MemoryState) -> None:
    state.last_run = datetime.now(timezone.utc).isoformat()
    state.total_runs += 1
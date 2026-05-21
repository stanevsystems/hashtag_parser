"""Слияние записей и запись ideas.json."""

from __future__ import annotations

import json
from pathlib import Path

from scanner import IdeaRecord


def records_to_json_list(records: list[IdeaRecord]) -> list[dict[str, str]]:
    return [
        {"author": r.author, "date": r.date, "text": r.text}
        for r in records
    ]


def load_existing_ideas(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    result: list[dict[str, str]] = []
    for item in data:
        if isinstance(item, dict) and "text" in item:
            result.append(
                {
                    "author": str(item.get("author", "Unknown")),
                    "date": str(item.get("date", "")),
                    "text": str(item.get("text", "")),
                }
            )
    return result


def _idea_key(item: dict[str, str]) -> tuple[str, str, str]:
    return (
        item.get("author", ""),
        item.get("date", ""),
        item.get("text", ""),
    )


def merge_ideas(
    existing: list[dict[str, str]],
    new_records: list[IdeaRecord],
) -> list[dict[str, str]]:
    seen = {_idea_key(item) for item in existing}
    merged = list(existing)
    for record in new_records:
        item = {
            "author": record.author,
            "date": record.date,
            "text": record.text,
        }
        key = _idea_key(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    merged.sort(key=lambda x: x.get("date", ""))
    return merged


def write_ideas(path: Path, ideas: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ideas, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

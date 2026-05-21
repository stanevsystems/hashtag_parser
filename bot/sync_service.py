"""Один цикл: сканирование → merge → git push."""

from __future__ import annotations

import logging

from config import Settings
from git_sync import GitSyncError, push_ideas
from scanner import scan_all
from state import BotState
from telethon import TelegramClient

logger = logging.getLogger(__name__)


async def run_sync_cycle(
    client: TelegramClient,
    settings: Settings,
    state: BotState,
) -> tuple[int, int]:
    """
    Сканирует все хэштеги и чаты, пушит в git.
    Возвращает (число найденных записей, число добавленных в репозиторий).
    """
    all_records = []
    for target in settings.export_targets:
        found = await scan_all(client, target.chat_ids, target.hashtag)
        logger.info(
            "Найдено %s сообщений с %s",
            len(found),
            target.hashtag,
        )
        all_records.extend(found)

    # Дедуп между хэштегами (если пересекаются чаты)
    seen: set[tuple[str, str, str]] = set()
    unique = []
    for r in all_records:
        k = r.key()
        if k not in seen:
            seen.add(k)
            unique.append(r)

    try:
        added = push_ideas(settings, unique)
    except GitSyncError:
        raise

    state.mark_sync_ok(len(unique))
    return len(unique), added

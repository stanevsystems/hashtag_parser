"""Сканирование истории чата по хэштегам."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from telethon import TelegramClient
from telethon.tl.custom.message import Message


@dataclass(frozen=True)
class IdeaRecord:
    author: str
    date: str
    text: str

    def key(self) -> tuple[str, str, str]:
        return (self.author, self.date, self.text)


def _format_date(message: Message) -> str:
    dt = message.date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )


async def _author_name(client: TelegramClient, message: Message) -> str:
    if not message.sender_id:
        return "Unknown"
    try:
        sender = await message.get_sender()
    except Exception:
        return "Unknown"
    if sender is None:
        return "Unknown"
    parts: list[str] = []
    if getattr(sender, "first_name", None):
        parts.append(sender.first_name)
    if getattr(sender, "last_name", None):
        parts.append(sender.last_name)
    name = " ".join(parts).strip()
    if name:
        return name
    if getattr(sender, "title", None):
        return sender.title
    if getattr(sender, "username", None):
        return sender.username
    return "Unknown"


async def scan_chat_hashtag(
    client: TelegramClient,
    chat_id: int,
    hashtag: str,
) -> list[IdeaRecord]:
    """Все сообщения в чате, найденные поиском Telegram по хэштегу."""
    records: list[IdeaRecord] = []
    seen: set[tuple[str, str, str]] = set()

    async for message in client.iter_messages(chat_id, search=hashtag, limit=None):
        if not message.text:
            continue
        author = await _author_name(client, message)
        record = IdeaRecord(
            author=author,
            date=_format_date(message),
            text=message.text.strip(),
        )
        key = record.key()
        if key in seen:
            continue
        seen.add(key)
        records.append(record)

    records.sort(key=lambda r: r.date)
    return records


async def scan_all(
    client: TelegramClient,
    chat_ids: list[int],
    hashtag: str,
) -> list[IdeaRecord]:
    merged: list[IdeaRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for chat_id in chat_ids:
        for record in await scan_chat_hashtag(client, chat_id, hashtag):
            key = record.key()
            if key not in seen:
                seen.add(key)
                merged.append(record)
    merged.sort(key=lambda r: r.date)
    return merged

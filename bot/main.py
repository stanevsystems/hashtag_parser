#!/usr/bin/env python3
"""
Бот-сборщик идей: сканирует историю чата по #япридумал, обновляет ideas.json в GitHub.

Использует Telethon (user API) — только так доступна полная история чата.
Управление: /start /stop /interval /sync /status (только TELEGRAM_ADMIN_IDS).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import telethon

from config import Settings
from git_sync import GitSyncError
from proxy_config import build_telethon_client_options
from state import BotState
from sync_service import run_sync_cycle
from telethon import TelegramClient, events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hashtag_bot")


def session_base_path(settings: Settings) -> Path:
    return settings.state_path.parent / settings.session_name


def session_file_path(settings: Settings) -> Path:
    return Path(str(session_base_path(settings)) + ".session")


def _session_mismatch_hint(settings: Settings) -> str:
    sf = session_file_path(settings)
    return (
        f"\nSession file format mismatch ({sf}).\n"
        "Cause: running with system Python/old Telethon while session was created by venv.\n"
        "Fix:\n"
        "  1) .\\run.ps1 --test   (uses venv)\n"
        "  2) If still fails, delete the .session file and login again:\n"
        f"     Remove-Item -Force \"{sf}\"\n"
    )


def create_telegram_client(settings: Settings) -> TelegramClient:
    client_opts = build_telethon_client_options(settings.proxy)
    try:
        return TelegramClient(
            str(session_base_path(settings)),
            settings.api_id,
            settings.api_hash,
            **client_opts,
        )
    except ValueError as e:
        if "too many values to unpack" in str(e):
            raise ValueError(_session_mismatch_hint(settings)) from e
        raise


class HashtagBotApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = BotState.load(settings.state_path, settings.interval_hours)
        self._sync_lock = asyncio.Lock()
        self._scheduler_task: asyncio.Task | None = None
        self.client = create_telegram_client(settings)

    def _is_admin(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in self.settings.admin_ids

    async def _reply_admin_only(self, event: events.NewMessage.Event) -> bool:
        if not self._is_admin(event.sender_id):
            await event.reply("⛔ Команда только для администратора.")
            return False
        return True

    def _status_text(self) -> str:
        s = self.state
        running = "🟢 запущен" if s.running else "🔴 остановлен"
        last = s.last_sync or "—"
        err = f"\n⚠️ Ошибка: {s.last_error}" if s.last_error else ""
        return (
            f"**Статус:** {running}\n"
            f"**Интервал:** {s.interval_hours} ч\n"
            f"**Последняя синхронизация:** {last}\n"
            f"**Записей в последнем скане:** {s.last_sync_count}\n"
            f"**Чаты:** `{self.settings.chat_ids}`\n"
            f"**Хэштеги:** {', '.join(self.settings.hashtags)}\n"
            f"**Репозиторий:** `{self.settings.git_repo_url}`\n"
            f"**Сеть:** {self.settings.proxy.describe()}"
            f"{err}"
        )

    async def do_sync(self, notify_event: events.NewMessage.Event | None = None) -> None:
        async with self._sync_lock:
            if notify_event:
                await notify_event.reply("🔄 Синхронизация…")
            try:
                total, added = await run_sync_cycle(
                    self.client, self.settings, self.state
                )
                self.state.save(self.settings.state_path)
                msg = (
                    f"✅ Готово: найдено **{total}**, "
                    f"добавлено в репозиторий **{added}**."
                )
                logger.info(msg)
                if notify_event:
                    await notify_event.reply(msg)
            except GitSyncError as e:
                self.state.mark_sync_error(str(e))
                self.state.save(self.settings.state_path)
                logger.exception("Ошибка git")
                if notify_event:
                    await notify_event.reply(f"❌ Git: {e}")
            except Exception as e:
                self.state.mark_sync_error(str(e))
                self.state.save(self.settings.state_path)
                logger.exception("Ошибка синхронизации")
                if notify_event:
                    await notify_event.reply(f"❌ {type(e).__name__}: {e}")

    async def _scheduler_loop(self) -> None:
        interval_sec = self.state.interval_hours * 3600
        logger.info("Планировщик: интервал %.1f ч", self.state.interval_hours)
        while True:
            await asyncio.sleep(interval_sec)
            if not self.state.running:
                continue
            logger.info("Плановая синхронизация")
            await self.do_sync()

    def _ensure_scheduler(self) -> None:
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    def register_handlers(self) -> None:
        client = self.client

        @client.on(events.NewMessage(pattern=r"^/start$"))
        async def cmd_start(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            self.state.running = True
            self.state.save(self.settings.state_path)
            self._ensure_scheduler()
            await event.reply(
                "▶️ Автосинхронизация включена.\n" + self._status_text()
            )

        @client.on(events.NewMessage(pattern=r"^/stop$"))
        async def cmd_stop(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            self.state.running = False
            self.state.save(self.settings.state_path)
            await event.reply(
                "⏸ Автосинхронизация остановлена (ручной /sync по-прежнему доступен).\n"
                + self._status_text()
            )

        @client.on(events.NewMessage(pattern=r"^/interval(?:\s+(\d+(?:\.\d+)?))?$"))
        async def cmd_interval(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            arg = event.pattern_match.group(1)
            if arg is None:
                await event.reply(
                    f"Текущий интервал: **{self.state.interval_hours}** ч.\n"
                    "Задать: `/interval 2` или `/interval 1.5`"
                )
                return
            hours = float(arg)
            if hours < 0.25:
                await event.reply("Минимальный интервал — 0.25 ч (15 мин).")
                return
            if hours > 168:
                await event.reply("Максимальный интервал — 168 ч (неделя).")
                return
            self.state.interval_hours = hours
            self.state.save(self.settings.state_path)
            self._ensure_scheduler()
            await event.reply(
                f"✅ Интервал обновления: **{hours}** ч.\n"
                "Перезапуск планировщика выполнен."
            )

        @client.on(events.NewMessage(pattern=r"^/sync$"))
        async def cmd_sync(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            await self.do_sync(event)

        @client.on(events.NewMessage(pattern=r"^/status$"))
        async def cmd_status(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            await event.reply(self._status_text())

        @client.on(events.NewMessage(pattern=r"^/help$"))
        async def cmd_help(event: events.NewMessage.Event) -> None:
            if not await self._reply_admin_only(event):
                return
            await event.reply(
                "**Команды (только админ):**\n"
                "`/start` — включить автосинхронизацию\n"
                "`/stop` — выключить автосинхронизацию\n"
                "`/interval [часы]` — интервал (по умолчанию 2)\n"
                "`/sync` — синхронизация сейчас\n"
                "`/status` — состояние\n"
                "`/help` — эта справка"
            )

    async def run(self) -> None:
        settings = self.settings
        self.register_handlers()
        await self.client.start()
        me = await self.client.get_me()
        logger.info(
            "Авторизован: %s (id=%s)",
            me.first_name,
            me.id,
        )

        if self.state.running:
            self._ensure_scheduler()
            asyncio.create_task(self._delayed_first_sync())

        print(
            "\n✅ Бот запущен. Напишите себе в «Избранное» или в личку: /help\n"
            f"   Админы: {settings.admin_ids}\n"
            f"   Интервал: {self.state.interval_hours} ч, running={self.state.running}\n"
        )
        await self.client.run_until_disconnected()

    async def _delayed_first_sync(self) -> None:
        """Первая синхронизация через 30 с после старта (не блокирует запуск)."""
        await asyncio.sleep(30)
        if self.state.running:
            await self.do_sync()


async def test_connection(settings: Settings) -> None:
    """Проверка сети и сессии без интерактивного входа."""
    print(f"Python: {sys.executable}")
    print(f"Telethon: {telethon.__version__}")
    print(f"Network: {settings.proxy.describe()}")
    sf = session_file_path(settings)
    print(f"Session: {sf} ({'exists' if sf.exists() else 'missing'})")
    client = create_telegram_client(settings)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(
                "Not authorized. Run once (interactive):\n"
                "  .\\run.ps1 --login\n"
                "  or: docker compose run --rm -it bot python main.py --login"
            )
            return
        me = await client.get_me()
        print(f"OK: {me.first_name} (id={me.id})")
    finally:
        await client.disconnect()


async def login_interactive(settings: Settings) -> None:
    """Однократный вход: телефон + код → файл .session в data/."""
    print(f"Network: {settings.proxy.describe()}")
    client = create_telegram_client(settings)
    try:
        await client.start()
        me = await client.get_me()
        print(f"Logged in: {me.first_name} (id={me.id})")
        print(f"Session saved: {session_file_path(settings)}")
    finally:
        await client.disconnect()


async def amain() -> None:
    try:
        settings = Settings.load()
    except ValueError as e:
        print(f"Config error: {e}")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "test"):
        try:
            await test_connection(settings)
        except ValueError as e:
            print(e)
            sys.exit(1)
        return

    if len(sys.argv) > 1 and sys.argv[1] in ("--login", "login"):
        try:
            await login_interactive(settings)
        except Exception as e:
            print(f"Login failed: {type(e).__name__}: {e}")
            if "ApiIdInvalid" in type(e).__name__:
                print(
                    "Check API_ID and API_HASH at https://my.telegram.org/apps "
                    "(App api_id / App api_hash, not BotFather)."
                )
            sys.exit(1)
        return

    app = HashtagBotApp(settings)
    await app.run()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()

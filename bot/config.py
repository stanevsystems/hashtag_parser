"""Конфигурация бота. Секреты только из .env и secrets/."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from proxy_config import ProxySettings

BOT_DIR = Path(__file__).resolve().parent
load_dotenv(BOT_DIR / ".env")


def _parse_int_list(value: str | None) -> list[int]:
    if not value or not value.strip():
        return []
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def _parse_str_list(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _normalize_api_id(raw: str | None) -> int | None:
    if not raw:
        return None
    api_id = int(raw.strip())
    if api_id <= 2_147_483_647:
        return api_id
    # Telethon на Windows: привести к signed int32
    return (api_id & 0xFFFFFFFF) - (1 << 32 if api_id & 0x80000000 else 0)


@dataclass
class HashtagExportTarget:
    """Пункт назначения экспорта (задел под несколько хэштегов)."""

    hashtag: str
    git_repo_url: str
    git_file_path: str = "ideas.json"
    chat_ids: list[int] = field(default_factory=list)


@dataclass
class Settings:
    api_id: int
    api_hash: str
    admin_ids: list[int]
    chat_ids: list[int]
    hashtags: list[str]
    session_name: str
    interval_hours: float
    git_repo_url: str
    git_repo_dir: Path
    git_branch: str
    git_ideas_file: str
    git_ssh_key: Path
    git_author_name: str
    git_author_email: str
    state_path: Path
    proxy: ProxySettings
    # Задел: список целей по хэштегам (пока один дефолтный)
    export_targets: list[HashtagExportTarget] = field(default_factory=list)

    @classmethod
    def load(cls) -> Settings:
        api_id = _normalize_api_id(os.getenv("API_ID") or os.getenv("api_id"))
        api_hash = (os.getenv("API_HASH") or os.getenv("api_hash") or "").strip()
        api_hash = api_hash.strip('"').strip("'")
        if api_id is None or not api_hash:
            raise ValueError(
                "Задайте API_ID и API_HASH в .env (my.telegram.org/apps)"
            )
        if len(api_hash) != 32 or not all(c in "0123456789abcdef" for c in api_hash.lower()):
            raise ValueError(
                "API_HASH должен быть 32 hex-символа с https://my.telegram.org/apps "
                "(не путать с BotFather token)"
            )

        admin_ids = _parse_int_list(os.getenv("TELEGRAM_ADMIN_IDS"))
        if not admin_ids:
            raise ValueError("Задайте TELEGRAM_ADMIN_IDS — user id администраторов")

        chat_ids = _parse_int_list(os.getenv("CHAT_IDS"))
        if not chat_ids:
            raise ValueError("Задайте CHAT_IDS — id чатов для сканирования")

        hashtags = _parse_str_list(os.getenv("HASHTAGS")) or ["#япридумал"]
        hashtags = [
            h if h.startswith("#") else f"#{h}" for h in hashtags
        ]

        interval = float(os.getenv("SYNC_INTERVAL_HOURS", "2"))

        git_repo_url = os.getenv(
            "GIT_REPO_URL",
            "git@github.com:stanevsystems/telegram-ideas.git",
        ).strip()
        git_repo_dir = BOT_DIR / "data" / "repo"
        git_branch = os.getenv("GIT_BRANCH", "main").strip()
        git_ideas_file = os.getenv("GIT_IDEAS_FILE", "ideas.json").strip()

        ssh_key = os.getenv("GIT_SSH_KEY_PATH", "secrets/github_deploy_key")
        git_ssh_key = (BOT_DIR / ssh_key).resolve() if not Path(ssh_key).is_absolute() else Path(ssh_key)

        export_targets = [
            HashtagExportTarget(
                hashtag=tag,
                git_repo_url=git_repo_url,
                git_file_path=git_ideas_file,
                chat_ids=chat_ids,
            )
            for tag in hashtags
        ]

        return cls(
            api_id=api_id,
            api_hash=api_hash,
            admin_ids=admin_ids,
            chat_ids=chat_ids,
            hashtags=hashtags,
            session_name=os.getenv("SESSION_NAME", "hashtag_bot_session"),
            interval_hours=interval,
            git_repo_url=git_repo_url,
            git_repo_dir=git_repo_dir,
            git_branch=git_branch,
            git_ideas_file=git_ideas_file,
            git_ssh_key=git_ssh_key,
            git_author_name=os.getenv("GIT_AUTHOR_NAME", "Hashtag Bot"),
            git_author_email=os.getenv(
                "GIT_AUTHOR_EMAIL", "hashtag-bot@stanevsystems.local"
            ),
            state_path=BOT_DIR / "data" / "state.json",
            proxy=ProxySettings.from_env(),
            export_targets=export_targets,
        )

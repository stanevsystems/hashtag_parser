"""Клонирование репозитория и push через deploy key."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from config import Settings
from exporter import load_existing_ideas, merge_ideas, write_ideas
from scanner import IdeaRecord

logger = logging.getLogger(__name__)


class GitSyncError(Exception):
    pass


def _git_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    key = settings.git_ssh_key
    if not key.exists():
        raise GitSyncError(
            f"SSH-ключ не найден: {key}. Положите deploy key в secrets/ "
            "и укажите GIT_SSH_KEY_PATH в .env"
        )
    # Windows: путь с обратными слэшами; ssh принимает оба варианта
    key_str = str(key).replace("\\", "/")
    env["GIT_SSH_COMMAND"] = (
        f'ssh -i "{key_str}" -o IdentitiesOnly=yes '
        f"-o StrictHostKeyChecking=accept-new"
    )
    env["GIT_AUTHOR_NAME"] = settings.git_author_name
    env["GIT_AUTHOR_EMAIL"] = settings.git_author_email
    env["GIT_COMMITTER_NAME"] = settings.git_author_name
    env["GIT_COMMITTER_EMAIL"] = settings.git_author_email
    return env


def _run(
    args: list[str],
    cwd: Path | None,
    env: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    logger.debug("git %s (cwd=%s)", " ".join(args), cwd)
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise GitSyncError(
            f"{' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def ensure_repo(settings: Settings) -> Path:
    env = _git_env(settings)
    repo_dir = settings.git_repo_dir
    if repo_dir.exists() and (repo_dir / ".git").exists():
        _run(["git", "fetch", "origin"], repo_dir, env)
        _run(["git", "checkout", settings.git_branch], repo_dir, env, check=False)
        _run(["git", "reset", "--hard", f"origin/{settings.git_branch}"], repo_dir, env)
        return repo_dir

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["git", "clone", "--branch", settings.git_branch, settings.git_repo_url, str(repo_dir)],
        None,
        env,
    )
    return repo_dir


def push_ideas(
    settings: Settings,
    new_records: list[IdeaRecord],
    *,
    commit_message: str | None = None,
) -> int:
    """Обновить ideas.json в репозитории и запушить. Возвращает число новых записей."""
    env = _git_env(settings)
    repo_dir = ensure_repo(settings)
    ideas_path = repo_dir / settings.git_ideas_file

    existing = load_existing_ideas(ideas_path)
    before = len(existing)
    merged = merge_ideas(existing, new_records)
    added = len(merged) - before

    write_ideas(ideas_path, merged)

    _run(["git", "add", settings.git_ideas_file], repo_dir, env)

    status = _run(["git", "status", "--porcelain"], repo_dir, env)
    if not status.stdout.strip():
        logger.info("Нет изменений для коммита")
        return 0

    msg = commit_message or f"sync: +{added} ideas ({len(merged)} total)"
    _run(["git", "commit", "-m", msg], repo_dir, env)
    _run(["git", "push", "origin", settings.git_branch], repo_dir, env)
    return added

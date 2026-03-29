"""Optional auto-commit of reports and memory."""

from __future__ import annotations

from pathlib import Path

from git import InvalidGitRepositoryError, Repo
from loguru import logger

from src.config import AppConfig


def maybe_git_commit(root: Path, cfg: AppConfig, message: str) -> None:
    if not cfg.git.auto_commit:
        return
    try:
        repo = Repo(root)
    except InvalidGitRepositoryError:
        logger.debug("Not a git repo; skip auto-commit")
        return
    try:
        if repo.is_dirty(untracked_files=True):
            repo.index.add(["reports", "memory.json"])
            repo.index.commit(message)
            logger.info("Git commit: {}", message)
            if cfg.git.auto_push and repo.remotes:
                repo.remotes.origin.push()
                logger.info("Git push completed")
    except Exception as e:  # noqa: BLE001
        logger.warning("Git operation failed: {}", e)
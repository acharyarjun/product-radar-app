"""Temu scraper (optional stub)."""

from __future__ import annotations

from loguru import logger

from src.config import AppConfig
from src.models import Product


def fetch_temu_products(cfg: AppConfig) -> list[Product]:
    if not cfg.sources.temu.enabled:
        return []
    logger.info("Temu enabled but scraper not implemented; returning empty list")
    return []
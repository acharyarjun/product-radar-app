"""Load config.yaml and merge GitHub-friendly environment secrets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RadarConfig(BaseModel):
    max_source_price_eur: float = 100.0
    min_profit_margin: float = 0.5
    min_demand_score: int = 5
    target_market: str = "Spain"
    target_city: str = "Bilbao"
    currency: str = "EUR"
    max_products_per_run: int = 50
    categories: list[str] = Field(default_factory=list)


class AliExpressSource(BaseModel):
    enabled: bool = True
    base_url: str = "https://www.aliexpress.com"
    sort_by: str = "orders"


class TemuSource(BaseModel):
    enabled: bool = False
    base_url: str = "https://www.temu.com"


class GoogleTrendsSource(BaseModel):
    enabled: bool = True
    region: str = "ES"
    timeframe: str = "today 3-m"


class SourcesConfig(BaseModel):
    aliexpress: AliExpressSource = Field(default_factory=AliExpressSource)
    temu: TemuSource = Field(default_factory=TemuSource)
    google_trends: GoogleTrendsSource = Field(default_factory=GoogleTrendsSource)


class AmazonEsCompetition(BaseModel):
    enabled: bool = True
    base_url: str = "https://www.amazon.es"


class GoogleShoppingCompetition(BaseModel):
    enabled: bool = False


class CompetitionConfig(BaseModel):
    amazon_es: AmazonEsCompetition = Field(default_factory=AmazonEsCompetition)
    google_shopping: GoogleShoppingCompetition = Field(default_factory=GoogleShoppingCompetition)


class NotionPropertyNames(BaseModel):
    title: str = "Name"
    source: str = "Source"
    source_url: str = "Source URL"
    source_price_eur: str = "Source price EUR"
    recommended_sale_eur: str = "Recommended sale EUR"
    margin_pct: str = "Margin pct"
    demand: str = "Demand"
    competition: str = "Competition"
    viability: str = "Viability"
    category: str = "Category"
    run_date: str = "Run date"
    notes: str = "Notes"
    pipeline_status: str = "Pipeline status"
    target: str = "Target"


class NotionConfig(BaseModel):
    enabled: bool = False
    database_id: str = ""
    register_marginal: bool = False
    notion_version: str = "2022-06-28"
    digest_parent_page_id: str = ""
    property_names: NotionPropertyNames = Field(default_factory=NotionPropertyNames)


class ScheduleConfig(BaseModel):
    daily_run_time: str = "08:00"
    timezone: str = "Europe/Madrid"


class GitConfig(BaseModel):
    auto_commit: bool = True
    auto_push: bool = False
    commit_prefix: str = "radar"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/radar.log"


class StorageConfig(BaseModel):
    sqlite_path: str = "data/radar.db"


class AppConfig(BaseModel):
    radar: RadarConfig = Field(default_factory=RadarConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    competition: CompetitionConfig = Field(default_factory=CompetitionConfig)
    notion: NotionConfig = Field(default_factory=NotionConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


class EnvSecrets(BaseSettings):
    """Secrets and CI overrides (GitHub Actions: repository Secrets / Variables)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    notion_token: str | None = Field(default=None, validation_alias="NOTION_TOKEN")
    notion_database_id: str | None = Field(default=None, validation_alias="NOTION_DATABASE_ID")
    notion_enabled: str | None = Field(default=None, validation_alias="NOTION_ENABLED")
    git_auto_commit: str | None = Field(default=None, validation_alias="RADAR_GIT_AUTO_COMMIT")
    git_auto_push: str | None = Field(default=None, validation_alias="RADAR_GIT_AUTO_PUSH")
    aliexpress_affiliate_key: str | None = Field(
        default=None, validation_alias="ALIEXPRESS_AFFILIATE_KEY"
    )


def _parse_bool(v: str | None) -> bool | None:
    if v is None or v == "":
        return None
    return v.strip().lower() in ("1", "true", "yes", "on")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_raw_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing config: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_env_into_config(data: dict[str, Any], env: EnvSecrets) -> dict[str, Any]:
    out = dict(data)
    notion = dict(out.get("notion") or {})
    if env.notion_database_id:
        notion["database_id"] = env.notion_database_id
    ne = _parse_bool(env.notion_enabled)
    if ne is not None:
        notion["enabled"] = ne
    out["notion"] = notion

    git = dict(out.get("git") or {})
    gac = _parse_bool(env.git_auto_commit)
    if gac is not None:
        git["auto_commit"] = gac
    gap = _parse_bool(env.git_auto_push)
    if gap is not None:
        git["auto_push"] = gap
    out["git"] = git
    return out


def load_app_config(root: Path | None = None) -> tuple[AppConfig, EnvSecrets]:
    root = root or project_root()
    raw = load_raw_config(root / "config.yaml")
    env = EnvSecrets()
    raw = merge_env_into_config(raw, env)
    cfg = AppConfig.model_validate(raw)
    return cfg, env


def setup_logging(cfg: AppConfig) -> None:
    logger.remove()
    log_path = project_root() / cfg.logging.file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level=cfg.logging.level,
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
    )
    logger.add(lambda m: print(m, end=""), level=cfg.logging.level)


def notion_token_resolved(env: EnvSecrets) -> str | None:
    return env.notion_token
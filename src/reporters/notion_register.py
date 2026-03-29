"""Register product analyses as rows in a Notion database."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
from loguru import logger

from src.config import AppConfig, EnvSecrets, notion_token_resolved
from src.models import ProductAnalysis, ViabilityStatus


NOTION_API = "https://api.notion.com/v1"


def _rich(name: str, text: str) -> dict[str, Any]:
    return {name: {"rich_text": [{"text": {"content": text[:2000]}}]}}


def _title(name: str, text: str) -> dict[str, Any]:
    return {name: {"title": [{"text": {"content": text[:2000]}}]}}


def _url_prop(name: str, url: str | None) -> dict[str, Any]:
    if not url:
        return {name: {"url": None}}
    return {name: {"url": url[:2000]}}


def _num(name: str, value: float | int) -> dict[str, Any]:
    return {name: {"number": float(value)}}


def _date_prop(name: str, d: date) -> dict[str, Any]:
    return {name: {"date": {"start": d.isoformat()}}}


def analysis_to_properties(cfg: AppConfig, a: ProductAnalysis, run_date: date) -> dict[str, Any]:
    pn = cfg.notion.property_names
    target = f"{cfg.radar.target_city} / {cfg.radar.target_market}"
    margin_pct = round(a.estimated_margin * 100.0, 2)
    props: dict[str, Any] = {}
    props.update(_title(pn.title, a.product.name))
    props.update(_rich(pn.source, a.product.source))
    props.update(_url_prop(pn.source_url, a.product.source_url))
    props.update(_num(pn.source_price_eur, a.product.source_price_eur))
    props.update(_num(pn.recommended_sale_eur, a.recommended_sale_price))
    props.update(_num(pn.margin_pct, margin_pct))
    props.update(_num(pn.demand, a.demand_score))
    props.update(_rich(pn.competition, a.competition_level))
    props.update(_rich(pn.viability, a.viability.value))
    props.update(_rich(pn.category, a.product.category))
    props.update(_date_prop(pn.run_date, run_date))
    props.update(_rich(pn.notes, a.notes[:1900]))
    props.update(_rich(pn.pipeline_status, "New"))
    props.update(_rich(pn.target, target))
    return props


def create_database_row(
    token: str,
    notion_version: str,
    database_id: str,
    properties: dict[str, Any],
) -> str | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }
    body = {"parent": {"database_id": database_id}, "properties": properties}
    try:
        r = httpx.post(f"{NOTION_API}/pages", headers=headers, json=body, timeout=60.0)
        if r.status_code >= 400:
            logger.error("Notion API error {}: {}", r.status_code, r.text[:500])
            return None
        data = r.json()
        return str(data.get("id", "")) or None
    except Exception as e:  # noqa: BLE001
        logger.error("Notion request failed: {}", e)
        return None


def register_analyses(
    cfg: AppConfig,
    env: EnvSecrets,
    analyses: list[ProductAnalysis],
    run_date: date,
    already_registered_urls: set[str],
) -> dict[str, str]:
    """Returns map source_url -> notion_page_id for newly created pages."""
    token = notion_token_resolved(env)
    if not cfg.notion.enabled or not token or not cfg.notion.database_id.strip():
        logger.info("Notion register skipped (disabled or missing token/database_id)")
        return {}
    out: dict[str, str] = {}
    for a in analyses:
        if a.viability == ViabilityStatus.NOT_VIABLE:
            continue
        if a.viability == ViabilityStatus.MARGINAL and not cfg.notion.register_marginal:
            continue
        url = a.product.source_url
        if url in already_registered_urls:
            continue
        props = analysis_to_properties(cfg, a, run_date)
        pid = create_database_row(
            token,
            cfg.notion.notion_version,
            cfg.notion.database_id.strip(),
            props,
        )
        if pid:
            out[url] = pid
            logger.info("Notion row created for {}", a.product.name[:50])
    return out


def _paragraph_block(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def publish_digest_if_configured(
    cfg: AppConfig,
    env: EnvSecrets,
    run_date: date,
    analyses: list[ProductAnalysis],
    *,
    notion_new_urls: set[str],
) -> None:
    """Create a summary child page under digest_parent_page_id when configured."""
    token = notion_token_resolved(env)
    parent = (cfg.notion.digest_parent_page_id or "").strip()
    if not parent or not token:
        return
    title_key = cfg.notion.digest_page_title_property.strip() or "title"
    viable = sum(1 for a in analyses if a.viability == ViabilityStatus.VIABLE)
    marginal = sum(1 for a in analyses if a.viability == ViabilityStatus.MARGINAL)
    scanned = len(analyses)
    lines = [
        f"Run date: {run_date.isoformat()}",
        f"Productos escaneados (nuevos en esta pasada): {scanned}",
        f"Viables: {viable} | Marginales: {marginal}",
        f"Nuevas filas Notion (esta pasada): {len(notion_new_urls)}",
        f"Mercado objetivo: {cfg.radar.target_city}, {cfg.radar.target_market}",
    ]
    children = [_paragraph_block(t) for t in lines]
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": cfg.notion.notion_version,
        "Content-Type": "application/json",
    }
    page_title = f"Radar summary - {run_date.isoformat()}"
    body: dict[str, Any] = {
        "parent": {"page_id": parent},
        "properties": {
            title_key: {"title": [{"text": {"content": page_title[:2000]}}]},
        },
        "children": children[:99],
    }
    try:
        r = httpx.post(f"{NOTION_API}/pages", headers=headers, json=body, timeout=60.0)
        if r.status_code >= 400:
            logger.error("Notion digest page error {}: {}", r.status_code, r.text[:500])
            return
        logger.info("Notion digest page created: {}", page_title)
    except Exception as e:  # noqa: BLE001
        logger.error("Notion digest failed: {}", e)
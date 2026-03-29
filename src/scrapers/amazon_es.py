"""Amazon.es search for competitor prices."""

from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from src.config import AppConfig
from src.models import CompetitorData
from src.scrapers import http_utils


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|[\d]+[.,]\d{2})", text.replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    if raw.count(".") > 1:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def search_competitors(
    cfg: AppConfig,
    client: httpx.Client,
    product_name: str,
    limit: int = 5,
) -> list[CompetitorData]:
    if not cfg.competition.amazon_es.enabled:
        return []
    base = cfg.competition.amazon_es.base_url.rstrip("/")
    q = quote_plus(product_name[:80])
    url = f"{base}/s?k={q}"
    if not http_utils.scraping_allowed(client, url):
        logger.warning("robots may disallow Amazon search; skipping {}", url)
        return []
    http_utils.delay_seconds(3.0, 8.0)
    try:
        r = client.get(url, timeout=30.0)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        logger.error("Amazon.es search failed: {}", e)
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results: list[CompetitorData] = []
    for card in soup.select("[data-component-type=s-search-result]")[:limit]:
        link = card.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        href = urljoin(base, link["href"])
        title_el = card.select_one("h2 span")
        title = title_el.get_text(strip=True) if title_el else ""
        price_el = card.select_one(".a-price .a-offscreen")
        price_txt = price_el.get_text(strip=True) if price_el else ""
        price = _parse_price(price_txt)
        if price is None:
            continue
        reviews_el = card.select_one('[aria-label$="estrellas"]') or card.select_one(".a-size-base")
        reviews = 0
        rating = 0.0
        if reviews_el:
            lab = reviews_el.get("aria-label") or reviews_el.get_text()
            rm = re.search(r"([\d.,]+)\s*(?:de|out of)?\s*5", lab or "")
            if rm:
                rating = float(rm.group(1).replace(",", "."))
            nm = re.search(r"(\d[\d.]*)", lab or "")
            if nm and "valoraci" in (lab or "").lower():
                try:
                    reviews = int(nm.group(1).replace(".", ""))
                except ValueError:
                    reviews = 0
        results.append(
            CompetitorData(
                platform="amazon.es",
                price_eur=price,
                seller_name=title[:120] or "unknown",
                url=href,
                num_reviews=reviews,
                rating=rating,
            )
        )
    logger.debug("Amazon.es {} hits for {}", len(results), product_name[:40])
    return results
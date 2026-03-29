"""AliExpress listing discovery (httpx + selectolax, BeautifulSoup fallback)."""

from __future__ import annotations

import re
from urllib.parse import urljoin, quote_plus

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from src.config import AliExpressSource, AppConfig
from src.models import Product
from src.scrapers import http_utils

CATEGORY_SEARCH_TERMS: dict[str, str] = {
    "electronics": "electronic gadgets",
    "home_garden": "home decor garden",
    "kitchen": "kitchen gadgets",
    "sports_outdoor": "sports outdoor fitness",
    "beauty_health": "beauty health care",
    "tools": "power tools diy",
    "pet_supplies": "pet supplies dog cat",
}


def _fx_usd_eur(client: httpx.Client) -> float:
    try:
        r = client.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "EUR"},
            timeout=15.0,
        )
        r.raise_for_status()
        return float(r.json()["rates"]["EUR"])
    except Exception as e:  # noqa: BLE001
        logger.warning("FX USD->EUR fallback 0.92 ({})", e)
        return 0.92


def _fx_cny_eur(client: httpx.Client) -> float:
    try:
        r = client.get(
            "https://api.frankfurter.app/latest",
            params={"from": "CNY", "to": "EUR"},
            timeout=15.0,
        )
        r.raise_for_status()
        return float(r.json()["rates"]["EUR"])
    except Exception as e:  # noqa: BLE001
        logger.warning("FX CNY->EUR fallback 0.13 ({})", e)
        return 0.13


def _parse_price_eur(text: str, usd_rate: float, cny_rate: float) -> float | None:
    if not text:
        return None
    t = text.replace("\xa0", " ").strip()
    m = re.search(
        r"EUR\s*([\d.,]+)|€\s*([\d.,]+)|USD\s*([\d.,]+)|US\s*\$\s*([\d.,]+)|([\d.,]+)\s*€",
        t,
        re.I,
    )
    if not m:
        nums = re.findall(r"[\d]+(?:[.,][\d]+)?", t.replace(",", "."))
        if not nums:
            return None
        raw = nums[0].replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            return None
        if val > 5000:
            return None
        return val
    for g in m.groups():
        if g:
            raw = g.replace(",", ".")
            try:
                val = float(raw)
            except ValueError:
                continue
            if m.group(3) or m.group(4):
                return round(val * usd_rate, 2)
            return val
    return None


def _listing_url(base_url: str, category_key: str, sort_by: str) -> str:
    term = CATEGORY_SEARCH_TERMS.get(category_key, category_key.replace("_", " "))
    q = quote_plus(term)
    sort = "total_tranpro_desc" if sort_by == "orders" else "default"
    return f"{base_url.rstrip('/')}/wholesale?SearchText={q}&sortType={sort}&page=1"


def _iter_listings_selectolax(html: str, base: str) -> list[tuple[str, str, str, str | None]]:
    try:
        from selectolax.lexbor import LexborHTMLParser
    except ImportError:
        return []
    tree = LexborHTMLParser(html)
    rows: list[tuple[str, str, str, str | None]] = []
    for node in tree.css('a[href*="/item/"]'):
        attrs = node.attributes or {}
        href = attrs.get("href") or ""
        if not href:
            continue
        full = urljoin(base, href.split("?")[0])
        title = (attrs.get("title") or "").strip()
        if not title:
            title = (node.text(deep=True) or "").strip()
        parent = node.parent
        price_text = ""
        img: str | None = None
        if parent is not None:
            price_text = (parent.text(deep=True) or "").strip()[:500]
            for im in parent.css("img"):
                src = (im.attributes or {}).get("src")
                if src:
                    img = urljoin(base, src)
                    break
        rows.append((full, title, price_text, img))
    return rows


def _iter_listings_bs4(html: str, base: str) -> list[tuple[str, str, str, str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str, str, str | None]] = []
    for a in soup.select('a[href*="/item/"]'):
        href = a.get("href") or ""
        full = urljoin(base, href.split("?")[0])
        title = (a.get("title") or a.get_text() or "").strip()
        parent = a.find_parent(["div", "li", "article"])
        price_text = ""
        if parent:
            price_text = parent.get_text(" ", strip=True)[:500]
        img = None
        if parent:
            im = parent.find("img")
            if im and im.get("src"):
                img = urljoin(base, im["src"])
        rows.append((full, title, price_text, img))
    return rows


def fetch_products_for_categories(
    cfg: AppConfig,
    client: httpx.Client,
    categories: list[str],
    max_per_category: int,
) -> list[Product]:
    src: AliExpressSource = cfg.sources.aliexpress
    if not src.enabled:
        return []
    base = src.base_url
    if not http_utils.scraping_allowed(client, base + "/"):
        logger.warning("robots.txt suggests skipping AliExpress; continuing with caution")
    usd = _fx_usd_eur(client)
    cny = _fx_cny_eur(client)
    out: list[Product] = []
    seen: set[str] = set()
    for cat in categories:
        if len(out) >= cfg.radar.max_products_per_run:
            break
        http_utils.delay_seconds(2.0, 5.0)
        url = _listing_url(base, cat, src.sort_by)
        try:
            r = client.get(url, timeout=30.0)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            logger.error("AliExpress fetch failed {}: {}", url, e)
            continue
        rows = _iter_listings_selectolax(r.text, base)
        if not rows:
            rows = _iter_listings_bs4(r.text, base)
        for full, title, price_text, img in rows:
            if len(out) >= cfg.radar.max_products_per_run:
                break
            if full in seen:
                continue
            seen.add(full)
            if len(title) < 4:
                continue
            pe = _parse_price_eur(price_text, usd, cny)
            if pe is None:
                pe = _parse_price_eur(title, usd, cny)
            if pe is None:
                continue
            if pe > cfg.radar.max_source_price_eur:
                continue
            out.append(
                Product(
                    name=title[:200],
                    source="aliexpress",
                    source_url=full,
                    source_price_eur=round(pe, 2),
                    category=cat,
                    image_url=img,
                )
            )
            if sum(1 for p in out if p.category == cat) >= max_per_category:
                break
    logger.info("AliExpress discovered {} products", len(out))
    return out
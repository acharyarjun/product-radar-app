"""HTTP helpers: user agents, delays, robots.txt check."""

from __future__ import annotations

import random
import time
from urllib.parse import urlparse

import httpx
from loguru import logger

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def random_ua() -> str:
    return random.choice(USER_AGENTS)


def browser_headers() -> dict[str, str]:
    return {
        "User-Agent": random_ua(),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def delay_seconds(min_s: float, max_s: float) -> None:
    t = random.uniform(min_s, max_s)
    time.sleep(t)


def robots_txt_url(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return ""
    return f"{p.scheme}://{p.netloc}/robots.txt"


def path_allowed_by_robots(robots_body: str, path: str) -> bool:
    """Very small robots.txt parser: honor Disallow: prefix if no matching Allow."""
    if not robots_body.strip():
        return True
    path = path or "/"
    disallows: list[str] = []
    allows: list[str] = []
    current: str | None = None
    for line in robots_body.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("user-agent:"):
            ua = line.split(":", 1)[1].strip()
            current = ua
            continue
        if current and current != "*" and "product" not in current.lower():
            continue
        if line.lower().startswith("disallow:"):
            v = line.split(":", 1)[1].strip()
            if v:
                disallows.append(v)
        elif line.lower().startswith("allow:"):
            v = line.split(":", 1)[1].strip()
            if v:
                allows.append(v)
    for a in allows:
        if path.startswith(a):
            return True
    for d in disallows:
        if d == "/":
            return False
        if path.startswith(d):
            return False
    return True


def fetch_robots(client: httpx.Client, base: str) -> str:
    u = robots_txt_url(base)
    if not u:
        return ""
    try:
        r = client.get(u, timeout=15.0)
        if r.status_code == 200:
            return r.text
    except Exception as e:  # noqa: BLE001
        logger.debug("robots fetch failed {}: {}", u, e)
    return ""


def url_path(url: str) -> str:
    p = urlparse(url)
    q = f"?{p.query}" if p.query else ""
    return (p.path or "/") + q


def scraping_allowed(client: httpx.Client, target_url: str) -> bool:
    p = urlparse(target_url)
    base = f"{p.scheme}://{p.netloc}"
    body = fetch_robots(client, base)
    if not body:
        return True
    return path_allowed_by_robots(body, url_path(target_url))
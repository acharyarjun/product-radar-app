"""Google Trends demand score via pytrends."""

from __future__ import annotations

from loguru import logger
from pytrends.request import TrendReq

from src.config import AppConfig


def demand_score_for_product(cfg: AppConfig, product_name: str) -> int:
    if not cfg.sources.google_trends.enabled:
        return 5
    city = cfg.radar.target_city
    market = cfg.radar.target_market
    kw = f"{product_name[:60]} {market}"
    try:
        pytrends = TrendReq(hl="es-ES", tz=360)
        pytrends.build_payload(
            [kw],
            cat=0,
            timeframe=cfg.sources.google_trends.timeframe,
            geo=cfg.sources.google_trends.region,
        )
        df = pytrends.interest_over_time()
        if df is None or df.empty or kw not in df.columns:
            logger.debug("pytrends empty for {}", kw)
            return 5
        series = df[kw].astype(float)
        mx = float(series.max()) if len(series) else 0.0
        if mx <= 0:
            return 5
        norm = min(10, max(1, int(round(mx / 10.0 + 0.5))))
        return norm
    except Exception as e:  # noqa: BLE001
        logger.warning("Google Trends failed for {}: {}", product_name[:40], e)
        return 5
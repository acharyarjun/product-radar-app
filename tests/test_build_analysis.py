"""build_analysis demand override (no duplicate Trends call)."""

from __future__ import annotations

from unittest.mock import patch

from src.analyzers import viability
from src.config import AppConfig, RadarConfig
from src.models import Product


def test_build_analysis_demand_override_skips_trends() -> None:
    cfg = AppConfig(radar=RadarConfig())
    p = Product(
        name="Test gadget",
        source="aliexpress",
        source_url="https://example.com/item/1",
        source_price_eur=12.0,
        category="electronics",
    )
    with patch(
        "src.analyzers.viability.google_trends.demand_score_for_product",
        side_effect=AssertionError("trends should not run when demand_score set"),
    ):
        an = viability.build_analysis(cfg, p, [], demand_score=6)
    assert an.demand_score == 6

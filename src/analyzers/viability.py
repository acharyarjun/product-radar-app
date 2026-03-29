"""Viability rules per instructions section 6."""

from __future__ import annotations

from src.analyzers import margin as margin_mod
from src.config import AppConfig
from src.models import CompetitorData, Product, ProductAnalysis, ViabilityStatus
from src.scrapers import google_trends


def classify_viability(
    est_margin: float,
    demand_score: int,
    competition: str,
) -> ViabilityStatus:
    if est_margin >= 0.50 and demand_score >= 7 and competition != "high":
        return ViabilityStatus.VIABLE
    if est_margin >= 0.50 and (demand_score >= 5 or competition == "medium"):
        return ViabilityStatus.MARGINAL
    return ViabilityStatus.NOT_VIABLE


def estimated_monthly_units(demand_score: int, competition: str) -> int:
    base = demand_score * 8
    if competition == "high":
        return max(5, base // 4)
    if competition == "medium":
        return max(10, base // 2)
    return max(15, base)


def build_analysis(
    cfg: AppConfig,
    product: Product,
    competitors: list[CompetitorData],
) -> ProductAnalysis:
    from src.analyzers import competition as comp_mod

    comp_level = comp_mod.competition_level(competitors)
    if competitors:
        avg = sum(c.price_eur for c in competitors) / len(competitors)
    else:
        avg = margin_mod.calculate_recommended_price(
            product.source_price_eur, cfg.radar.min_profit_margin
        )
    est_margin = margin_mod.calculate_margin(product.source_price_eur, avg)
    demand_raw = google_trends.demand_score_for_product(cfg, product.name)
    demand = max(1, min(10, demand_raw))
    viability = classify_viability(est_margin, demand, comp_level)
    rec_sale = margin_mod.calculate_recommended_price(
        product.source_price_eur, cfg.radar.min_profit_margin
    )
    units = estimated_monthly_units(demand, comp_level)
    notes_parts = [
        f"Target {cfg.radar.target_city}/{cfg.radar.target_market}",
        f"Competitors sampled: {len(competitors)}",
    ]
    return ProductAnalysis(
        product=product,
        competitors=competitors,
        avg_competitor_price=round(avg, 2),
        estimated_margin=round(est_margin, 4),
        demand_score=demand,
        competition_level=comp_level,
        viability=viability,
        recommended_sale_price=round(rec_sale, 2),
        estimated_monthly_units=units,
        notes="; ".join(notes_parts),
    )

"""Competition level from Amazon-style results."""

from __future__ import annotations

from src.models import CompetitorData


def competition_level(competitors: list[CompetitorData]) -> str:
    n = len(competitors)
    if n == 0:
        return "low"
    total_reviews = sum(c.num_reviews for c in competitors)
    if n >= 4 and total_reviews > 500:
        return "high"
    if n >= 2 or total_reviews > 100:
        return "medium"
    return "low"
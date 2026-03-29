"""CSV export for viable (and optional marginal) products."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.config import AppConfig
from src.models import ProductAnalysis, ViabilityStatus


def write_csv_export(
    root: Path,
    cfg: AppConfig,
    analyses: list[ProductAnalysis],
    run_date: date,
    include_marginal: bool = True,
) -> Path:
    rows: list[ProductAnalysis] = [
        a for a in analyses if a.viability == ViabilityStatus.VIABLE
    ]
    if include_marginal:
        rows.extend(a for a in analyses if a.viability == ViabilityStatus.MARGINAL)
    path = root / "reports" / f"{run_date.isoformat()}-export.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "name",
                "source",
                "source_url",
                "source_price_eur",
                "recommended_sale_eur",
                "margin",
                "demand",
                "competition",
                "viability",
                "category",
                "notes",
            ]
        )
        for a in rows:
            w.writerow(
                [
                    a.product.name,
                    a.product.source,
                    a.product.source_url,
                    a.product.source_price_eur,
                    a.recommended_sale_price,
                    a.estimated_margin,
                    a.demand_score,
                    a.competition_level,
                    a.viability.value,
                    a.product.category,
                    a.notes,
                ]
            )
    return path
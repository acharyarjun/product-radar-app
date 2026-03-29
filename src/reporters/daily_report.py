"""Daily Markdown report."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from src.config import AppConfig
from src.models import ProductAnalysis, ViabilityStatus


def _pct(m: float) -> str:
    return f"{m * 100:.1f}%"


def _comp_es(level: str) -> str:
    return {"low": "Baja", "medium": "Media", "high": "Alta"}.get(level, level)


def build_markdown(cfg: AppConfig, analyses: list[ProductAnalysis], run_date: date) -> str:
    viable = [a for a in analyses if a.viability == ViabilityStatus.VIABLE]
    marginal = [a for a in analyses if a.viability == ViabilityStatus.MARGINAL]
    scanned = len(analyses)
    avg_margin = sum(a.estimated_margin for a in viable) / len(viable) if viable else 0.0
    top_cat = ""
    if viable:
        cats: dict[str, int] = {}
        for a in viable:
            cats[a.product.category] = cats.get(a.product.category, 0) + 1
        top_cat = max(cats, key=cats.get)

    lines = [
        f"# Product Radar - Informe Diario {run_date.isoformat()}",
        "",
        "## Resumen",
        f"- Productos escaneados: {scanned}",
        f"- Productos viables: {len(viable)}",
        f"- Margen medio (viables): {_pct(avg_margin)}",
        f"- Top categoria: {top_cat or 'n/a'}",
        "",
        "## Productos Viables",
        "",
        "| # | Producto | Precio Origen | Precio Venta Est. | Margen | Demanda | Competencia | Link |",
        "|---|----------|---------------|-------------------|--------|---------|-------------|------|",
    ]
    for i, a in enumerate(viable, 1):
        lines.append(
            f"| {i} | {a.product.name[:40]} | {a.product.source_price_eur} EUR | "
            f"{a.recommended_sale_price} EUR | {_pct(a.estimated_margin)} | "
            f"{a.demand_score}/10 | {_comp_es(a.competition_level)} | {a.product.source_url} |"
        )
    lines += ["", "## Productos Marginales", ""]
    lines += [
        "| # | Producto | Precio Origen | Precio Venta Est. | Margen | Demanda | Competencia | Link |",
        "|---|----------|---------------|-------------------|--------|---------|-------------|------|",
    ]
    for i, a in enumerate(marginal, 1):
        lines.append(
            f"| {i} | {a.product.name[:40]} | {a.product.source_price_eur} EUR | "
            f"{a.recommended_sale_price} EUR | {_pct(a.estimated_margin)} | "
            f"{a.demand_score}/10 | {_comp_es(a.competition_level)} | {a.product.source_url} |"
        )
    lines += [
        "",
        "## Notas",
        f"- Mercado objetivo: {cfg.radar.target_city}, {cfg.radar.target_market}",
        "- Agente automatico; validar precios y stock antes de comprar.",
    ]
    return "\n".join(lines) + "\n"


def write_daily_report(root: Path, cfg: AppConfig, analyses: list[ProductAnalysis], run_date: date) -> Path:
    out = root / "reports" / f"{run_date.isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_markdown(cfg, analyses, run_date), encoding="utf-8")
    return out
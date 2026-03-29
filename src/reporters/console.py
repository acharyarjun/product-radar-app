"""Rich console summary."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from src.models import ProductAnalysis, ViabilityStatus


def print_summary(analyses: list[ProductAnalysis]) -> None:
    con = Console()
    viable = [a for a in analyses if a.viability == ViabilityStatus.VIABLE]
    mar = [a for a in analyses if a.viability == ViabilityStatus.MARGINAL]
    con.print("[bold]Product Radar[/bold] — run complete")
    con.print(f"  Viable: {len(viable)}  Marginal: {len(mar)}  Total analyzed: {len(analyses)}")
    if not viable:
        return
    t = Table(title="Top viable")
    t.add_column("Product")
    t.add_column("Margin", justify="right")
    t.add_column("Demand", justify="right")
    t.add_column("Source EUR", justify="right")
    for a in viable[:15]:
        t.add_row(
            a.product.name[:50],
            f"{a.estimated_margin * 100:.0f}%",
            str(a.demand_score),
            f"{a.product.source_price_eur:.2f}",
        )
    con.print(t)
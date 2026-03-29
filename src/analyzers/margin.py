"""Margin and recommended sale price."""

from __future__ import annotations


def calculate_margin(source_price: float, sale_price: float) -> float:
    if sale_price <= 0:
        return 0.0
    return (sale_price - source_price) / sale_price


def calculate_recommended_price(source_price: float, min_margin: float = 0.50) -> float:
    if min_margin >= 1:
        return source_price * 2
    return source_price / (1.0 - min_margin)
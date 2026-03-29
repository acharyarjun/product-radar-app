"""Demand score wrapper (trends live in scrapers)."""

from __future__ import annotations


def normalize_demand(raw: int) -> int:
    return max(1, min(10, int(raw)))
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ViabilityStatus(str, Enum):
    VIABLE = "viable"
    MARGINAL = "marginal"
    NOT_VIABLE = "not_viable"


class Product(BaseModel):
    name: str
    source: str
    source_url: str
    source_price_eur: float
    category: str
    image_url: str | None = None
    discovered_at: datetime = Field(default_factory=datetime.now)


class CompetitorData(BaseModel):
    platform: str
    price_eur: float
    seller_name: str
    url: str
    num_reviews: int = 0
    rating: float = 0.0


class ProductAnalysis(BaseModel):
    product: Product
    competitors: list[CompetitorData]
    avg_competitor_price: float
    estimated_margin: float
    demand_score: int
    competition_level: str
    viability: ViabilityStatus
    recommended_sale_price: float
    estimated_monthly_units: int
    notes: str = ""
    analyzed_at: datetime = Field(default_factory=datetime.now)

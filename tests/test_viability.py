import pytest

from src.analyzers.viability import classify_viability
from src.models import ViabilityStatus


def test_viable_high_demand():
    assert classify_viability(0.55, 7, "low") == ViabilityStatus.VIABLE


def test_high_competition_becomes_marginal_not_viable():
    assert classify_viability(0.55, 8, "high") == ViabilityStatus.MARGINAL


def test_marginal_medium_comp():
    assert classify_viability(0.50, 4, "medium") == ViabilityStatus.MARGINAL


def test_marginal_demand_five():
    assert classify_viability(0.50, 5, "low") == ViabilityStatus.MARGINAL


def test_not_viable_low_margin():
    assert classify_viability(0.40, 9, "low") == ViabilityStatus.NOT_VIABLE


def test_not_viable_low_demand_high_comp():
    assert classify_viability(0.50, 4, "high") == ViabilityStatus.NOT_VIABLE
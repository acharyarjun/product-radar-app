import pytest

from src.analyzers import margin


def test_calculate_margin_basic():
    assert margin.calculate_margin(10.0, 20.0) == pytest.approx(0.5)


def test_calculate_margin_zero_sale():
    assert margin.calculate_margin(10.0, 0.0) == 0.0


def test_recommended_price():
    p = margin.calculate_recommended_price(50.0, 0.5)
    assert p == pytest.approx(100.0)
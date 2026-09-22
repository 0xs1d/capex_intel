from datetime import date

import polars as pl
import pytest

from capex_intelligence.features import build_model_ready, build_monthly_signals


def test_monthly_signals_calculate_asp_and_market_benchmark() -> None:
    tx = pl.DataFrame({
        "transaction_date": [date(2024, 1, 1), date(2024, 1, 1)],
        "product_id": ["A", "B"], "market_id": ["M", "M"],
        "units": [10, 10], "net_sales": [100.0, 200.0],
    })
    result = build_monthly_signals(tx.lazy()).collect().sort("product_id")
    assert result["asp"].to_list() == [10.0, 20.0]
    assert result["market_asp"].to_list() == [15.0, 15.0]
    assert result["asp_vs_market_pct"].to_list() == pytest.approx([-(1 / 3), 1 / 3])


def test_model_ready_target_is_next_month_only() -> None:
    tx = pl.DataFrame({
        "transaction_date": [date(2024, 1, 1), date(2024, 2, 1)],
        "product_id": ["A", "A"], "market_id": ["M", "M"],
        "units": [10, 20], "net_sales": [100.0, 240.0],
    })
    products = pl.DataFrame({
        "product_id": ["A"], "product_family": ["Imaging"],
        "equipment_type": ["CT"], "launch_date": [date(2023, 1, 1)],
    })
    result = build_model_ready(build_monthly_signals(tx.lazy()), products.lazy()).collect().sort("month")
    assert result["target_volume_next_month"].to_list() == [20, None]
    assert result["product_family"].to_list() == ["Imaging", "Imaging"]

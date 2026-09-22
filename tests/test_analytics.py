from datetime import date

import polars as pl

from capex_intelligence.analytics import run_analytics


def test_analytics_publishes_trends_and_metrics(tmp_path) -> None:
    months = [date(2024, month, 1) for month in range(1, 7)]
    signals = pl.DataFrame({
        "month": months,
        "product_id": ["A"] * 6,
        "market_id": ["M"] * 6,
        "equipment_type": ["CT"] * 6,
        "asp": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        "volume_units": [10] * 6,
        "net_sales": [1_000.0, 1_010.0, 1_020.0, 1_030.0, 1_040.0, 1_050.0],
    })
    summary = run_analytics(signals, tmp_path)
    assert summary["sku_count"] == 1
    assert (tmp_path / "analytics" / "metrics.json").exists()
    assert pl.read_parquet(tmp_path / "analytics" / "asp_trends.parquet")["asp_trend"].item() == "rising"

"""Robust commercial analytics: ASP anomaly detection, trend scoring, and KPI marts."""

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl


def _robust_features(signals: pl.DataFrame) -> pl.DataFrame:
    keys = ["product_id", "market_id"]
    peer_keys = ["month", "market_id", "equipment_type"] if "equipment_type" in signals.columns else ["month", "market_id"]
    return (
        signals.sort(keys + ["month"])
        .with_columns(
            pl.col("asp").rolling_median(window_size=6, min_samples=3).over(keys).alias("asp_rolling_median"),
        )
        .with_columns(
            (pl.col("asp") - pl.col("asp_rolling_median")).abs().alias("asp_abs_deviation"),
        )
        .with_columns(
            pl.col("asp_abs_deviation")
            .rolling_median(window_size=6, min_samples=3)
            .over(keys)
            .alias("asp_rolling_mad"),
            pl.col("asp").median().over(peer_keys).alias("peer_asp_median"),
            (pl.col("asp") - pl.col("asp").median().over(peer_keys)).abs()
            .median()
            .over(peer_keys)
            .alias("peer_asp_mad"),
        )
        .with_columns(
            ((pl.col("asp") - pl.col("asp_rolling_median")) / (1.4826 * pl.col("asp_rolling_mad").clip(lower_bound=1.0))).alias("temporal_robust_z"),
            ((pl.col("asp") - pl.col("peer_asp_median")) / (1.4826 * pl.col("peer_asp_mad").clip(lower_bound=1.0))).alias("peer_robust_z"),
        )
        .with_columns(
            (pl.col("temporal_robust_z").abs() >= 3.5).alias("temporal_outlier"),
            (pl.col("peer_robust_z").abs() >= 3.5).alias("peer_outlier"),
        )
        .with_columns(
            (pl.col("temporal_outlier") | pl.col("peer_outlier")).alias("asp_outlier"),
            pl.when(pl.col("temporal_outlier") & pl.col("peer_outlier")).then(pl.lit("temporal_and_peer"))
            .when(pl.col("temporal_outlier")).then(pl.lit("temporal_shift"))
            .when(pl.col("peer_outlier")).then(pl.lit("peer_price_gap"))
            .otherwise(pl.lit("in_range")).alias("outlier_reason"),
        )
    )


def _trend_table(signals: pl.DataFrame) -> pl.DataFrame:
    frame = signals.with_columns(
        ((pl.col("month").dt.year() * 12 + pl.col("month").dt.month()).cast(pl.Float64)).alias("month_index")
    ).with_columns(
        pl.col("month_index").mean().over(["product_id", "market_id"]).alias("x_mean"),
        pl.col("asp").mean().over(["product_id", "market_id"]).alias("y_mean"),
        pl.col("volume_units").mean().over(["product_id", "market_id"]).alias("v_mean"),
    ).with_columns(
        ((pl.col("month_index") - pl.col("x_mean")) * (pl.col("asp") - pl.col("y_mean"))).alias("xy_dev"),
        ((pl.col("month_index") - pl.col("x_mean")) ** 2).alias("x_dev_sq"),
        ((pl.col("month_index") - pl.col("x_mean")) * (pl.col("volume_units") - pl.col("v_mean"))).alias("xv_dev"),
    )
    return (
        frame.group_by(["product_id", "market_id"])
        .agg(
            pl.len().alias("months_observed"),
            pl.col("asp").first().alias("asp_start"),
            pl.col("asp").last().alias("asp_end"),
            (pl.col("xy_dev").sum() / pl.col("x_dev_sq").sum()).alias("asp_monthly_slope"),
            (pl.col("xv_dev").sum() / pl.col("x_dev_sq").sum()).alias("volume_monthly_slope"),
        )
        .with_columns(
            (pl.col("asp_end") / pl.col("asp_start") - 1).alias("asp_total_change_pct"),
            (pl.col("asp_monthly_slope") / pl.col("asp_start")).alias("asp_monthly_slope_pct"),
        )
        .with_columns(
            pl.when(pl.col("asp_monthly_slope_pct") > 0.005).then(pl.lit("rising"))
            .when(pl.col("asp_monthly_slope_pct") < -0.005).then(pl.lit("falling"))
            .otherwise(pl.lit("stable")).alias("asp_trend"),
        )
        .sort("asp_total_change_pct", descending=True)
    )


def run_analytics(signals: pl.DataFrame, output_root: Path) -> dict[str, object]:
    """Write anomaly/trend marts and a recruiter-ready metrics summary."""
    robust = _robust_features(signals)
    trends = _trend_table(signals)
    analytics_dir = output_root / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    robust.filter(pl.col("asp_outlier")).write_parquet(analytics_dir / "asp_outliers.parquet", compression="zstd")
    trends.write_parquet(analytics_dir / "asp_trends.parquet", compression="zstd")
    total_sales = signals["net_sales"].sum()
    outliers = robust.filter(pl.col("asp_outlier"))
    summary: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "signal_rows": signals.height,
        "sku_count": signals["product_id"].n_unique(),
        "market_count": signals["market_id"].n_unique(),
        "total_net_sales": round(float(total_sales), 2),
        "asp_outlier_rows": outliers.height,
        "asp_outlier_rate": round(outliers.height / max(signals.height, 1), 6),
        "outlier_sales_exposure": round(float(outliers["net_sales"].sum() or 0), 2),
        "rising_sku_market_trends": trends.filter(pl.col("asp_trend") == "rising").height,
        "falling_sku_market_trends": trends.filter(pl.col("asp_trend") == "falling").height,
        "stable_sku_market_trends": trends.filter(pl.col("asp_trend") == "stable").height,
    }
    (analytics_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary

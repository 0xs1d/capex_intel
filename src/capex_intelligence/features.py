"""Business features for pricing signals and CAPEX forecasting."""

import polars as pl


def build_monthly_signals(transactions: pl.LazyFrame) -> pl.LazyFrame:
    """Aggregate transaction facts into product-market-month commercial signals."""
    return (
        transactions
        .with_columns(pl.col("transaction_date").dt.truncate("1mo").alias("month"))
        .group_by(["month", "product_id", "market_id"])
        .agg(
            pl.col("units").sum().alias("volume_units"),
            pl.col("net_sales").sum().alias("net_sales"),
        )
        .with_columns(
            (pl.col("net_sales") / pl.col("volume_units")).alias("asp"),
            pl.col("volume_units")
            .sum()
            .over(["month", "market_id"])
            .alias("market_volume_units"),
            pl.col("net_sales").sum().over(["month", "market_id"]).alias("market_sales"),
        )
        .with_columns(
            (pl.col("market_sales") / pl.col("market_volume_units")).alias("market_asp"),
        )
        .with_columns(
            (pl.col("asp") / pl.col("market_asp") - 1).alias("asp_vs_market_pct"),
        )
        .sort(["product_id", "market_id", "month"])
        .with_columns(
            pl.col("asp")
            .pct_change()
            .over(["product_id", "market_id"])
            .alias("asp_mom_pct"),
            pl.col("volume_units")
            .pct_change()
            .over(["product_id", "market_id"])
            .alias("volume_mom_pct"),
            pl.col("asp")
            .rolling_mean(window_size=3)
            .over(["product_id", "market_id"])
            .alias("asp_3m_avg"),
            pl.len().over(["product_id", "market_id"]).alias("history_months"),
        )
    )


def build_model_ready(signals: pl.LazyFrame, products: pl.LazyFrame) -> pl.LazyFrame:
    """Attach product attributes and lagged targets without leaking future observations."""
    return (
        signals.join(products, on="product_id", how="left")
        .with_columns(
            pl.col("volume_units").shift(-1).over(["product_id", "market_id"]).alias("target_volume_next_month"),
            pl.col("asp").shift(-1).over(["product_id", "market_id"]).alias("target_asp_next_month"),
        )
        .filter(pl.col("history_months") >= 1)
    )

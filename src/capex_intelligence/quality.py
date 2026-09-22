"""Data quality checks fail fast before expensive feature calculations."""

import polars as pl

from .schemas import DataQualityReport


def validate_transactions(frame: pl.DataFrame) -> DataQualityReport:
    keys = ["transaction_id"] if "transaction_id" in frame.columns else ["transaction_date", "product_id", "market_id"]
    duplicate_rows = frame.height - frame.select(keys).unique().height
    invalid = frame.filter(
        pl.any_horizontal(
            pl.col("transaction_date").is_null(),
            pl.col("transaction_id").is_null() if "transaction_id" in frame.columns else pl.lit(False),
            pl.col("product_id").is_null(),
            pl.col("market_id").is_null(),
            pl.col("units") <= 0,
            pl.col("net_sales") < 0,
        )
    ).height
    null_rates = {
        name: frame.get_column(name).null_count() / max(frame.height, 1)
        for name in frame.columns
    }
    return DataQualityReport(frame.height, duplicate_rows, null_rates, invalid)


def enforce(report: DataQualityReport, null_rate_threshold: float) -> None:
    too_null = {k: v for k, v in report.null_rate_by_column.items() if v > null_rate_threshold}
    if not report.passed or too_null:
        raise ValueError(
            f"Input quality checks failed: invalid_rows={report.invalid_rows}, "
            f"duplicate_rows={report.duplicate_rows}, null_rates={too_null}"
        )

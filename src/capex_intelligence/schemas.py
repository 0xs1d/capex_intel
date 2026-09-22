"""Canonical column contracts used at pipeline boundaries."""

from dataclasses import dataclass

import polars as pl

TRANSACTION_COLUMNS = {
    "transaction_date": pl.Date,
    "product_id": pl.String,
    "market_id": pl.String,
    "units": pl.Int64,
    "net_sales": pl.Float64,
}

PRODUCT_COLUMNS = {
    "product_id": pl.String,
    "product_family": pl.String,
    "equipment_type": pl.String,
    "launch_date": pl.Date,
}


@dataclass(frozen=True)
class DataQualityReport:
    """Small serializable quality summary emitted with each run."""

    rows: int
    duplicate_rows: int
    null_rate_by_column: dict[str, float]
    invalid_rows: int

    @property
    def passed(self) -> bool:
        return self.invalid_rows == 0 and self.duplicate_rows == 0

"""Bronze/Silver/Gold table builders."""

import json
from pathlib import Path

import polars as pl

from .features import build_model_ready, build_monthly_signals
from .io import read_products, read_transactions, write_parquet
from .quality import enforce, validate_transactions


def build_bronze(transactions: Path, products: Path, root: Path) -> tuple[Path, Path]:
    """Persist immutable source copies and return their paths."""
    bronze = root / "bronze"
    bronze.mkdir(parents=True, exist_ok=True)
    tx_out, product_out = bronze / "transactions.parquet", bronze / "products.parquet"
    read_transactions(transactions).sink_parquet(tx_out, compression="zstd", engine="streaming")
    read_products(products).sink_parquet(product_out, compression="zstd", engine="streaming")
    return tx_out, product_out


def build_silver(bronze_transactions: Path, bronze_products: Path, root: Path, null_threshold: float) -> tuple[pl.DataFrame, pl.LazyFrame]:
    """Clean, deduplicate, and validate source facts before downstream aggregation."""
    raw = read_transactions(bronze_transactions).collect()
    report = validate_transactions(raw)
    enforce(report, null_threshold)
    dedupe_keys = ["transaction_id"] if "transaction_id" in raw.columns else ["transaction_date", "product_id", "market_id"]
    cleaned = raw.unique(subset=dedupe_keys, keep="last")
    silver = root / "silver"
    write_parquet(cleaned, silver / "transactions_clean.parquet")
    products = read_products(bronze_products)
    write_parquet(products.collect(), silver / "products_clean.parquet")
    (silver / "quality_report.json").write_text(
        json.dumps(
            {
                "rows": report.rows,
                "duplicate_rows": report.duplicate_rows,
                "invalid_rows": report.invalid_rows,
                "null_rate_by_column": report.null_rate_by_column,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return cleaned, products


def build_gold(silver_transactions: pl.DataFrame, products: pl.LazyFrame, root: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Publish the analytical feature layer and model-ready table."""
    signals = build_monthly_signals(silver_transactions.lazy()).collect()
    model_ready = build_model_ready(signals.lazy(), products).collect()
    gold = root / "gold"
    write_parquet(signals, gold / "monthly_pricing_signals.parquet")
    write_parquet(model_ready, gold / "model_ready_features.parquet")
    return signals, model_ready

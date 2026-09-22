"""Deterministic, vectorized synthetic source generator for scale and demo reproducibility."""

from pathlib import Path

import polars as pl

EQUIPMENT = ["CT", "MRI", "Ultrasound", "X-Ray", "Mammography", "PET"]
FAMILIES = ["Imaging", "Patient Monitoring", "Surgical", "Laboratory", "Radiotherapy", "Dental"]


def _hash(name: str, seed: int) -> pl.Expr:
    return pl.col("row_id").hash(seed=seed).alias(name)


def _label(index: pl.Expr, labels: list[str]) -> pl.Expr:
    expression = pl.lit(labels[-1])
    for position, label in reversed(list(enumerate(labels[:-1]))):
        expression = pl.when(index == position).then(pl.lit(label)).otherwise(expression)
    return expression


def _product_frame(sku_count: int, seed: int) -> pl.LazyFrame:
    return (
        pl.LazyFrame({"sku_num": pl.int_range(0, sku_count, eager=True)})
        .with_columns(
            pl.concat_str([pl.lit("SKU-"), pl.col("sku_num").cast(pl.String).str.zfill(6)]).alias("product_id"),
            _label(pl.col("sku_num").mod(len(FAMILIES)), FAMILIES).alias("product_family"),
            _label(pl.col("sku_num").mod(len(EQUIPMENT)), EQUIPMENT).alias("equipment_type"),
            (pl.date(2021, 1, 1) + pl.duration(days=pl.col("sku_num").mod(1_095))).alias("launch_date"),
        )
        .select(["product_id", "product_family", "equipment_type", "launch_date"])
    )


def generate_dataset(
    output_dir: Path,
    transaction_rows: int = 2_000_000,
    sku_count: int = 10_000,
    market_count: int = 30,
    months: int = 24,
    seed: int = 42,
) -> tuple[Path, Path]:
    """Generate source parquet files without materializing all transactions in Python memory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    products_path = output_dir / "products.parquet"
    transactions_path = output_dir / "transactions.parquet"
    _product_frame(sku_count, seed).sink_parquet(products_path, compression="zstd")

    source = pl.LazyFrame({"row_id": pl.int_range(0, transaction_rows, eager=True)}).with_columns(
        _hash("h1", seed),
        _hash("h2", seed + 1),
        _hash("h3", seed + 2),
        _hash("h4", seed + 3),
        _hash("h5", seed + 4),
    )
    month_idx = pl.col("h1").mod(months)
    month_date = pl.concat_str(
        [
            (2023 + month_idx.floordiv(12)).cast(pl.String),
            pl.lit("-"),
            (month_idx.mod(12) + 1).cast(pl.String).str.zfill(2),
            pl.lit("-01"),
        ]
    ).str.strptime(pl.Date, "%Y-%m-%d")
    sku_num = pl.col("h2").mod(sku_count)
    market_num = pl.col("h3").mod(market_count)
    equipment_num = pl.col("h2").mod(sku_count).mod(len(EQUIPMENT))
    equipment_price = (
        pl.when(equipment_num == 0).then(1_000_000.0)
        .when(equipment_num == 1).then(1_500_000.0)
        .when(equipment_num == 2).then(80_000.0)
        .when(equipment_num == 3).then(180_000.0)
        .when(equipment_num == 4).then(250_000.0)
        .otherwise(900_000.0)
    )
    source = (
        source.with_columns(
            pl.concat_str([pl.lit("TXN-"), pl.col("row_id").cast(pl.String).str.zfill(10)]).alias("transaction_id"),
            pl.concat_str([pl.lit("SKU-"), sku_num.cast(pl.String).str.zfill(6)]).alias("product_id"),
            pl.concat_str([pl.lit("MKT-"), market_num.cast(pl.String).str.zfill(3)]).alias("market_id"),
            month_date.alias("transaction_date"),
            (1 + pl.col("h4").mod(12)).cast(pl.Int64).alias("units"),
            equipment_price.alias("base_price"),
        )
        .with_columns(
            (
                pl.col("base_price")
                * (0.88 + pl.col("h5").cast(pl.Float64) / pl.lit(2**64) * 0.24)
                * (1 + month_idx * 0.004)
                * pl.when(pl.col("h1").mod(1_000) < 2).then(2.2)
                .when(pl.col("h1").mod(1_000) < 5).then(0.35)
                .otherwise(1.0)
            ).alias("asp_simulated"),
        )
        .with_columns((pl.col("asp_simulated") * pl.col("units")).alias("net_sales"))
        .select(["transaction_id", "transaction_date", "product_id", "market_id", "units", "net_sales"])
    )
    source.sink_parquet(transactions_path, compression="zstd", engine="streaming")
    return transactions_path, products_path

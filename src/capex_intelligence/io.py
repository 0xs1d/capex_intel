"""Input/output adapters. CSV is convenient for the demo; parquet is the production path."""

from pathlib import Path

import polars as pl

from .schemas import PRODUCT_COLUMNS, TRANSACTION_COLUMNS


def _scan(path: Path) -> pl.LazyFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Input path does not exist: {path}. "
            "Pass real local paths with --transactions/--products, or use --generate for demo data."
        )
    if path.suffix.lower() == ".parquet":
        return pl.scan_parquet(path)
    if path.suffix.lower() in {".csv", ".tsv"}:
        return pl.scan_csv(path, separator="\t" if path.suffix.lower() == ".tsv" else ",")
    raise ValueError(f"Unsupported input format: {path.suffix}")


def read_transactions(path: Path) -> pl.LazyFrame:
    return _cast_contract(_scan(path), TRANSACTION_COLUMNS)


def read_products(path: Path) -> pl.LazyFrame:
    return _cast_contract(_scan(path), PRODUCT_COLUMNS)


def _cast_contract(frame: pl.LazyFrame, contract: dict[str, pl.DataType]) -> pl.LazyFrame:
    missing = set(contract) - set(frame.collect_schema().names())
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return frame.with_columns([pl.col(name).cast(dtype, strict=False) for name, dtype in contract.items()])


def write_parquet(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path, compression="zstd")

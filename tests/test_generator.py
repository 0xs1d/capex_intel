from pathlib import Path

import polars as pl

from capex_intelligence.generator import generate_dataset


def test_generator_writes_requested_rows_and_stable_ids(tmp_path: Path) -> None:
    transactions, products = generate_dataset(tmp_path, transaction_rows=2_000, sku_count=100, market_count=4, months=6)
    tx = pl.read_parquet(transactions)
    product_frame = pl.read_parquet(products)
    assert tx.height == 2_000
    assert tx["transaction_id"].n_unique() == 2_000
    assert product_frame.height == 100

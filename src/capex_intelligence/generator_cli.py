"""CLI wrapper for generating benchmark data without running analytics."""

import argparse

from .config import PipelineSettings
from .generator import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic medical CAPEX source data")
    parser.add_argument("--output-dir", default="data/generated")
    parser.add_argument("--run-id", default="benchmark")
    parser.add_argument("--transaction-rows", type=int, default=2_000_000)
    parser.add_argument("--sku-count", type=int, default=10_000)
    parser.add_argument("--market-count", type=int, default=30)
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    settings = PipelineSettings(
        source_dir=args.output_dir,
        run_id=args.run_id,
        transaction_rows=args.transaction_rows,
        sku_count=args.sku_count,
        market_count=args.market_count,
        months=args.months,
        seed=args.seed,
    )
    transactions, products = generate_dataset(
        settings.source_dir / settings.run_id,
        settings.transaction_rows,
        settings.sku_count,
        settings.market_count,
        settings.months,
        settings.seed,
    )
    print(f"transactions={transactions}\nproducts={products}")


if __name__ == "__main__":
    main()

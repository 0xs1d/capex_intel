"""Command line entry point."""

import argparse
import logging

from .config import PipelineSettings
from .pipeline import generate, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Build medical CAPEX commercial intelligence features")
    parser.add_argument("--transactions", dest="transactions_path")
    parser.add_argument("--products", dest="products_path")
    parser.add_argument("--output-dir", dest="output_dir")
    parser.add_argument("--source-dir", dest="source_dir")
    parser.add_argument("--run-id", dest="run_id")
    parser.add_argument("--generate", action="store_true", help="generate synthetic source data before running")
    parser.add_argument("--transaction-rows", type=int, dest="transaction_rows")
    parser.add_argument("--sku-count", type=int, dest="sku_count")
    parser.add_argument("--market-count", type=int, dest="market_count")
    parser.add_argument("--months", type=int, dest="months")
    parser.add_argument("--seed", type=int, dest="seed")
    args = parser.parse_args()
    values = {key: value for key, value in vars(args).items() if value is not None and key != "generate"}
    settings = PipelineSettings(**values)
    if args.generate:
        transactions_path, products_path = generate(settings)
        settings = settings.model_copy(
            update={"transactions_path": transactions_path, "products_path": products_path}
        )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        print(run(settings))
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

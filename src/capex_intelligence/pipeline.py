"""Orchestration layer: extract, validate, transform, publish, and audit."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from .analytics import run_analytics
from .config import PipelineSettings
from .generator import generate_dataset
from .medallion import build_bronze, build_gold, build_silver

LOGGER = logging.getLogger(__name__)


def run(settings: PipelineSettings) -> Path:
    started = datetime.now(UTC)
    output = settings.output_dir / settings.run_id
    bronze_transactions, bronze_products = build_bronze(
        settings.transactions_path, settings.products_path, output
    )
    silver_transactions, products = build_silver(
        bronze_transactions, bronze_products, output, settings.null_rate_threshold
    )
    signals, model_ready = build_gold(silver_transactions, products, output)
    metrics = run_analytics(model_ready, output)

    audit = {
        "run_id": settings.run_id,
        "started_at": started.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "input_rows": silver_transactions.height,
        "signal_rows": signals.height,
        "model_ready_rows": model_ready.height,
        "medallion": ["bronze", "silver", "gold", "analytics"],
        "metrics": metrics,
    }
    (output / "run_manifest.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Published %s rows to %s", model_ready.height, output)
    return output


def generate(settings: PipelineSettings) -> tuple[Path, Path]:
    """Generate a scale-configurable source dataset and return transaction/product paths."""
    return generate_dataset(
        settings.source_dir / settings.run_id,
        transaction_rows=settings.transaction_rows,
        sku_count=settings.sku_count,
        market_count=settings.market_count,
        months=settings.months,
        seed=settings.seed,
    )

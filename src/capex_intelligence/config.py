"""Typed configuration loaded from environment variables or a YAML-like mapping."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    """Runtime settings; all paths are resolved relative to the working directory."""

    model_config = SettingsConfigDict(env_prefix="CAPEX_", case_sensitive=False)

    transactions_path: Path = Field(default=Path("data/sample/transactions.csv"))
    products_path: Path = Field(default=Path("data/sample/products.csv"))
    output_dir: Path = Field(default=Path("artifacts"))
    run_id: str = "local"
    source_dir: Path = Field(default=Path("data/generated"))
    transaction_rows: int = Field(default=2_000_000, ge=1_000, le=500_000_000)
    sku_count: int = Field(default=10_000, ge=100, le=5_000_000)
    market_count: int = Field(default=30, ge=2, le=500)
    months: int = Field(default=24, ge=6, le=120)
    seed: int = Field(default=42, ge=0)
    lookback_months: int = Field(default=12, ge=1, le=120)
    min_history_months: int = Field(default=3, ge=1, le=120)
    null_rate_threshold: float = Field(default=0.05, ge=0, le=1)

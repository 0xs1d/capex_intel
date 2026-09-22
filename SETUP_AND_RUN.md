# Setup, Runbook, and Troubleshooting

This document is the copy-paste operating guide for the Medical CAPEX Commercial Intelligence Pipeline.

## 1. What is required

- Python 3.11 or newer.
- [`uv`](https://docs.astral.sh/uv/) installed and available on `PATH`.
- Docker and Docker Compose only if you want the container workflow.

The project does not require Databricks, Spark, PyArrow, a database, or external services for the local demo. Polars handles CSV/Parquet reads and writes.

## 2. First-time local setup

From the project root:

```bash
cd ~/xxx/projectx/capex
uv sync --extra dev
```

If `uv sync` is unavailable in an older `uv` version, use:

```bash
uv venv
uv pip install -e '.[dev]'
```

Verify the installation:

```bash
uv run capex-pipeline --help
uv run capex-generate --help
```

## 3. Run the included small sample

This uses the checked-in CSV files and is useful for a fast functional check:

```bash
uv run capex-pipeline \
  --transactions data/sample/transactions.csv \
  --products data/sample/products.csv \
  --output-dir artifacts \
  --run-id sample
```

Inspect the results:

```bash
cat artifacts/sample/analytics/metrics.json
cat artifacts/sample/silver/quality_report.json
find artifacts/sample -maxdepth 2 -type f -printf '%P\n' | sort
```

## 4. Generate and run the million-row demo

The recommended recruiter/demo command generates deterministic synthetic source data and runs it through the entire Bronze–Silver–Gold and analytics pipeline:

```bash
uv run capex-pipeline \
  --generate \
  --transaction-rows 2000000 \
  --sku-count 10000 \
  --market-count 30 \
  --months 24 \
  --source-dir data/generated \
  --output-dir artifacts \
  --run-id benchmark
```

The source files are written to `data/generated/benchmark/`. The medallion outputs are written to `artifacts/benchmark/`.

Generate source data without running the pipeline:

```bash
uv run capex-generate \
  --output-dir data/generated \
  --run-id large-demo \
  --transaction-rows 10000000 \
  --sku-count 50000 \
  --market-count 50 \
  --months 36
```

Then run it as an input dataset:

```bash
uv run capex-pipeline \
  --transactions data/generated/large-demo/transactions.parquet \
  --products data/generated/large-demo/products.parquet \
  --output-dir artifacts \
  --run-id large-demo
```

## 5. Run with real local data

The original failing example used `/data/transactions/2026-01.parquet` and `/data/reference/products.parquet`. Those are placeholder paths; they must exist on the machine where the command runs. Replace them with actual paths:

```bash
ls -lh /absolute/path/to/transactions-2026-01.parquet
ls -lh /absolute/path/to/products.parquet

uv run capex-pipeline \
  --transactions /absolute/path/to/transactions-2026-01.parquet \
  --products /absolute/path/to/products.parquet \
  --output-dir artifacts \
  --run-id 2026-01
```

CSV is also supported:

```bash
uv run capex-pipeline \
  --transactions /absolute/path/to/transactions.csv \
  --products /absolute/path/to/products.csv \
  --output-dir artifacts \
  --run-id real-csv
```

Required transaction columns:

```text
transaction_date, product_id, market_id, units, net_sales
```

An optional `transaction_id` is recommended for real transaction data. When present, quality checks use it as the uniqueness key so multiple same-day sales for the same product and market remain valid. Required product columns:

```text
product_id, product_family, equipment_type, launch_date
```

Dates must be parseable as ISO dates such as `2026-01-31`. Units must be positive and `net_sales` cannot be negative.

## 6. Test and quality commands

Run the complete test suite:

```bash
uv run --extra dev pytest
```

Run with more detail:

```bash
uv run --extra dev pytest -vv
```

Run linting:

```bash
uv run ruff check src tests
```

Run both checks together:

```bash
uv run ruff check src tests && uv run --extra dev pytest
```

The tests cover monthly ASP and market benchmarks, leakage-safe next-month targets, quality-gate failures, deterministic generation, and analytics output publication.

## 7. Docker workflow

Build and run the default 2M-row demo:

```bash
docker compose up --build
```

The container writes results to the host `artifacts/` directory. Run a custom size:

```bash
docker build -t medical-capex-commercial-intelligence:local .
docker run --rm \
  -v "$PWD/artifacts:/app/artifacts" \
  -v "$PWD/data/generated:/app/data/generated" \
  medical-capex-commercial-intelligence:local \
  --generate \
  --transaction-rows 10000000 \
  --sku-count 50000 \
  --market-count 50 \
  --run-id large-demo
```

## 8. Outputs and interpretation

Every run writes:

```text
artifacts/<run-id>/
├── bronze/       # typed immutable source copies
├── silver/       # validated facts and quality_report.json
├── gold/         # monthly signals and model-ready features
├── analytics/    # asp_outliers.parquet, asp_trends.parquet, metrics.json
└── run_manifest.json
```

Useful commands:

```bash
cat artifacts/benchmark/analytics/metrics.json
cat artifacts/benchmark/run_manifest.json
du -sh artifacts/benchmark data/generated/benchmark
```

The synthetic dollar totals and outlier sales exposure are for pipeline demonstration only. They are not production financial estimates.

## 9. Clean generated outputs

Generated data, pipeline artifacts, virtual environments, caches, bytecode, and local build metadata are disposable and ignored by Git. To reset the workspace outputs:

```bash
rm -rf artifacts data/generated .pytest_cache .ruff_cache
find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
find src -maxdepth 1 -type d -name '*.egg-info' -prune -exec rm -rf {} +
```

Do not delete `data/sample`, `src`, `tests`, `configs`, `README.md`, or this runbook.

## 10. Common errors

### `FileNotFoundError: /data/...`

The path is a placeholder or does not exist in the current environment. Use the sample command, use `--generate`, or pass absolute paths verified with `ls -lh`.

### `Input quality checks failed`

Inspect `artifacts/<run-id>/silver/quality_report.json`. Typical causes are null keys, duplicate `transaction_id` values, non-positive units, negative sales, or a null rate above `CAPEX_NULL_RATE_THRESHOLD`.

### `command not found: uv`

Install `uv` using the official installation method, restart the shell, and verify with `uv --version`.

### Docker cannot write outputs

Make sure the host directories exist and are writable:

```bash
mkdir -p artifacts data/generated
```

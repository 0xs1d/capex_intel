FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

COPY configs ./configs
COPY data ./data

ENTRYPOINT ["capex-pipeline"]
CMD ["--generate", "--transaction-rows", "2000000", "--sku-count", "10000", "--market-count", "30", "--months", "24", "--output-dir", "/app/artifacts", "--source-dir", "/app/data/generated", "--run-id", "docker-demo"]

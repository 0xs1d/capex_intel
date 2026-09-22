from datetime import date

import polars as pl
import pytest

from capex_intelligence.quality import enforce, validate_transactions


def test_quality_rejects_duplicate_business_keys() -> None:
    frame = pl.DataFrame({
        "transaction_date": [date(2024, 1, 1), date(2024, 1, 1)],
        "product_id": ["A", "A"], "market_id": ["M", "M"],
        "units": [1, 1], "net_sales": [2.0, 2.0],
    })
    report = validate_transactions(frame)
    assert report.duplicate_rows == 1
    with pytest.raises(ValueError, match="duplicate_rows=1"):
        enforce(report, 0.05)

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch
from services.risk_engine import compute_beta_vs_benchmark

@pytest.mark.asyncio
async def test_compute_beta_vs_benchmark_with_malformed_indices():
    # 1. Setup mock equity curve
    equity_curve = [
        {"snapshot_date": "2024-01-01", "nav": 100000},
        {"snapshot_date": "2024-01-02", "nav": 101000},
        {"snapshot_date": "2024-01-03", "nav": 100500},
        {"snapshot_date": "2024-01-04", "nav": 102000},
        {"snapshot_date": "2024-01-05", "nav": 103000},
    ]

    # 2. Setup mock benchmark data with MultiIndex (Date, Ticker) - the offending case
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    multi_index = pd.MultiIndex.from_tuples(
        [(d, "SPY") for d in dates],
        names=["Date", "Ticker"]
    )
    benchmark_series = pd.Series([400, 405, 402, 410, 412], index=multi_index, name="Close")

    # 3. Setup mock benchmark data with tuple-valued single index
    # We use object dtype to force tuples
    tuple_index = pd.Index([(d,) for d in dates], dtype='object')
    benchmark_df_tuples = pd.DataFrame({"close": [400, 405, 402, 410, 412]}, index=tuple_index)

    # 4. Setup mock benchmark data with mixed-tz datetimes
    mixed_tz_dates = [
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2024-01-02", tz="US/Eastern"),
        pd.Timestamp("2024-01-03", tz=None),
        pd.Timestamp("2024-01-04", tz="UTC"),
        pd.Timestamp("2024-01-05", tz="UTC"),
    ]
    benchmark_series_mixed = pd.Series([400, 405, 402, 410, 412], index=mixed_tz_dates, name="Close")

    # Mock get_price_history to return the malformed data
    with patch("services.risk_engine.get_price_history") as mock_get_history:
        # Case 1: MultiIndex
        mock_get_history.return_value = {"SPY": benchmark_series}
        beta = await compute_beta_vs_benchmark(equity_curve, "SPY")
        assert isinstance(beta, float)
        assert not np.isnan(beta)
        print(f"Beta (MultiIndex): {beta}")

        # Case 2: Tuple-valued single index
        mock_get_history.return_value = {"SPY": benchmark_df_tuples}
        beta = await compute_beta_vs_benchmark(equity_curve, "SPY")
        assert isinstance(beta, float)
        assert not np.isnan(beta)
        print(f"Beta (Tuples): {beta}")

        # Case 3: Mixed-tz datetimes
        mock_get_history.return_value = {"SPY": benchmark_series_mixed}
        beta = await compute_beta_vs_benchmark(equity_curve, "SPY")
        assert isinstance(beta, float)
        assert not np.isnan(beta)
        print(f"Beta (Mixed TZ): {beta}")

if __name__ == "__main__":
    pytest.main([__file__])

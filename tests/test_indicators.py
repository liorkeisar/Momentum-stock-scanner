from modules import indicators
import pandas as pd

from tests._helpers import create_price_df


def test_add_indicators_and_compute_breakout():
    df = create_price_df(260)
    df_ind = indicators.add_indicators(df)
    # check important columns exist
    required = ["EMA20", "EMA50", "ATR", "STD20", "MA20", "UpperBB", "LowerBB", "VOL_MA20", "SMA200"]
    for c in required:
        assert c in df_ind.columns

    res = indicators.compute_breakout_decision(df_ind.dropna())
    assert isinstance(res, dict)
    assert "score" in res and "confidence" in res and "components" in res

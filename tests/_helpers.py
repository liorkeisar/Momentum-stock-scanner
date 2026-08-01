import pandas as pd
import numpy as np
from modules.utils import safe_last, is_bad, safe_div


def create_price_df(n=500, start_price=100.0, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq='B')
    # simple random walk for close
    steps = rng.normal(0, 1, size=n).cumsum()
    close = start_price + steps
    high = close + np.abs(rng.normal(0, 1, size=n))
    low = close - np.abs(rng.normal(0, 1, size=n))
    open_ = close + rng.normal(0, 0.5, size=n)
    volume = (rng.integers(1_000_000, 5_000_000, size=n)).astype(float)
    df = pd.DataFrame({'Date': dates, 'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': volume})
    df = df.set_index('Date')
    return df

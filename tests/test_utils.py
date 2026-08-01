import numpy as np
import pandas as pd
from modules.utils import safe_last, is_bad, safe_div


def test_safe_last_and_is_bad():
    ser = pd.Series([1, 2, np.nan])
    assert safe_last(ser) is np.nan or pd.isna(safe_last(ser))
    assert is_bad(None)
    assert is_bad(np.nan)


def test_safe_div():
    assert safe_div(10, 2) == 5
    assert safe_div(10, 0, default=0) == 0
    assert safe_div(None, 2, default=7) == 7

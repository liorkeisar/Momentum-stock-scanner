"""
modules/utils.py
Wyckoff Pro Swing Scanner

פונקציות עזר גנריות: טיפול בטוח ב-NaN/None, חילוקים, ולידציה, ופורמט תצוגה.
משמש כמעט את כל שאר המודולים - אין לו תלות באף מודול אחר בפרויקט.
"""
import numpy as np
import pandas as pd

def safe_last(s):
    """מחזיר את הערך האחרון של Series בצורה בטוחה, כולל טיפול ב-NaN."""
    try:
        if s is None:
            return np.nan
        if hasattr(s, "iloc"):
            if len(s) == 0:
                return np.nan
            return s.iloc[-1]
        return s
    except Exception:
        return np.nan

def is_bad(v):
    """בדיקת NaN/None בטוחה שעובדת גם על float רגיל וגם על numpy - מחליפה את הבאג `x in [0, None, np.nan]`."""
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except Exception:
        return False

def safe_div(a, b, default=1.0):
    """חילוק בטוח שמונע ZeroDivisionError / NaN שקטים."""
    if is_bad(a) or is_bad(b) or b == 0:
        return default
    try:
        return a / b
    except Exception:
        return default

def safe_div_series(numerator, denominator):
    """חילוק בטוח בין שני Series - מחליף מכנה 0/NaN ב-NaN במקום לזרוק שגיאה."""
    try:
        denom = denominator.replace(0, np.nan)
        return numerator / denom
    except Exception:
        return pd.Series(np.nan, index=numerator.index if hasattr(numerator, "index") else None)

def validate_df(df, required_cols=None):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, f"עמודות חסרות: {missing}"
    return True, None

def fmt_compact_number(v):
    try:
        v = float(v)
    except Exception:
        return "—"
    if is_bad(v):
        return "—"
    if abs(v) >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:.0f}"

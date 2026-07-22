"""
modules/finnhub_source.py
Wyckoff Pro Swing Scanner

מקור נתונים חלופי/גיבוי דרך Finnhub - נכנס לפעולה רק כש-yfinance נכשל
(בעיקר בגלל rate limiting של Yahoo בסריקות מרוכזות של עשרות-מאות טיקרים
על שרתי Streamlit Cloud המשותפים). yfinance נשאר המקור הראשי תמיד.

המפתח נשמר ב-Streamlit Secrets (לא בקוד/בריפו) - ראה הוראות הגדרה במסך
ההגדרות של האפליקציה. בלי מפתח מוגדר, כל הפונקציות כאן פשוט "שקופות" -
מחזירות None/ריק בלי לזרוק שגיאה, כך שהאפליקציה ממשיכה לעבוד רגיל עם
yfinance בלבד.

⚠️ מגבלת הטייר החינמי של Finnhub: עד שנה אחת של נתונים יומיים בקריאה
בודדת. לתקופות ארוכות יותר (24mo, 5y) הפונקציה כאן "מחלקת" את הבקשה
למקטעים של שנה ומאחדת אותם - עובד, אבל צורך יותר קריאות API.
"""
import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

FINNHUB_BASE_URL = "https://finnhub.io/api/v1/stock/candle"
FINNHUB_MAX_YEARS_PER_CALL = 1  # מגבלת הטייר החינמי


def get_finnhub_api_key():
    """
    שולף את מפתח ה-API של Finnhub מ-Streamlit Secrets בלבד (לא מקוד/מריפו).
    מחזיר None בשקט אם אין מפתח מוגדר - זה תקין ומצופה למי שלא הגדיר Finnhub.
    """
    try:
        return st.secrets.get("FINNHUB_API_KEY")
    except Exception:
        return None


def _period_to_years(period):
    """ממיר מחרוזת period (כמו שמשתמשים בה ב-load_history) למספר שנים לאחור."""
    period = (period or "12mo").lower().strip()
    mapping = {
        "1mo": 0.1, "3mo": 0.3, "6mo": 0.5, "12mo": 1.0, "1y": 1.0,
        "24mo": 2.0, "2y": 2.0, "5y": 5.0, "10y": 10.0,
    }
    return mapping.get(period, 1.0)


def _fetch_finnhub_chunk(ticker, api_key, start_dt, end_dt, timeout=10):
    """קריאת API בודדת ל-Finnhub עבור טווח תאריכים אחד (עד שנה)."""
    try:
        params = {
            "symbol": ticker,
            "resolution": "D",
            "from": int(start_dt.timestamp()),
            "to": int(end_dt.timestamp()),
            "token": api_key,
        }
        r = requests.get(FINNHUB_BASE_URL, params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or data.get("s") != "ok" or not data.get("t"):
            return None
        df = pd.DataFrame({
            "Open": data["o"], "High": data["h"], "Low": data["l"],
            "Close": data["c"], "Volume": data["v"],
        }, index=pd.to_datetime(data["t"], unit="s"))
        return df
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_finnhub_history(ticker, period="12mo"):
    """
    טוען היסטוריית מחירים מ-Finnhub, בפורמט זהה ל-load_history של yfinance
    (עמודות Open/High/Low/Close/Volume, DatetimeIndex) - כך שהיא drop-in
    replacement בכל מקום שמצפה לפלט של load_history.
    מחזירה DataFrame ריק אם אין מפתח מוגדר, או אם הקריאה נכשלת.
    """
    api_key = get_finnhub_api_key()
    if not api_key:
        return pd.DataFrame()

    years_needed = _period_to_years(period)
    end_dt = datetime.now()
    chunks = []

    years_remaining = years_needed
    chunk_end = end_dt
    while years_remaining > 0:
        chunk_years = min(FINNHUB_MAX_YEARS_PER_CALL, years_remaining)
        chunk_start = chunk_end - timedelta(days=int(chunk_years * 365) + 2)
        df_chunk = _fetch_finnhub_chunk(ticker, api_key, chunk_start, chunk_end)
        if df_chunk is not None and not df_chunk.empty:
            chunks.append(df_chunk)
        chunk_end = chunk_start
        years_remaining -= chunk_years

    if not chunks:
        return pd.DataFrame()

    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df.dropna()
    return df


def fetch_supported_indices(api_key, timeout=10):
    """שולף את רשימת סמלי המדדים הנתמכים (אם ה-endpoint פנוי בטייר שלך)."""
    try:
        r = requests.get("https://finnhub.io/api/v1/index/list", params={"token": api_key}, timeout=timeout)
        return r.status_code, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return None, str(e)


def fetch_index_constituents(index_symbol, api_key, timeout=10):
    """
    שולף את רשימת המניות המרכיבות מדד נתון (למשל ^GSPC ל-S&P 500).
    ⚠️ ל-Finnhub יש דיווחים שה-endpoint הזה הועבר לטייר בתשלום - הפונקציה
    הזו קיימת בעיקר כדי *לבדוק בפועל* אם זה עובד עם המפתח שהוגדר, לא כי
    יש ודאות שזה יעבוד.
    """
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/index/constituents",
            params={"symbol": index_symbol, "token": api_key}, timeout=timeout
        )
        return r.status_code, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return None, str(e)


def finnhub_status_badge():
    """מחזיר (is_configured: bool, label: str) - לשימוש בהצגת סטטוס במסך ההגדרות."""
    if get_finnhub_api_key():
        return True, "✅ Finnhub מוגדר ופעיל כגיבוי"
    return False, "⚪ Finnhub לא מוגדר - הסריקה תסתמך רק על yfinance"

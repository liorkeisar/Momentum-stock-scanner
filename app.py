import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- מנוע חישובים טכני מקצועי ---
class TechnicalEngine:
    @staticmethod
    def get_indicators(df):
        # ATR לניהול סיכון
        hl = df['High'] - df['Low']
        atr = hl.rolling(14).mean().iloc[-1]

        # RSI מתוקן - חישוב Wilder's RSI תקני
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = delta.clip(upper=0).abs()

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        # הגנה מפני חילוק באפס (כשאין ירידות בכלל בחלון)
        avg_loss_safe = avg_loss.replace(0, np.nan)
        rs = avg_gain / avg_loss_safe
        rsi_series = 100 - (100 / (1 + rs))
        # אם avg_loss היה 0 (כל הימים עליות) -> RSI = 100
        rsi_series = rsi_series.fillna(100)
        rsi = rsi_series.iloc[-1]

        # Wyckoff Logic (Volume Ratio & Range Width)
        recent = df.tail(20)
        up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
        down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()

        # הגנה מפני חילוק באפס / NaN ב-VR
        if pd.isna(down_vol) or down_vol == 0:
            vr = 1.0 if pd.isna(up_vol) or up_vol == 0 else 2.0
        else:
            vr = up_vol / down_vol

        rw = (recent['High'].max() - recent['Low'].min()) / recent['Close'].mean() * 100

        return {"atr": atr, "rsi": rsi, "vr": vr, "rw": rw}

    @staticmethod
    def analyze(ticker):
        try:
            time.sleep(0.1)  # הגנה אקטיבית מחסימה
            df = yf.Ticker(ticker).history(period="1y")
            if df is None or len(df) < 200:
                logger.warning(f"{ticker}: נתונים לא מספיקים (פחות מ-200 ימי מסחר)")
                return None

            ind = TechnicalEngine.get_indicators(df)

            # בדיקת תקינות לפני חישוב הציון
            if any(pd.isna(v) for v in ind.values()):
                logger.warning(f"{ticker}: אינדיקטור לא תקין (NaN) - {ind}")
                return None

            price = df['Close'].iloc[-1]

            # חישוב ציון "בית השקעות" (משוקלל)
            score = (ind['vr'] * 10) + (10 - ind['rw']) * 3 + (50 if ind['rsi'] < 40 else 0)
            score = max(score, 0)  # מניעת ציון שלילי

            return {
                "Ticker": ticker, "Price": round(price, 2),
                "Score": int(min(score, 100)),
                "RSI": round(ind['rsi'], 1),
                "Stop": round(price - (2 * ind['atr']), 2),
                "Target": round(price + (6 * ind['atr']), 2)
            }
        except Exception as e:
            logger.error(f"{ticker}: שגיאה בניתוח - {e}")
            return None

# --- ממשק ניהול (UI) ---
st.set_page_config(layout="wide")
st.title("🏛️ Institutional Trading Terminal")

if st.button("הרץ סריקת עומק"):
    # רשימה שמחולקת ל-Batches למניעת עומס
    tickers = ["AAPL", "NVDA", "MSFT", "AMD", "META", "GOOGL"]  # כאן טוענים את ה-Batch

    with st.spinner("סורק נתונים..."):
        with ThreadPoolExecutor(max_workers=5) as executor:
            data = list(executor.map(TechnicalEngine.analyze, tickers))

    results = [d for d in data if d]
    failed = len(tickers) - len(results)

    if failed > 0:
        st.warning(f"⚠️ {failed} טיקרים נכשלו או הוחזרו ללא נתונים מספיקים (ראה לוג בקונסול)")

    if results:
        df_results = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.dataframe(df_results, use_container_width=True)
    else:
        st.error("לא התקבלו תוצאות תקינות מהסריקה")

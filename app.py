import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

# ==========================
# הגדרות כלליות
# ==========================

st.set_page_config(page_title="Breakout Scanner Pro", layout="wide")

DEFAULT_PERIOD = "6mo"
DEFAULT_INTERVAL = "1d"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================
# פונקציות עזר לנתונים
# ==========================

@st.cache_data
def load_data(ticker, period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL):
    df = yf.download(ticker, period=period, interval=interval)
    df.dropna(inplace=True)
    return df


def add_indicators(df):
    df = df.copy()

    # ממוצעים
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # ATR
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift(1))
    low_close = np.abs(df["Low"] - df["Close"].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # בולינגר
    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]

    # קלטנר
    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    # OBV
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()

    # Accumulation/Distribution
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / \
         (df["High"] - df["Low"]).replace(0, 1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()

    # MFI
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0, 1))))

    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


# ==========================
# לוגיקת פריצה + ניקוד
# ==========================

def breakout_score(df):
    df = df.copy()
    score = 0

    # דשדוש 10 ימים
    range10 = (df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]
    if range10.iloc[-1] < 0.03:
        score += 15

    # סטיית תקן נמוכה
    std_now = df["Close"].rolling(20).std().iloc[-1]
    std_mean = df["Close"].rolling(20).std().mean()
    if std_now < std_mean * 0.8:
        score += 10

    # ATR נמוך
    atr_now = df["ATR"].iloc[-1]
    atr_mean = df["ATR"].rolling(20).mean().iloc[-1]
    if atr_now < atr_mean * 0.8:
        score += 10

    # כסף מוסדי
    if df["OBV"].iloc[-1] > df["OBV"].iloc[-10]:
        score += 10
    if df["AD_Cum"].iloc[-1] > df["AD_Cum"].iloc[-10]:
        score += 10
    if df["MFI"].iloc[-1] > 60:
        score += 10
    if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] * 1.3:
        score += 10

    # מומנטום
    if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]:
        score += 10
    if 50 < df["RSI"].iloc[-1] < 60:
        score += 5
    if df["Close"].iloc[-1] > df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        score += 10

    # קרבה לפריצה
    if df["Close"].iloc[-1] > df["High"].rolling(20).max().iloc[-1] * 0.97:
        score += 10
    if (df["High"] - df["Low"]).iloc[-1] < df["ATR"].iloc[-1] * 0.7:
        score += 5

    return score


def detect_breakout_setup(df):
    df = df.copy()

    # דשדוש
    df["Range10"] = df["High"].rolling(10).max() - df["Low"].rolling(10).min()
    df["Range10_pct"] = df["Range10"] / df["Close"]
    sideways = df["Range10_pct"].iloc[-1] < 0.03

    # כסף מוסדי
    institutional_buying = (
        df["AD_Cum"].iloc[-1] > df["AD_Cum"].iloc[-10] and
        df["MFI"].iloc[-1] > 60 and
        df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] * 1.3
    )

    # סקוויז
    squeeze_on = (
        df["UpperBB"].iloc[-1] < df["UpperKC"].iloc[-1] and
        df["LowerBB"].iloc[-1] > df["LowerKC"].iloc[-1]
    )

    # לחץ קונים
    buy_pressure = df["OBV"].iloc[-1] > df["OBV"].iloc[-10]

    # MACD חיובי
    macd_bullish = df["MACD"].iloc[-1] > df["Signal"].iloc[-1]

    return all([sideways, institutional_buying, squeeze_on, buy_pressure, macd_bullish])


# ==========================
# Backtesting לפריצות
# ==========================

def breakout_backtest(df, min_score=60, lookahead_days=10, rr=2.0):
    df = df.copy()
    results = []

    for i in range(40, len(df) - lookahead_days):
        window = df.iloc[:i]
        score = breakout_score(window)

        if score >= min_score and detect_breakout_setup(window):
            entry = df["Close"].iloc[i]
            stop = window["Low"].rolling(10).min().iloc[-1]
            risk = entry - stop
            if risk <= 0:
                continue
            target = entry + risk * rr

            future = df.iloc[i:i + lookahead_days]

            hit_target = (future["High"] >= target).any()
            hit_stop = (future["Low"] <= stop).any()

            if hit_target:
                results.append(rr)
            elif hit_stop:
                results.append(-1)
            else:
                final = future["Close"].iloc[-1]
                results.append((final - entry) / risk)

    if not results:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "avg_r": 0.0,
            "max_drawdown_r": 0.0
        }

    results_series = pd.Series(results)
    wins = (results_series > 0).sum()
    losses = (results_series <= 0).sum()
    win_rate = wins / (wins + losses) * 100
    avg_r = results_series.mean()
    max_dd = results_series.min()

    return {
        "trades": len(results),
        "win_rate": round(win_rate, 2),
        "avg_r": round(avg_r, 2),
        "max_drawdown_r": round(max_dd, 2)
    }


# ==========================
# גרפים מתקדמים
# ==========================

def plot_advanced_chart(df, ticker):
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.45, 0.15, 0.2, 0.2]
    )

    # נרות
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price"
    ), row=1, col=1)

    # בולינגר
    fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="blue"), name="Upper BB"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="blue"), name="Lower BB"), row=1, col=1)

    # קלטנר
    fig.add_trace(go.Scatter(x=df.index, y=df["UpperKC"], line=dict(color="orange"), name="Upper KC"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["LowerKC"], line=dict(color="orange"), name="Lower KC"), row=1, col=1)

    # נפחים
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

    # OBV
    fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV", line=dict(color="purple")), row=3, col=1)

    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="green")), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal", line=dict(color="red")), row=4, col=1)

    fig.update_layout(title=f"Advanced Breakout Chart — {ticker}", height=900)
    return fig


# ==========================
# UI ראשי
# ==========================

st.title("📈 Breakout Scanner Pro — דשדוש, כסף מוסדי, סקוויז, Backtesting")

tickers_input = st.text_area(
    "הכנס רשימת טיקרי מניות (מופרדים בפסיק):",
    value="AAPL, MSFT, NVDA, META, TSLA"
)

min_score = st.slider("מינימום ציון פריצה להצגה:", 0, 100, 60)
run_backtest = st.checkbox("הרץ Backtesting לכל טיקר")

if st.button("הרץ סורק"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    master_list = []
    backtest_results = {}

    progress = st.progress(0)

    for idx, ticker in enumerate(tickers):
        try:
            df = load_data(ticker)
            df = add_indicators(df)

            score = breakout_score(df)
            setup = detect_breakout_setup(df)

            if score >= min_score and setup:
                master_list.append({
                    "Ticker": ticker,
                    "Score": score,
                    "Price": round(float(df["Close"].iloc[-1]), 2),
                    "RVOL": round(float(df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]), 2)
                })

                if run_backtest:
                    stats = breakout_backtest(df, min_score=min_score)
                    backtest_results[ticker] = stats

        except Exception as e:
            logger.warning(f"בעיה עם {ticker}: {e}")
            st.warning(f"בעיה עם {ticker}: {e}")

        progress.progress((idx + 1) / len(tickers))

    if master_list:
        df_results = pd.DataFrame(master_list).sort_values("Score", ascending=False)
        st.subheader("📊 מניות לפני פריצה לפי ניקוד")
        st.dataframe(df_results, use_container_width=True)

        selected_ticker = st.selectbox("בחר טיקר להצגת גרף:", df_results["Ticker"])
        df_sel = add_indicators(load_data(selected_ticker))
        fig = plot_advanced_chart(df_sel, selected_ticker)
        st.plotly_chart(fig, use_container_width=True)

        if run_backtest and backtest_results:
            st.subheader("🧪 Backtesting תוצאות")
            bt_df = pd.DataFrame(backtest_results).T
            bt_df.index.name = "Ticker"
            st.dataframe(bt_df, use_container_width=True)
    else:
        st.info("לא נמצאו מניות שעומדות בתנאים שהגדרת.")

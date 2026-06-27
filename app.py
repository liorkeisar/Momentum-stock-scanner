import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import traceback
import glob
import os

st.set_page_config(page_title="Breakout Scanner Pro", layout="wide")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PERIOD = "6mo"
DEFAULT_INTERVAL = "1d"

# ==========================
# רשימות מדדים מוכנות
# ==========================
SP500 = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","BRK-B","UNH","XOM","JPM","JNJ","V","PG","MA",
    "HD","CVX","ABBV","LLY","PFE","KO","PEP","BAC","COST","MRK","AVGO","TMO","WMT","DIS","CSCO"
]

NASDAQ100 = [
    "AAPL","MSFT","AMZN","NVDA","META","GOOGL","TSLA","PEP","COST","AVGO","ADBE","NFLX","CMCSA",
    "AMD","INTC","QCOM","TXN","AMGN","SBUX","HON","INTU","AMAT","MDLZ","PYPL","BKNG"
]

DOW30 = [
    "AAPL","MSFT","JPM","V","GS","HD","UNH","JNJ","PG","DIS","KO","MCD","IBM","INTC","WMT","CAT",
    "CVX","BA","MMM","AXP","NKE","MRK","TRV","VZ","CSCO","DOW","WBA","HON","AMGN","CRM"
]

RUSSELL2000 = [
    "AAON","ABCB","ABG","ABM","ABR","ABUS","ACAD","ACDC","ACEL","ACGL","ACHC","ACIW","ACLS","ACMR"
]

INDEX_MAP = {
    "S&P 500": SP500,
    "NASDAQ 100": NASDAQ100,
    "Dow Jones 30": DOW30,
    "Russell 2000 (דוגמה חלקית)": RUSSELL2000
}

# ==========================
# פונקציות עזר בטוחות
# ==========================
def safe_last(s):
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

def validate_df(df, required_cols):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return False, f"עמודות חסרות: {missing}"
    return True, None

# ==========================
# טעינת CSV טיקרים
# ==========================
def load_csv_tickers(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        if "Ticker" not in df.columns and "Symbol" not in df.columns:
            st.error("בקובץ חייבת להיות עמודה בשם 'Ticker' או 'Symbol'")
            return []
        col = "Ticker" if "Ticker" in df.columns else "Symbol"
        return df[col].dropna().astype(str).str.upper().tolist()
    except Exception as e:
        st.error(f"בעיה בקריאת הקובץ: {e}")
        return []

def tickers_from_csv_file(path):
    try:
        df = pd.read_csv(path)
        if "Ticker" in df.columns:
            return df["Ticker"].dropna().astype(str).str.upper().tolist()
        if "Symbol" in df.columns:
            return df["Symbol"].dropna().astype(str).str.upper().tolist()
    except Exception:
        pass
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return [name.upper()]

# ==========================
# נתונים ואינדיקטורים
# ==========================
@st.cache_data
def load_data(ticker, period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        logger.warning(f"load_data failed for {ticker}: {e}")
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift(1))
    low_close = np.abs(df["Low"] - df["Close"].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]

    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()

    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / \
         (df["High"] - df["Low"]).replace(0, 1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0, 1))))

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1)
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df

# ==========================
# ניקוד פריצה ובדיקה (בטוחות)
# ==========================
def breakout_score_safe(df):
    required = ["High","Low","Close","Volume","ATR","STD20","OBV","AD_Cum","MFI","MACD","Signal","RSI","EMA20","EMA50"]
    ok, msg = validate_df(df, required)
    if not ok:
        raise ValueError(f"DF לא תקין: {msg}")

    score = 0

    range10 = (df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]
    if safe_last(range10) < 0.03:
        score += 15

    if safe_last(df["STD20"]) < df["STD20"].mean() * 0.8:
        score += 10

    if safe_last(df["ATR"]) < df["ATR"].rolling(20).mean().iloc[-1] * 0.8:
        score += 10

    if safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10)):
        score += 10
    if safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10)):
        score += 10
    if safe_last(df["MFI"]) > 60:
        score += 10
    vol_mean20 = df["Volume"].rolling(20).mean()
    if not np.isnan(safe_last(vol_mean20)) and safe_last(df["Volume"]) > safe_last(vol_mean20) * 1.3:
        score += 10

    if safe_last(df["MACD"]) > safe_last(df["Signal"]):
        score += 10
    rsi_val = safe_last(df["RSI"])
    if not np.isnan(rsi_val) and 50 < rsi_val < 60:
        score += 5
    if safe_last(df["Close"]) > safe_last(df["EMA20"]) > safe_last(df["EMA50"]):
        score += 10

    high20 = df["High"].rolling(20).max()
    if not np.isnan(safe_last(high20)) and safe_last(df["Close"]) > safe_last(high20) * 0.97:
        score += 10
    if (safe_last(df["High"]) - safe_last(df["Low"])) < safe_last(df["ATR"]) * 0.7:
        score += 5

    return score

def detect_breakout_setup_safe(df):
    required = ["High","Low","Close","Volume","UpperBB","LowerBB","UpperKC","LowerKC","AD_Cum","MFI","OBV","MACD","Signal","ATR"]
    ok, msg = validate_df(df, required)
    if not ok:
        raise ValueError(f"DF לא תקין: {msg}")

    sideways = safe_last((df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]) < 0.03

    institutional_buying = (
        safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10)) and
        safe_last(df["MFI"]) > 60 and
        (not np.isnan(safe_last(df["Volume"].rolling(20).mean()))) and
        safe_last(df["Volume"]) > safe_last(df["Volume"].rolling(20).mean()) * 1.3
    )

    squeeze_on = (
        safe_last(df["UpperBB"]) < safe_last(df["UpperKC"]) and
        safe_last(df["LowerBB"]) > safe_last(df["LowerKC"])
    )

    buy_pressure = safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10))
    macd_bullish = safe_last(df["MACD"]) > safe_last(df["Signal"])

    return bool(sideways and institutional_buying and squeeze_on and buy_pressure and macd_bullish)

# ==========================
# Backtesting
# ==========================
def breakout_backtest(df, min_score=60, lookahead_days=10, rr=2.0):
    df = df.copy()
    results = []

    for i in range(40, len(df) - lookahead_days):
        window = df.iloc[:i]
        try:
            score = breakout_score_safe(window)
            setup = detect_breakout_setup_safe(window)
        except Exception:
            continue

        if score >= min_score and setup:
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
        return {"trades": 0, "win_rate": 0, "avg_r": 0, "max_drawdown_r": 0}

    s = pd.Series(results)
    return {
        "trades": len(s),
        "win_rate": round((s > 0).mean() * 100, 2),
        "avg_r": round(s.mean(), 2),
        "max_drawdown_r": round(s.min(), 2)
    }

# ==========================
# גרפים
# ==========================
def plot_advanced_chart(df, ticker):
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.45, 0.15, 0.2, 0.2]
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="blue"), name="Upper BB"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="blue"), name="Lower BB"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["UpperKC"], line=dict(color="orange"), name="Upper KC"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["LowerKC"], line=dict(color="orange"), name="Lower KC"), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV", line=dict(color="purple")), row=3, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="green")), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal", line=dict(color="red")), row=4, col=1)

    fig.update_layout(title=f"Advanced Breakout Chart — {ticker}", height=900)
    return fig

# ==========================
# סריקה עם תמיכה ב־CSV ורשימות מדדים
# ==========================
st.title("📈 Breakout Scanner Pro — גרסה יציבה")

mode = st.radio("בחר מקור טיקרים:", ["הקלדה ידנית", "קובץ CSV", "רשימות מדדים מוכנות"])

tickers = []
if mode == "הקלדה ידנית":
    tickers_input = st.text_area("הכנס טיקרים (מופרדים בפסיק):", "AAPL, MSFT, NVDA")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

elif mode == "קובץ CSV":
    uploaded_file = st.file_uploader("העלה קובץ CSV עם עמודה בשם Ticker או Symbol", type=["csv"])
    if uploaded_file:
        tickers = load_csv_tickers(uploaded_file)

else:
    index_choice = st.selectbox("בחר מדד:", list(INDEX_MAP.keys()))
    tickers = INDEX_MAP[index_choice]

min_score = st.slider("מינימום ציון להצגה:", 0, 100, 60)
run_backtest = st.checkbox("הרץ Backtesting")
run_debug = st.checkbox("הפעל דיבאג מפורט (יעצור על שגיאה)")

if st.button("הרץ סורק"):
    if not tickers:
        st.error("לא נמצאו טיקרים")
        st.stop()

    master_list = []
    backtest_results = {}
    progress = st.progress(0)

    for idx, ticker in enumerate(tickers):
        try:
            st.write(f"בודק {ticker} ...")
            df = load_data(ticker)
            if df is None or df.empty:
                st.warning(f"{ticker} - אין נתונים")
                progress.progress((idx + 1) / len(tickers))
                continue

            df = add_indicators(df)

            # בדיקת עמודות חיוניות
            needed = ["Open","High","Low","Close","Volume","ATR","STD20","UpperBB","LowerBB","UpperKC","LowerKC","OBV","AD_Cum","MFI","MACD","Signal","RSI","EMA20","EMA50"]
            missing = [c for c in needed if c not in df.columns]
            if missing:
                st.warning(f"{ticker} - עמודות חסרות: {missing}")
                progress.progress((idx + 1) / len(tickers))
                continue

            # חישוב score ו-setup עם טיפול בשגיאות
            try:
                score = breakout_score_safe(df)
                st.write(f"{ticker} score = {score}")
            except Exception as e_score:
                st.error(f"{ticker} - שגיאה ב־breakout_score_safe: {e_score}")
                st.text(traceback.format_exc())
                st.text(df.tail().to_string())
                if run_debug:
                    st.stop()
                progress.progress((idx + 1) / len(tickers))
                continue

            try:
                setup = detect_breakout_setup_safe(df)
                st.write(f"{ticker} setup = {setup}")
            except Exception as e_setup:
                st.error(f"{ticker} - שגיאה ב־detect_breakout_setup_safe: {e_setup}")
                st.text(traceback.format_exc())
                st.text(df.tail().to_string())
                if run_debug:
                    st.stop()
                progress.progress((idx + 1) / len(tickers))
                continue

            if score >= min_score and setup:
                rv = np.nan
                try:
                    rv = safe_last(df["Volume"]) / safe_last(df["Volume"].rolling(20).mean())
                except Exception:
                    rv = np.nan
                master_list.append({
                    "Ticker": ticker,
                    "Score": score,
                    "Price": round(float(safe_last(df["Close"])), 2),
                    "RVOL": round(float(rv), 2) if not np.isnan(rv) else np.nan
                })

                if run_backtest:
                    backtest_results[ticker] = breakout_backtest(df, min_score=min_score)

        except Exception as e:
            st.error(f"בעיה כללית עם {ticker}: {e}")
            st.text(traceback.format_exc())
            if run_debug:
                st.stop()

        progress.progress((idx + 1) / len(tickers))

    if master_list:
        df_results = pd.DataFrame(master_list).sort_values("Score", ascending=False)
        st.subheader("📊 מניות לפני פריצה")
        st.dataframe(df_results, use_container_width=True)

        csv_data = df_results.to_csv(index=False).encode("utf-8")
        st.download_button("📥 הורד תוצאות כ־CSV", csv_data, "breakout_results.csv", "text/csv")

        selected = st.selectbox("בחר טיקר לגרף:", df_results["Ticker"])
        df_sel = add_indicators(load_data(selected))
        st.plotly_chart(plot_advanced_chart(df_sel, selected), use_container_width=True)

        if run_backtest and backtest_results:
            st.subheader("🧪 Backtesting")
            st.dataframe(pd.DataFrame(backtest_results).T, use_container_width=True)
    else:
        st.info("לא נמצאו מניות מתאימות.")

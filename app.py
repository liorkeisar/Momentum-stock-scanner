import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob
import traceback

st.set_page_config(page_title="Breakout Scanner Pro", layout="wide")

# ============================================================
# פונקציות עזר בטוחות
# ============================================================

def safe_last(s):
    try:
        if s is None:
            return np.nan
        if hasattr(s, "iloc"):
            if len(s) == 0:
                return np.nan
            return s.iloc[-1]
        return s
    except:
        return np.nan

def validate_df(df, required_cols):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return False, f"עמודות חסרות: {missing}"
    return True, None

# ============================================================
# טעינת נתונים
# ============================================================

@st.cache_data
def load_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        df.dropna(inplace=True)
        return df
    except:
        return pd.DataFrame()

# ============================================================
# טעינת טיקרים מתיקיית CSV
# ============================================================

def load_tickers_from_folder(folder_path):
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_tickers = []

    for f in csv_files:
        try:
            df = pd.read_csv(f)
            if "Ticker" in df.columns:
                tickers = df["Ticker"].dropna().astype(str).str.upper().tolist()
            elif "Symbol" in df.columns:
                tickers = df["Symbol"].dropna().astype(str).str.upper().tolist()
            else:
                base = os.path.basename(f)
                name = os.path.splitext(base)[0]
                tickers = [name.upper()]
            all_tickers.extend(tickers)
        except Exception as e:
            st.warning(f"בעיה בקריאת {f}: {e}")

    return list(dict.fromkeys(all_tickers))  # הסרת כפילויות

# ============================================================
# אינדיקטורים
# ============================================================

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift(1)).abs(),
        (df["Low"] - df["Close"].shift(1)).abs()
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["MA20"] = df["Close"].rolling(20).mean()

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
    pos = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos / neg.replace(0, 1))))

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1)
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12).mean()
    exp2 = df["Close"].ewm(span=26).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    return df

# ============================================================
# ניקוד פריצה
# ============================================================

def breakout_score(df):
    required = ["High","Low","Close","Volume","ATR","STD20","OBV","AD_Cum","MFI","MACD","Signal","RSI","EMA20","EMA50"]
    ok, msg = validate_df(df, required)
    if not ok:
        return 0

    score = 0

    if safe_last((df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]) < 0.03:
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

    vol20 = df["Volume"].rolling(20).mean()
    if safe_last(df["Volume"]) > safe_last(vol20) * 1.3:
        score += 10

    if safe_last(df["MACD"]) > safe_last(df["Signal"]):
        score += 10

    rsi = safe_last(df["RSI"])
    if 50 < rsi < 60:
        score += 5

    if safe_last(df["Close"]) > safe_last(df["EMA20"]) > safe_last(df["EMA50"]):
        score += 10

    high20 = df["High"].rolling(20).max()
    if safe_last(df["Close"]) > safe_last(high20) * 0.97:
        score += 10

    if (safe_last(df["High"]) - safe_last(df["Low"])) < safe_last(df["ATR"]) * 0.7:
        score += 5

    return score

# ============================================================
# זיהוי פריצה
# ============================================================

def detect_breakout(df):
    try:
        sideways = safe_last((df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]) < 0.03
        inst = (
            safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10)) and
            safe_last(df["MFI"]) > 60 and
            safe_last(df["Volume"]) > safe_last(df["Volume"].rolling(20).mean()) * 1.3
        )
        squeeze = (
            safe_last(df["UpperBB"]) < safe_last(df["UpperKC"]) and
            safe_last(df["LowerBB"]) > safe_last(df["LowerKC"])
        )
        obv = safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10))
        macd = safe_last(df["MACD"]) > safe_last(df["Signal"])

        return sideways and inst and squeeze and obv and macd
    except:
        return False

# ============================================================
# גרף
# ============================================================

def plot_chart(df, ticker):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02)

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price"
    ), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal"), row=4, col=1)

    fig.update_layout(height=900, title=f"{ticker} — Breakout Analysis")
    return fig

# ============================================================
# UI
# ============================================================

st.title("📈 Breakout Scanner Pro — גרסה מלאה עם טעינת תיקיות CSV")

mode = st.radio(
    "בחר מקור טיקרים:",
    ["הקלדה ידנית", "קובץ CSV", "תיקיית CSV", "רשימות מדדים מוכנות"]
)

tickers = []

# הקלדה ידנית
if mode == "הקלדה ידנית":
    tickers_input = st.text_area("הכנס טיקרים (מופרדים בפסיק):", "AAPL, MSFT, NVDA")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# קובץ CSV בודד
elif mode == "קובץ CSV":
    uploaded_file = st.file_uploader("העלה קובץ CSV עם עמודה Ticker או Symbol", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        col = "Ticker" if "Ticker" in df.columns else "Symbol"
        tickers = df[col].dropna().astype(str).str.upper().tolist()

# תיקיית CSV
elif mode == "תיקיית CSV":
    folder = st.text_input("הכנס נתיב לתיקיה:")
    if folder and os.path.isdir(folder):
        tickers = load_tickers_from_folder(folder)
        st.success(f"נטענו {len(tickers)} טיקרים מתוך התיקיה")

# רשימות מדדים
else:
    INDEX_MAP = {
        "S&P 500": ["AAPL","MSFT","AMZN","NVDA","GOOGL","META"],
        "NASDAQ 100": ["AAPL","MSFT","AMZN","NVDA","META"],
        "Dow Jones 30": ["AAPL","MSFT","JPM","V","GS"],
    }
    index_choice = st.selectbox("בחר מדד:", list(INDEX_MAP.keys()))
    tickers = INDEX_MAP[index_choice]

min_score = st.slider("מינימום ציון:", 0, 100, 60)

# ============================================================
# הרצת הסורק
# ============================================================

if st.button("הרץ סורק"):
    if not tickers:
        st.error("לא נמצאו טיקרים")
        st.stop()

    results = []

    for t in tickers:
        df = load_data(t)
        if df.empty:
            continue

        df = add_indicators(df)

        score = breakout_score(df)
        setup = detect_breakout(df)

        if score >= min_score and setup:
            results.append({
                "Ticker": t,
                "Score": score,
                "Price": safe_last(df["Close"])
            })

    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.dataframe(df_res)

        selected = st.selectbox("בחר טיקר לגרף:", df_res["Ticker"])
        df_sel = add_indicators(load_data(selected))
        st.plotly_chart(plot_chart(df_sel, selected), use_container_width=True)
    else:
        st.info("לא נמצאו מניות מתאימות.")

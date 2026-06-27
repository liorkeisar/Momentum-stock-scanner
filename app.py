# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob
import traceback
from datetime import datetime

st.set_page_config(page_title="Breakout Scanner Pro — Decision Support", layout="wide")
st.title("📈 Breakout Scanner Pro — כלי תמיכה בהחלטה לפני פריצה")

PORTFOLIO_FILE = 'portfolio.csv'

# -------------------------
# עזרות כלליות
# -------------------------
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

def validate_df(df, required_cols=None):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, f"עמודות חסרות: {missing}"
    return True, None

# -------------------------
# טעינת טיקרים מתיקיה
# -------------------------
def load_tickers_from_folder(folder_path):
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_tickers = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            cols = [c.strip().lower() for c in df.columns]
            if 'ticker' in cols:
                col = [c for c in df.columns if c.strip().lower() == 'ticker'][0]
                all_tickers.extend(df[col].dropna().astype(str).str.upper().tolist())
            elif 'symbol' in cols:
                col = [c for c in df.columns if c.strip().lower() == 'symbol'][0]
                all_tickers.extend(df[col].dropna().astype(str).str.upper().tolist())
            else:
                base = os.path.basename(f)
                name = os.path.splitext(base)[0]
                all_tickers.append(name.upper())
        except Exception as e:
            st.warning(f"בעיה בקריאת {f}: {e}")
    # הסרת כפילויות ושמירה על סדר
    seen = set()
    tickers = []
    for t in all_tickers:
        if t not in seen:
            seen.add(t)
            tickers.append(t)
    return tickers

# -------------------------
# הורדת נתונים והוספת אינדיקטורים
# -------------------------
@st.cache_data
def load_data(ticker, period="6mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    # EMAs
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # ATR
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # Volatility
    df["STD20"] = df["Close"].rolling(20).std()
    df["MA20"] = df["Close"].rolling(20).mean()

    # Bollinger and Keltner
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]
    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    # OBV and AD
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0,1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()

    # MFI
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0,1))))

    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0,1)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # RVOL
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RVOL"] = df["Volume"] / df["VOL_MA20"]

    return df

# -------------------------
# פונקציית ניקוד החלטה
# -------------------------
def score_component(value, low, high, invert=False):
    """ממפה ערך ל-0..100 לפי טווח; invert הופך את הכיוון"""
    try:
        if np.isnan(value):
            return 0
        if low == high:
            return 100 if not invert else 0
        v = (value - low) / (high - low)
        v = max(0.0, min(1.0, v))
        if invert:
            v = 1.0 - v
        return int(round(v * 100))
    except:
        return 0

def compute_decision_score(df):
    """
    מחזיר dict עם רכיבי ניקוד ו-score סופי.
    components: dict של רכיבים 0..100
    score: משוקלל 0..100
    risk: 0..100 (גבוה = יותר סיכון)
    confidence: 0..100
    note: טקסט קצר
    """
    try:
        ok, msg = validate_df(df, ["High","Low","Close","Volume","ATR","STD20","MA20","RVOL","OBV","AD_Cum","MACD","Signal","RSI","EMA20","EMA50"])
        if not ok:
            return {"components":{}, "score":0, "risk":100, "confidence":0, "note":"נתונים חסרים"}

        comps = {}

        # 1. Volatility compression (lower STD20 relative to historical)
        std20 = safe_last(df["STD20"])
        # השוואה לטווח אחוזי: נשתמש ב־rolling של כל היסטוריה
        hist_std = df["STD20"].dropna()
        if len(hist_std) >= 30:
            low_std, high_std = hist_std.quantile(0.05), hist_std.quantile(0.95)
        else:
            low_std, high_std = hist_std.min() if not hist_std.empty else 0, hist_std.max() if not hist_std.empty else 1
        comps['compression'] = score_component(std20, low_std, high_std, invert=True)

        # 2. RVOL (נפח יחסי)
        rvol = safe_last(df["RVOL"])
        comps['rvol'] = score_component(rvol, 0.5, 2.5)  # 0.5..2.5

        # 3. Trend strength (EMA20 > EMA50)
        ema20 = safe_last(df["EMA20"])
        ema50 = safe_last(df["EMA50"])
        trend_ratio = (ema20 / ema50) if ema50 and not np.isnan(ema50) else 1.0
        comps['trend'] = score_component(trend_ratio, 0.95, 1.1)

        # 4. Momentum (MACD > Signal and RSI in healthy zone)
        macd = safe_last(df["MACD"])
        signal = safe_last(df["Signal"])
        macd_diff = macd - signal if not np.isnan(macd) and not np.isnan(signal) else 0
        comps['macd'] = score_component(macd_diff, -1.0, 2.0)
        rsi = safe_last(df["RSI"])
        comps['rsi'] = score_component(rsi, 30, 70)

        # 5. Institutional flow (OBV and AD)
        obv = safe_last(df["OBV"])
        obv_shift = safe_last(df["OBV"].shift(10))
        obv_gain = 1 if (not np.isnan(obv) and not np.isnan(obv_shift) and obv > obv_shift) else 0
        ad = safe_last(df["AD_Cum"])
        ad_shift = safe_last(df["AD_Cum"].shift(10))
        ad_gain = 1 if (not np.isnan(ad) and not np.isnan(ad_shift) and ad > ad_shift) else 0
        comps['institution'] = int(round((obv_gain + ad_gain) / 2 * 100))

        # 6. Squeeze (BB inside KC)
        upperbb = safe_last(df["UpperBB"])
        upperkc = safe_last(df["UpperKC"])
        lowerbb = safe_last(df["LowerBB"])
        lowerkc = safe_last(df["LowerKC"])
        squeeze = 1 if (not np.isnan(upperbb) and not np.isnan(upperkc) and upperbb < upperkc and not np.isnan(lowerbb) and not np.isnan(lowerkc) and lowerbb > lowerkc) else 0
        comps['squeeze'] = 100 if squeeze else 0

        # 7. Proximity to breakout (close to 20-day high)
        high20 = df["High"].rolling(20).max()
        prox = safe_last(df["Close"]) / safe_last(high20) if not np.isnan(safe_last(high20)) and safe_last(high20) != 0 else 0
        comps['proximity'] = score_component(prox, 0.9, 1.02)

        # 8. Liquidity and risk (ATR / Price and avg volume)
        atr = safe_last(df["ATR"])
        price = safe_last(df["Close"])
        atr_pct = (atr / price) if price and not np.isnan(price) and not np.isnan(atr) else 0
        comps['risk'] = score_component(atr_pct, 0.0, 0.05, invert=True)  # lower ATR% => better (higher score)
        vol_ma20 = safe_last(df["VOL_MA20"])
        comps['liquidity'] = score_component(vol_ma20, 10000, 2000000)  # adjust ranges as needed

        # Weights (sum to 1)
        weights = {
            'compression': 0.20,
            'rvol': 0.20,
            'trend': 0.15,
            'macd': 0.08,
            'rsi': 0.07,
            'institution': 0.10,
            'squeeze': 0.05,
            'proximity': 0.10,
            'liquidity': 0.05
        }

        # Compute weighted score
        total = 0.0
        for k,w in weights.items():
            val = comps.get(k, 0)
            total += val * w

        final_score = int(round(total))

        # Confidence: based on number of strong signals
        strong_signals = sum(1 for k in ['compression','rvol','trend','macd','institution','squeeze','proximity'] if comps.get(k,0) >= 70)
        confidence = int(round(min(100, strong_signals / 7 * 100)))

        # Risk metric (higher = more risky)
        risk_metric = int(round((100 - comps['risk']) * 1.0))  # invert risk score to "riskiness"

        # Note generation
        notes = []
        if comps['compression'] >= 70:
            notes.append("דחיסה חזקה")
        if comps['rvol'] >= 70:
            notes.append("נפח תומך")
        if comps['trend'] >= 60:
            notes.append("טרנד עולה")
        if comps['institution'] >= 60:
            notes.append("כסף מוסדי")
        if comps['squeeze'] >= 100:
            notes.append("Squeeze פעיל")
        if prox < 0.95:
            notes.append("מרחק מהפריצה >5%")
        note = ", ".join(notes) if notes else "אין אותות חזקים"

        return {
            "components": comps,
            "score": final_score,
            "risk": risk_metric,
            "confidence": confidence,
            "note": note
        }

    except Exception as e:
        return {"components":{}, "score":0, "risk":100, "confidence":0, "note":f"error: {e}"}

# -------------------------
# גרף מפורט
# -------------------------
def plot_advanced(df, ticker):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        row_heights=[0.5, 0.12, 0.18, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="blue"), name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="lightblue"), name="UpperBB"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="lightblue"), name="LowerBB"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal"), row=4, col=1)
    fig.update_layout(height=900, title=f"{ticker} — Decision Chart")
    return fig

# -------------------------
# UI
# -------------------------
st.sidebar.header("מקורות טיקרים")
mode = st.sidebar.radio("בחר מקור:", ["הקלדה ידנית", "קובץ CSV בודד", "תיקיית CSV", "מדד מובנה"])

tickers = []
if mode == "הקלדה ידנית":
    txt = st.sidebar.text_area("טיקרים (מופרדים בפסיק):", "AAPL, MSFT, NVDA")
    tickers = [t.strip().upper() for t in txt.split(",") if t.strip()]

elif mode == "קובץ CSV בודד":
    uploaded = st.sidebar.file_uploader("העלה CSV עם עמודת Ticker או Symbol", type=["csv"])
    if uploaded:
        dfu = pd.read_csv(uploaded)
        cols = [c.strip().lower() for c in dfu.columns]
        if 'ticker' in cols:
            col = [c for c in dfu.columns if c.strip().lower()=='ticker'][0]
            tickers = dfu[col].dropna().astype(str).str.upper().tolist()
        elif 'symbol' in cols:
            col = [c for c in dfu.columns if c.strip().lower()=='symbol'][0]
            tickers = dfu[col].dropna().astype(str).str.upper().tolist()
        else:
            st.sidebar.error("אין עמודת Ticker/Symbol בקובץ")

elif mode == "תיקיית CSV":
    folder = st.sidebar.text_input("נתיב לתיקיה (מקומי):", ".")
    if folder and os.path.isdir(folder):
        tickers = load_tickers_from_folder(folder)
        st.sidebar.success(f"נטענו {len(tickers)} טיקרים מתיקיה")

else:
    INDEX_MAP = {
        "S&P 500 small sample": ["AAPL","MSFT","AMZN","NVDA","GOOGL","META"],
        "NASDAQ sample": ["AAPL","MSFT","NVDA","AMD","INTC"]
    }
    idx = st.sidebar.selectbox("בחר מדד:", list(INDEX_MAP.keys()))
    tickers = INDEX_MAP[idx]

min_score = st.sidebar.slider("מינימום ציון להצגה:", 0, 100, 60)
max_tickers = st.sidebar.number_input("מקסימום טיקרים לסריקה:", min_value=10, max_value=1000, value=200, step=10)

st.sidebar.markdown("---")
st.sidebar.markdown("**הערה**: זהו כלי תמיכה בלבד, לא ייעוץ השקעות.")

# כפתור הרצה
if st.button("הרץ סורק עם תמיכה בהחלטה"):
    if not tickers:
        st.error("לא נבחרו טיקרים")
        st.stop()

    tickers = tickers[:int(max_tickers)]
    rows = []
    details = {}

    progress = st.progress(0)
    total = len(tickers)

    for i, t in enumerate(tickers):
        try:
            st.write(f"בודק {t} ({i+1}/{total})")
            df = load_data(t)
            if df.empty:
                rows.append({"Ticker": t, "Score": 0, "Price": np.nan, "Confidence": 0, "Risk": 100})
                continue
            df = add_indicators(df)
            res = compute_decision_score(df)
            rows.append({"Ticker": t, "Score": res["score"], "Price": round(float(safe_last(df["Close"])),2) if not np.isnan(safe_last(df["Close"])) else np.nan, "Confidence": res["confidence"], "Risk": res["risk"]})
            details[t] = {"res": res, "df_tail": df.tail(30)}
        except Exception as e:
            rows.append({"Ticker": t, "Score": 0, "Price": np.nan, "Confidence": 0, "Risk": 100})
        progress.progress((i+1)/total)

    df_results = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    st.subheader("תוצאות סריקה")
    st.dataframe(df_results, use_container_width=True)

    # בחירת טיקר להצגה מפורטת
    st.subheader("דוח מפורט לטיקר")
    sel = st.selectbox("בחר טיקר להצגה:", df_results["Ticker"].tolist())
    if sel:
        info = details.get(sel)
        if info:
            res = info["res"]
            st.metric("ציון כולל", res["score"])
            st.metric("ביטחון", res["confidence"])
            st.metric("מדד סיכון", res["risk"])
            st.write("**רכיבי ניקוד**")
            comp_df = pd.DataFrame.from_dict(res["components"], orient="index", columns=["Value"]).sort_values("Value", ascending=False)
            st.table(comp_df)

            st.write("**הערות**")
            st.info(res["note"])

            # גרף
            df_plot = info["df_tail"].copy()
            st.plotly_chart(plot_advanced(df_plot, sel), use_container_width=True)

            # קישורים חיצוניים
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"[Yahoo](https://finance.yahoo.com/quote/{sel})")
            with c2: st.markdown(f"[Finviz](https://finviz.com/quote.ashx?t={sel})")
            with c3: st.markdown(f"[Investing](https://www.investing.com/search/?q={sel})")
            with c4: st.markdown(f"[Webull](https://www.webull.com/quote/{sel})")

            # הוספה לתיק
            if st.button("הוסף לתיק ההשקעות"):
                price = res.get("price", None)
                try:
                    price = round(float(safe_last(info["df_tail"]["Close"])),2)
                except:
                    price = None
                new_row = pd.DataFrame({'Ticker':[sel], 'Date':[datetime.now().strftime('%Y-%m-%d')], 'EntryPrice':[price]})
                header = not os.path.exists(PORTFOLIO_FILE)
                new_row.to_csv(PORTFOLIO_FILE, mode='a', header=header, index=False)
                st.success(f"{sel} נוסף לתיק")

        else:
            st.warning("אין פרטים לטיקר זה")

    # הורדה של התוצאות
    csv_data = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("הורד תוצאות כ־CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")

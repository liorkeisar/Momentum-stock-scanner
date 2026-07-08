# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, timedelta
import traceback
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Optional ML import
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro — עם חיזוי", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף — סורק פריצה משופר + חיזוי")

PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
PREDICTIONS_FILE = 'predictions.csv'

# ============================
# פונקציות עזר בטוחות
# ============================

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

def validate_df(df, required_cols=None):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, f"עמודות חסרות: {missing}"
    return True, None

# ============================
# טעינת טיקרים מקבצי CSV / תיקיה
# ============================

def get_csv_files_in_cwd():
    return [f for f in os.listdir('.') if f.lower().endswith('.csv')]

def tickers_from_csv_file(path):
    try:
        df = pd.read_csv(path)
        cols = [c.strip().lower() for c in df.columns]
        if 'ticker' in cols:
            col = [c for c in df.columns if c.strip().lower() == 'ticker'][0]
            return df[col].dropna().astype(str).str.upper().tolist()
        if 'symbol' in cols:
            col = [c for c in df.columns if c.strip().lower() == 'symbol'][0]
            return df[col].dropna().astype(str).str.upper().tolist()
    except Exception:
        pass
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return [name.upper()]

def load_tickers_from_folder(folder_path):
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_tickers = []
    for f in csv_files:
        try:
            tickers = tickers_from_csv_file(f)
            all_tickers.extend(tickers)
        except Exception as e:
            st.warning(f"בעיה בקריאת {f}: {e}")
    seen = set()
    unique = []
    for t in all_tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique

# ============================
# הורדת נתונים והוספת אינדיקטורים
# ============================

@st.cache_data
def load_history(ticker, period="12mo"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    df["STD20"] = df["Close"].rolling(20).std()
    df["MA20"] = df["Close"].rolling(20).mean()

    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]

    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0,1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0,1))))

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0,1)
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RVOL"] = df["Volume"] / df["VOL_MA20"]

    return df

# ============================
# מנוע החלטה לפני פריצה (כבר קיים)
# ============================

def score_component(value, low, high, invert=False):
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return 0
        if low == high:
            return 100 if not invert else 0
        v = (value - low) / (high - low)
        v = max(0.0, min(1.0, v))
        if invert:
            v = 1.0 - v
        return int(round(v * 100))
    except Exception:
        return 0

def compute_breakout_decision(df):
    ok, msg = validate_df(df, ["High","Low","Close","Volume","EMA20","EMA50","ATR","STD20","OBV","AD_Cum","MACD","Signal","RSI","MA20","UpperBB","LowerBB","UpperKC","LowerKC","VOL_MA20"])
    if not ok:
        return {"score":0, "confidence":0, "risk":100, "components":{}, "note":"נתונים חסרים"}

    comps = {}
    std20 = safe_last(df["STD20"])
    hist_std = df["STD20"].dropna()
    if len(hist_std) >= 30:
        low_std, high_std = hist_std.quantile(0.05), hist_std.quantile(0.95)
    else:
        low_std, high_std = (hist_std.min() if not hist_std.empty else 0), (hist_std.max() if not hist_std.empty else 1)
    comps["compression"] = score_component(std20, low_std, high_std, invert=True)

    vol_ma20 = safe_last(df["VOL_MA20"])
    rvol = safe_last(df["Volume"]) / vol_ma20 if vol_ma20 not in [0, None, np.nan] else 1
    comps["rvol"] = score_component(rvol, 0.5, 3.0)

    ema20, ema50 = safe_last(df["EMA20"]), safe_last(df["EMA50"])
    trend_ratio = ema20 / ema50 if ema50 not in [0, None, np.nan] else 1
    comps["trend"] = score_component(trend_ratio, 0.95, 1.1)

    macd_diff = safe_last(df["MACD"]) - safe_last(df["Signal"])
    comps["macd"] = score_component(macd_diff, -1.0, 2.0)
    comps["rsi"] = score_component(safe_last(df["RSI"]), 40, 70)

    obv_gain = 1 if (safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10))) else 0
    ad_gain = 1 if (safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10))) else 0
    comps["institutional"] = int(round(((obv_gain + ad_gain) / 2) * 100))

    high20 = df["High"].rolling(20).max()
    prox = safe_last(df["Close"]) / safe_last(high20) if safe_last(high20) not in [0, None, np.nan] else 0
    comps["proximity"] = score_component(prox, 0.9, 1.02)

    atr_pct = safe_last(df["ATR"]) / safe_last(df["Close"]) if safe_last(df["Close"]) not in [0, None, np.nan] else 0
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    sq = (
        safe_last(df["UpperBB"]) < safe_last(df["UpperKC"]) and
        safe_last(df["LowerBB"]) > safe_last(df["LowerKC"])
    )
    comps["squeeze"] = 100 if sq else 0

    weights = {
        "compression": 0.20,
        "rvol": 0.20,
        "trend": 0.15,
        "macd": 0.10,
        "rsi": 0.05,
        "institutional": 0.10,
        "proximity": 0.10,
        "squeeze": 0.05,
        "risk": 0.05
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    risk_metric = 100 - comps.get("risk", 0)

    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {
        "score": final_score,
        "confidence": confidence,
        "risk": risk_metric,
        "components": comps,
        "note": note
    }

# ============================
# חיזוי — פונקציות עיקריות
# ============================

def compute_features_for_ml(df, window=20):
    rows = []
    for end in range(window, len(df)-5):
        w = df.iloc[end-window:end]
        feat = {
            "close_last": w["Close"].iloc[-1],
            "std20": w["Close"].rolling(20).std().iloc[-1] if len(w)>=20 else np.nan,
            "rvol": w["Volume"].iloc[-1] / (w["Volume"].rolling(20).mean().iloc[-1] if w["Volume"].rolling(20).mean().iloc[-1] not in [0, np.nan] else 1),
            "ema20_ema50": w["Close"].ewm(span=20, adjust=False).mean().iloc[-1] / (w["Close"].ewm(span=50, adjust=False).mean().iloc[-1] if w["Close"].ewm(span=50, adjust=False).mean().iloc[-1] not in [0, np.nan] else 1),
            "macd_diff": w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
            "rsi": (w["Close"].diff().where(lambda x: x>0, 0).rolling(14).mean().iloc[-1]) if len(w)>=14 else np.nan,
            "atr_pct": (w["High"] - w["Low"]).rolling(14).mean().iloc[-1] / (w["Close"].iloc[-1] if w["Close"].iloc[-1] not in [0, np.nan] else 1),
            "obv": (np.sign(w["Close"].diff()) * w["Volume"]).fillna(0).cumsum().iloc[-1]
        }
        future = df.iloc[end:end+5]
        label = 0
        if not future.empty:
            if future["Close"].max() > w["High"].max() * 1.005:
                label = 1
        feat["label"] = label
        rows.append(feat)
    return pd.DataFrame(rows)

def train_logistic_model(df):
    try:
        feats = compute_features_for_ml(df, window=20)
        feats = feats.dropna()
        if len(feats) < 30 or feats['label'].sum() < 5:
            return None
        X = feats.drop(columns=["label"])
        y = feats["label"]
        if SKLEARN_AVAILABLE:
            model = LogisticRegression(max_iter=200)
            model.fit(X, y)
            return model
        else:
            return None
    except Exception:
        return None

def logistic_predict_probability(model, df):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return None
        last = feats.dropna().iloc[-1].drop(labels=["label"])
        if SKLEARN_AVAILABLE and model is not None:
            prob = model.predict_proba([last.values])[0][1]
            return float(prob)
        else:
            return None
    except Exception:
        return None

def statistical_similarity_prediction(df, tolerance=0.15, lookahead=5):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return {"count":0, "successes":0, "rate":0.0}
        target = feats.dropna().iloc[-1]
        candidates = feats.dropna().iloc[:-1]
        if candidates.empty:
            return {"count":0, "successes":0, "rate":0.0}
        def similar(row):
            try:
                for k in ["std20","rvol","ema20_ema50","macd_diff","rsi"]:
                    if k not in row or k not in target:
                        continue
                    a = float(row[k])
                    b = float(target[k])
                    if b == 0:
                        if abs(a - b) > 1e-6:
                            return False
                        else:
                            continue
                    if abs(a - b) / (abs(b) + 1e-9) > tolerance:
                        return False
                return True
            except Exception:
                return False
        sim = candidates[candidates.apply(similar, axis=1)]
        count = len(sim)
        successes = int(sim['label'].sum()) if 'label' in sim.columns else 0
        rate = (successes / count) if count>0 else 0.0
        return {"count":count, "successes":successes, "rate":float(rate)}
    except Exception:
        return {"count":0, "successes":0, "rate":0.0}

def pattern_detection_vcp_like(df):
    try:
        window = 30
        if len(df) < window:
            return {"match":False, "desc":"לא מספיק נתונים לתבנית"}
        w = df.tail(window)
        highs = w["High"].values
        lows = w["Low"].values
        peaks = [highs[i] for i in range(0, len(highs), max(1, len(highs)//3))]
        troughs = [lows[i] for i in range(0, len(lows), max(1, len(lows)//3))]
        lower_highs = all(peaks[i] > peaks[i+1] for i in range(len(peaks)-1))
        higher_lows = all(troughs[i] < troughs[i+1] for i in range(len(troughs)-1))
        std_vals = w["Close"].rolling(10).std().dropna()
        std_trend = np.polyfit(range(len(std_vals)), std_vals, 1)[0] if len(std_vals)>2 else 0
        compression = std_trend < 0
        match = lower_highs and higher_lows and compression
        desc = []
        if lower_highs: desc.append("Lower highs")
        if higher_lows: desc.append("Higher lows")
        if compression: desc.append("STD יורד (דחיסה)")
        if not desc:
            desc = ["לא נמצאו סימני VCP ברורים"]
        return {"match": bool(match), "desc": "; ".join(desc)}
    except Exception:
        return {"match":False, "desc":"שגיאה בזיהוי תבנית"}

# ============================
# שמירת תחזיות ופעולות מחיקה
# ============================

def save_prediction_record(record):
    try:
        df = pd.DataFrame([record])
        header = not os.path.exists(PREDICTIONS_FILE)
        df.to_csv(PREDICTIONS_FILE, mode='a', header=header, index=False)
        return True
    except Exception:
        return False

def load_predictions():
    if not os.path.exists(PREDICTIONS_FILE):
        return pd.DataFrame(columns=["Ticker","SavedAt","stat_count","stat_successes","stat_rate","pattern_match","pattern_desc","ml_prob"])
    try:
        return pd.read_csv(PREDICTIONS_FILE)
    except Exception:
        return pd.DataFrame(columns=["Ticker","SavedAt","stat_count","stat_successes","stat_rate","pattern_match","pattern_desc","ml_prob"])

def delete_prediction_tickers(tickers):
    if not os.path.exists(PREDICTIONS_FILE):
        return False
    try:
        df = pd.read_csv(PREDICTIONS_FILE)
        df = df[~df['Ticker'].isin(tickers)]
        df.to_csv(PREDICTIONS_FILE, index=False)
        return True
    except Exception:
        return False

def clear_all_predictions():
    if os.path.exists(PREDICTIONS_FILE):
        try:
            os.remove(PREDICTIONS_FILE)
            return True
        except Exception:
            return False
    return True

# ============================
# שמירת תוצאות סריקה (יחיד) ותמיכה במחיקה
# ============================

def save_single_scan_result(record):
    """
    record: dict with keys Ticker, Score, Confidence, Risk, Price, Note, SavedAt
    """
    try:
        df = pd.DataFrame([record])
        header = not os.path.exists(SCAN_RESULTS_FILE)
        df.to_csv(SCAN_RESULTS_FILE, mode='a', header=header, index=False)
        return True
    except Exception:
        return False

def load_saved_scan_results():
    if not os.path.exists(SCAN_RESULTS_FILE):
        return pd.DataFrame(columns=["Ticker","Score","Confidence","Risk","Price","Note","SavedAt"])
    try:
        return pd.read_csv(SCAN_RESULTS_FILE)
    except Exception:
        return pd.DataFrame(columns=["Ticker","Score","Confidence","Risk","Price","Note","SavedAt"])

def delete_saved_scan_tickers(tickers):
    if not os.path.exists(SCAN_RESULTS_FILE):
        return False
    try:
        df = pd.read_csv(SCAN_RESULTS_FILE)
        df = df[~df['Ticker'].isin(tickers)]
        df.to_csv(SCAN_RESULTS_FILE, index=False)
        return True
    except Exception:
        return False

def clear_all_saved_scans():
    if os.path.exists(SCAN_RESULTS_FILE):
        try:
            os.remove(SCAN_RESULTS_FILE)
            return True
        except Exception:
            return False
    return True

# ============================
# גרף מפורט
# ============================

def plot_advanced(df, ticker):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        row_heights=[0.5, 0.12, 0.18, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="blue"), name="MA20"), row=1, col=1)
    if "UpperBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="lightblue"), name="UpperBB"), row=1, col=1)
    if "LowerBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="lightblue"), name="LowerBB"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV"), row=3, col=1)
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"), row=4, col=1)
    if "Signal" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal"), row=4, col=1)
    fig.update_layout(height=900, title=f"{ticker} — Decision Chart")
    return fig

# ============================
# תיק השקעות
# ============================

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    try:
        return pd.read_csv(PORTFOLIO_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df

def show_buttons(ticker):
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"[Yahoo](https://finance.yahoo.com/quote/{ticker})")
    with c2: st.markdown(f"[Finviz](https://finviz.com/quote.ashx?t={ticker})")
    c3, c4 = st.columns(2)
    with c3: st.markdown(f"[Investing](https://www.investing.com/search/?q={ticker})")
    with c4: st.markdown(f"[Webull](https://www.webull.com/quote/{ticker})")

# ============================
# ממשק משתמש — טאבים
# ============================

tab1, tab2, tab3 = st.tabs(["📊 סורק פריצה משופר", "💼 תיק השקעות", "💾 תוצאות שמורות"])

# --- טאב הסורק ---
with tab1:
    st.sidebar.header("מקורות טיקרים לסורק")
    mode = st.sidebar.radio(
        "בחר מקור:",
        ["קובץ CSV בודד", "תיקיית CSV", "רשימת CSV בתיקייה הנוכחית", "הקלדה ידנית"]
    )

    tickers = []

    if mode == "קובץ CSV בודד":
        uploaded = st.sidebar.file_uploader("העלה קובץ CSV עם עמודת Ticker או Symbol", type=["csv"])
        if uploaded:
            try:
                dfu = pd.read_csv(uploaded)
                cols = [c.strip().lower() for c in dfu.columns]
                if 'ticker' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'ticker'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().tolist()
                elif 'symbol' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'symbol'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().tolist()
                else:
                    st.sidebar.error("לא נמצאה עמודת Ticker/Symbol בקובץ")
            except Exception as e:
                st.sidebar.error(f"שגיאה בקריאת הקובץ: {e}")

    elif mode == "תיקיית CSV":
        folder = st.sidebar.text_input("נתיב לתיקיה:", ".")
        if folder and os.path.isdir(folder):
            tickers = load_tickers_from_folder(folder)
            st.sidebar.success(f"נטענו {len(tickers)} טיקרים מהתיקיה")
        elif folder:
            st.sidebar.error("התיקיה לא קיימת")

    elif mode == "רשימת CSV בתיקייה הנוכחית":
        available_lists = get_csv_files_in_cwd()
        if available_lists:
            selected_file = st.sidebar.selectbox("בחר קובץ מהרשימה:", available_lists)
            tickers = tickers_from_csv_file(selected_file)
            st.sidebar.success(f"נטענו {len(tickers)} טיקרים מהקובץ")
        else:
            st.sidebar.info("אין קבצי CSV בתיקייה הנוכחית")

    else:  # הקלדה ידנית
        txt = st.sidebar.text_area("טיקרים (מופרדים בפסיק):", "AAPL, MSFT, NVDA")
        tickers = [t.strip().upper() for t in txt.split(",") if t.strip()]

    min_score = st.sidebar.slider("ציון מינימלי להצגה:", 0, 100, 60)
    max_tickers = st.sidebar.number_input("מקסימום טיקרים לסריקה:", min_value=10, max_value=1000, value=200, step=10)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**הערה**: כלי תמיכה בהחלטה בלבד, לא ייעוץ השקעות.")

    if st.sidebar.button("הרץ סריקת פריצה"):
        if not tickers:
            st.error("לא נבחרו טיקרים")
        else:
            tickers = tickers[:int(max_tickers)]
            results = []
            details = {}
            progress = st.progress(0)
            total = len(tickers)

            for i, ticker in enumerate(tickers):
                try:
                    st.write(f"בודק {ticker} ({i+1}/{total})")
                    df = load_history(ticker, period="12mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100, "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        progress.progress((i+1)/total)
                        continue
                    df = add_indicators(df)
                    res = compute_breakout_decision(df)
                    results.append({
                        "Ticker": ticker,
                        "Score": res["score"],
                        "Confidence": res["confidence"],
                        "Risk": res["risk"],
                        "Price": round(float(safe_last(df["Close"])), 2) if not np.isnan(safe_last(df["Close"])) else np.nan,
                        "Note": res["note"],
                        "SavedAt": ""
                    })
                    details[ticker] = {"res": res, "df_tail": df.tail(120)}
                except Exception as e:
                    results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100, "Price": np.nan, "Note": "שגיאה", "SavedAt": ""})
                progress.progress((i+1)/total)

            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).reset_index(drop=True)
            df_res = df_res[df_res["Score"] >= min_score]

            if df_res.empty:
                st.info("לא נמצאו מניות מתאימות לפי הקריטריונים.")
            else:
                st.subheader("תוצאות סריקה")
                st.dataframe(df_res, use_container_width=True)

                # שמירת תוצאות (אצווה)
                st.divider()
                col_save1, col_save2 = st.columns([3,1])
                with col_save1:
                    save_note = st.text_input("הערה לשמירה (אופציונלי):", "")
                with col_save2:
                    if st.button("שמור תוצאות"):
                        df_to_save = df_res.copy()
                        df_to_save["SavedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if save_note:
                            df_to_save["Note"] = df_to_save["Note"].astype(str) + " | " + save_note
                        header = not os.path.exists(SCAN_RESULTS_FILE)
                        df_to_save.to_csv(SCAN_RESULTS_FILE, mode='a', header=header, index=False)
                        st.success("תוצאות נשמרו בהצלחה")

                st.divider()
                col_select, col_buttons = st.columns([2, 1])
                with col_select:
                    to_view = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].tolist())
                with col_buttons:
                    if st.button("הוסף לתיק ההשקעות 💼"):
                        try:
                            price = df_res[df_res['Ticker'] == to_view]['Price'].values[0]
                        except Exception:
                            price = None
                        new_row = pd.DataFrame({'Ticker': [to_view], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                        new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                        st.success(f"{to_view} נוספה בהצלחה לתיק!")

                # דוח מפורט לטיקר הנבחר + לחצן חיזוי
                st.subheader("דוח מפורט לטיקר")
                sel = to_view
                info = details.get(sel)
                if info:
                    res = info["res"]
                    st.metric("ציון פריצה", res["score"])
                    st.metric("ביטחון", res["confidence"])
                    st.metric("מדד סיכון", res["risk"])
                    st.write("**רכיבי ניקוד**")
                    comp_df = pd.DataFrame.from_dict(res["components"], orient="index", columns=["Value"]).sort_values("Value", ascending=False)
                    st.table(comp_df)
                    st.write("**הערות**")
                    st.info(res["note"])

                    df_plot = info["df_tail"].copy()
                    st.plotly_chart(plot_advanced(df_plot, sel), use_container_width=True)

                    show_buttons(sel)

                    # ---------- לחצן חיזוי ----------
                    st.markdown("---")
                    st.markdown("### 🔮 חיזוי תנועות עבר")
                    colp1, colp2 = st.columns([3,1])
                    with colp1:
                        lookahead = st.selectbox("חלון חיזוי (ימים):", [3,5,7], index=1, key=f"look_{sel}")
                        stat_tol = st.slider("סף דמיון סטטיסטי (אחוזי שונות):", 5, 50, 15, key=f"tol_{sel}")
                    with colp2:
                        if st.button("הרץ חיזוי עבור " + sel, key=f"pred_btn_{sel}"):
                            with st.spinner("מריץ חיזוי..."):
                                try:
                                    # Load full history for robust features
                                    hist_full = load_history(sel, period="24mo")
                                    if hist_full.empty:
                                        st.error("אין היסטוריית מחירים מספקת לחיזוי")
                                    else:
                                        hist_full = add_indicators(hist_full)
                                        # 1) חיזוי סטטיסטי
                                        stat = statistical_similarity_prediction(hist_full, tolerance=stat_tol/100.0, lookahead=lookahead)
                                        # 2) תבניות
                                        pat = pattern_detection_vcp_like(hist_full)
                                        # 3) מודל לוגיסטי
                                        model = train_logistic_model(hist_full)
                                        ml_prob = logistic_predict_probability(model, hist_full)
                                        # fallback heuristic if no model
                                        if ml_prob is None:
                                            comps = res["components"]
                                            wsum = 0
                                            wtot = 0
                                            heur_weights = {"compression":0.25,"rvol":0.25,"trend":0.2,"macd":0.15,"proximity":0.15}
                                            for k,wght in heur_weights.items():
                                                wtot += wght
                                                wsum += comps.get(k,0) * wght
                                            ml_prob = float(min(0.99, max(0.01, wsum / (wtot*100))))
                                        # הצגת תוצאות
                                        st.success("חיזוי הושלם")
                                        st.write("**חיזוי סטטיסטי**")
                                        st.write(f"מספר חלונות דומים בעבר: **{stat['count']}**, הצלחות: **{stat['successes']}**, שיעור הצלחה: **{round(stat['rate']*100,1)}%**")
                                        st.write("**זיהוי תבנית (VCP-like)**")
                                        st.write(f"מצב: **{pat['match']}** — {pat['desc']}")
                                        st.write("**חיזוי הסתברותי (מודל)**")
                                        st.write(f"הסתברות לפריצה בתוך {lookahead} ימים: **{round(ml_prob*100,1)}%**")
                                        # שמירת תחזית
                                        rec = {
                                            "Ticker": sel,
                                            "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "stat_count": stat["count"],
                                            "stat_successes": stat["successes"],
                                            "stat_rate": stat["rate"],
                                            "pattern_match": pat["match"],
                                            "pattern_desc": pat["desc"],
                                            "ml_prob": ml_prob
                                        }
                                        saved = save_prediction_record(rec)
                                        if saved:
                                            st.info("תחזית נשמרה ב־predictions.csv")
                                        # שמירת שורת סריקה יחידה (כדי לאפשר הוספה לתיק גם אחרי חיזוי)
                                        scan_row = {
                                            "Ticker": sel,
                                            "Score": res["score"],
                                            "Confidence": res["confidence"],
                                            "Risk": res["risk"],
                                            "Price": round(float(safe_last(hist_full["Close"])), 2) if not np.isnan(safe_last(hist_full["Close"])) else np.nan,
                                            "Note": res["note"] + " | prediction",
                                            "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }
                                        saved_scan = save_single_scan_result(scan_row)
                                        if saved_scan:
                                            st.info("שורת סריקה נשמרה ב־scan_results.csv (ניתן להוסיף לתיק)")
                                        else:
                                            st.warning("לא הצלחנו לשמור את שורת הסריקה")
                                except Exception as e:
                                    st.error(f"שגיאה בהרצת חיזוי: {e}")
                    # כפתור להוספה לתיק ישירות מתוך דוח החיזוי/סריקה
                    st.markdown("---")
                    add_col1, add_col2 = st.columns([3,1])
                    with add_col1:
                        st.write("הוספה מהירה לתיק ההשקעות")
                    with add_col2:
                        if st.button("הוסף לתיק מהדוח", key=f"add_from_report_{sel}"):
                            try:
                                hist_full = load_history(sel, period="12mo")
                                price = round(float(safe_last(hist_full["Close"])), 2) if not hist_full.empty else None
                                new_row = pd.DataFrame({'Ticker': [sel], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                                new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                                st.success(f"{sel} נוספה בהצלחה לתיק!")
                            except Exception as e:
                                st.error(f"שגיאה בהוספה לתיק: {e}")
                else:
                    st.warning("אין פרטים לטיקר זה")

                # הורדה של התוצאות
                csv_data = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("הורד תוצאות כ־CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")

# --- טאב תיק ההשקעות ---
with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        # עדכון מחירים וביצועים
        for i, row in portfolio.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                portfolio.loc[i, 'Performance'] = f"{round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)}%"
            except Exception:
                portfolio.loc[i, 'CurrentPrice'] = np.nan
                portfolio.loc[i, 'Performance'] = "N/A"

        st.dataframe(portfolio, use_container_width=True)

        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())

        show_buttons(to_manage)

        # כפתור מחיקה יחיד (מחק מניה מהתיק)
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_manage} הוסר מהתיק")
            st.experimental_rerun()

        # כפתור הוספה מהירה (למקרה רוצים להוסיף ידנית)
        if st.button("הוסף מניה חדשה לתיק"):
            new_t = st.text_input("הזן טיקר להוספה:", key="manual_add_ticker")
            # note: input appears only after click; handle via rerun pattern is complex — keep simple: show instruction
            st.info("להוספה מהירה: השתמש בסריקה או בדוח החיזוי (כפתור 'הוסף לתיק מהדוח').")

    else:
        st.info("התיק ריק.")

# --- טאב תחזיות שמורות ---
with tab3:
    st.header("תחזיות שמורות")
    preds = load_predictions()
    if preds.empty:
        st.info("אין תחזיות שמורות כרגע.")
    else:
        st.dataframe(preds, use_container_width=True)
        st.divider()
        col_del1, col_del2 = st.columns([3,1])
        with col_del1:
            to_delete = st.multiselect("בחר טיקרים למחיקה מהתחזיות השמורות:", options=sorted(preds['Ticker'].unique().tolist()))
        with col_del2:
            if st.button("מחק נבחרים"):
                if not to_delete:
                    st.warning("לא נבחרו טיקרים למחיקה")
                else:
                    ok = delete_prediction_tickers(to_delete)
                    if ok:
                        st.success("התחזיות נמחקו")
                        st.experimental_rerun()
                    else:
                        st.error("שגיאה במחיקה")
        st.divider()
        if st.button("נקה את כל התחזיות השמורות"):
            ok = clear_all_predictions()
            if ok:
                st.success("כל התחזיות נמחקו")
                st.experimental_rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")
        csv_all = preds.to_csv(index=False).encode('utf-8')
        st.download_button("הורד את כל התחזיות כ־CSV", csv_all, file_name="saved_predictions.csv", mime="text/csv")

    # בנוסף: אפשרות להוסיף טיקר מהתחזיות ישירות לתיק
    st.markdown("---")
    st.subheader("הוספה מהתחזיות לתיק ההשקעות")
    saved_preds = preds['Ticker'].unique().tolist() if not preds.empty else []
    if saved_preds:
        pick = st.selectbox("בחר טיקר להוספה לתיק:", saved_preds)
        if st.button("הוסף את הטיקר הנבחר לתיק"):
            try:
                hist_full = load_history(pick, period="12mo")
                price = round(float(safe_last(hist_full["Close"])), 2) if not hist_full.empty else None
                new_row = pd.DataFrame({'Ticker': [pick], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success(f"{pick} נוספה בהצלחה לתיק!")
            except Exception as e:
                st.error(f"שגיאה בהוספה לתיק: {e}")

# ============================
# טאב ניהול תוצאות סריקה שמורות (נפרד)
# ============================
st.sidebar.markdown("---")
if st.sidebar.button("נהל תוצאות שמורות"):
    st.sidebar.write("ניהול תוצאות שמורות")
    saved_scans = load_saved_scan_results()
    if saved_scans.empty:
        st.sidebar.info("אין תוצאות סריקה שמורות")
    else:
        st.sidebar.dataframe(saved_scans)
        # מחיקה מהירה
        to_del = st.sidebar.multiselect("בחר טיקרים למחיקה מקובץ הסריקות:", options=sorted(saved_scans['Ticker'].unique().tolist()))
        if st.sidebar.button("מחק טיקרים מסריקות"):
            if not to_del:
                st.sidebar.warning("לא נבחרו טיקרים")
            else:
                ok = delete_saved_scan_tickers(to_del)
                if ok:
                    st.sidebar.success("הפריטים נמחקו מקובץ הסריקות")
                else:
                    st.sidebar.error("שגיאה במחיקה")
        if st.sidebar.button("נקה את כל קובץ הסריקות"):
            ok = clear_all_saved_scans()
            if ok:
                st.sidebar.success("קובץ הסריקות נוקה")
            else:
                st.sidebar.error("שגיאה בניקוי הקובץ")

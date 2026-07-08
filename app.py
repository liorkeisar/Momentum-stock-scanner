# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Optional ML import
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# ============================
# הגדרות דף + עיצוב מודרני
# ============================
st.set_page_config(page_title="מערכת וייקוף Pro — עם חיזוי", layout="wide", page_icon="◈")

st.markdown("""
<style>
    html, body, [class*="css"]  { font-family: 'Segoe UI', 'Rubik', sans-serif; }

    .main .block-container { padding-top: 1.5rem; }

    h1 { font-weight: 800; letter-spacing: -0.5px; }

    /* כרטיסי מדדים */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1f2430 0%, #2a3142 100%);
        border: 1px solid #3a4256;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }
    div[data-testid="stMetric"] label { color: #9aa4bd !important; }

    /* טאבים */
    button[data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 600;
        padding: 10px 18px;
    }

    /* כפתורים */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid #3a4256;
        transition: all 0.15s ease-in-out;
    }
    div.stButton > button:hover {
        border-color: #6c8cff;
        color: #6c8cff;
    }

    /* תיבת הערה עליונה */
    .top-banner {
        background: linear-gradient(90deg, #1c2333, #232b40);
        border: 1px solid #333d55;
        border-radius: 12px;
        padding: 10px 16px;
        margin-bottom: 14px;
        color: #b7c0d8;
        font-size: 14px;
    }

    /* badge לציון */
    .score-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

st.title("◈ מערכת השקעות מבוססת וייקוף — סורק פריצה משופר + חיזוי")
st.markdown(
    '<div class="top-banner">⚠️ כלי תמיכה בהחלטה בלבד — אינו מהווה ייעוץ השקעות. '
    'כל החלטת מסחר היא באחריות המשתמש בלבד.</div>',
    unsafe_allow_html=True
)

PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
PREDICTIONS_FILE = 'predictions.csv'

# ============================
# פונקציות עזר בטוחות
# ============================

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
            return df[col].dropna().astype(str).str.upper().str.strip().tolist()
        if 'symbol' in cols:
            col = [c for c in df.columns if c.strip().lower() == 'symbol'][0]
            return df[col].dropna().astype(str).str.upper().str.strip().tolist()
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

@st.cache_data(ttl=300, show_spinner=False)
def load_history(ticker, period="12mo"):
    """טעינת היסטוריית מחירים. cache עם TTL של 5 דקות כדי למנוע נתונים תקועים לאורך זמן."""
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna()
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
    range_hl = (df["High"] - df["Low"]).replace(0, np.nan)
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / range_hl * df["Volume"]
    df["AD_Cum"] = ad.fillna(0).cumsum()

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum().replace(0, np.nan)
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow)))

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RVOL"] = df["Volume"] / df["VOL_MA20"].replace(0, np.nan)

    return df

# ============================
# מנוע החלטה לפני פריצה
# ============================

def score_component(value, low, high, invert=False):
    try:
        if is_bad(value):
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
    ok, msg = validate_df(df, ["High", "Low", "Close", "Volume", "EMA20", "EMA50", "ATR", "STD20",
                               "OBV", "AD_Cum", "MACD", "Signal", "RSI", "MA20", "UpperBB", "LowerBB",
                               "UpperKC", "LowerKC", "VOL_MA20"])
    if not ok:
        return {"score": 0, "confidence": 0, "risk": 100, "components": {}, "note": f"נתונים חסרים ({msg})"}

    comps = {}
    std20 = safe_last(df["STD20"])
    hist_std = df["STD20"].dropna()
    if len(hist_std) >= 30:
        low_std, high_std = hist_std.quantile(0.05), hist_std.quantile(0.95)
    else:
        low_std, high_std = (hist_std.min() if not hist_std.empty else 0), (hist_std.max() if not hist_std.empty else 1)
    comps["compression"] = score_component(std20, low_std, high_std, invert=True)

    vol_ma20 = safe_last(df["VOL_MA20"])
    rvol = safe_div(safe_last(df["Volume"]), vol_ma20, default=1.0)
    comps["rvol"] = score_component(rvol, 0.5, 3.0)

    ema20, ema50 = safe_last(df["EMA20"]), safe_last(df["EMA50"])
    trend_ratio = safe_div(ema20, ema50, default=1.0)
    comps["trend"] = score_component(trend_ratio, 0.95, 1.1)

    macd_diff = safe_last(df["MACD"]) - safe_last(df["Signal"])
    comps["macd"] = score_component(macd_diff, -1.0, 2.0)
    comps["rsi"] = score_component(safe_last(df["RSI"]), 40, 70)

    obv_now, obv_prev = safe_last(df["OBV"]), safe_last(df["OBV"].shift(10))
    ad_now, ad_prev = safe_last(df["AD_Cum"]), safe_last(df["AD_Cum"].shift(10))
    obv_gain = 1 if (not is_bad(obv_now) and not is_bad(obv_prev) and obv_now > obv_prev) else 0
    ad_gain = 1 if (not is_bad(ad_now) and not is_bad(ad_prev) and ad_now > ad_prev) else 0
    comps["institutional"] = int(round(((obv_gain + ad_gain) / 2) * 100))

    high20 = df["High"].rolling(20).max()
    prox = safe_div(safe_last(df["Close"]), safe_last(high20), default=0.0)
    comps["proximity"] = score_component(prox, 0.9, 1.02)

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    weights = {
        "compression": 0.20, "rvol": 0.20, "trend": 0.15, "macd": 0.10, "rsi": 0.05,
        "institutional": 0.10, "proximity": 0.10, "squeeze": 0.05, "risk": 0.05
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
    if not is_bad(prox) and prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric, "components": comps, "note": note}

# ============================
# חיזוי — פונקציות עיקריות
# ============================

def compute_features_for_ml(df, window=20):
    rows = []
    for end in range(window, len(df) - 5):
        w = df.iloc[end - window:end]

        vol_ma = w["Volume"].rolling(20).mean().iloc[-1]
        ema20 = w["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = w["Close"].ewm(span=50, adjust=False).mean().iloc[-1]

        # RSI אמיתי (14 תקופות) - תוקן, קודם לכן חושב רק על עליות בלי ירידות
        delta = w["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1] if len(w) >= 14 else np.nan
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1] if len(w) >= 14 else np.nan
        rsi_val = np.nan
        if not is_bad(gain) and not is_bad(loss):
            rs = gain / loss if loss != 0 else np.nan
            rsi_val = 100 - (100 / (1 + rs)) if not is_bad(rs) else 100.0

        true_range = (w["High"] - w["Low"]).rolling(14).mean().iloc[-1]

        feat = {
            "close_last": w["Close"].iloc[-1],
            "std20": w["Close"].rolling(20).std().iloc[-1] if len(w) >= 20 else np.nan,
            "rvol": safe_div(w["Volume"].iloc[-1], vol_ma, default=1.0),
            "ema20_ema50": safe_div(ema20, ema50, default=1.0),
            "macd_diff": w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
            "rsi": rsi_val,
            "atr_pct": safe_div(true_range, w["Close"].iloc[-1], default=0.0),
            "obv": (np.sign(w["Close"].diff()) * w["Volume"]).fillna(0).cumsum().iloc[-1]
        }
        future = df.iloc[end:end + 5]
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
        return None
    except Exception:
        return None

def logistic_predict_probability(model, df):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return None
        clean = feats.dropna()
        if clean.empty:
            return None
        last = clean.iloc[-1].drop(labels=["label"])
        if SKLEARN_AVAILABLE and model is not None:
            prob = model.predict_proba([last.values])[0][1]
            return float(prob)
        return None
    except Exception:
        return None

def statistical_similarity_prediction(df, tolerance=0.15, lookahead=5):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}
        clean = feats.dropna()
        if clean.empty or len(clean) < 2:
            return {"count": 0, "successes": 0, "rate": 0.0}
        target = clean.iloc[-1]
        candidates = clean.iloc[:-1]
        if candidates.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}

        def similar(row):
            try:
                for k in ["std20", "rvol", "ema20_ema50", "macd_diff", "rsi"]:
                    if k not in row or k not in target:
                        continue
                    a = float(row[k])
                    b = float(target[k])
                    if b == 0:
                        if abs(a - b) > 1e-6:
                            return False
                        continue
                    if abs(a - b) / (abs(b) + 1e-9) > tolerance:
                        return False
                return True
            except Exception:
                return False

        sim = candidates[candidates.apply(similar, axis=1)]
        count = len(sim)
        successes = int(sim['label'].sum()) if 'label' in sim.columns else 0
        rate = (successes / count) if count > 0 else 0.0
        return {"count": count, "successes": successes, "rate": float(rate)}
    except Exception:
        return {"count": 0, "successes": 0, "rate": 0.0}

def pattern_detection_vcp_like(df):
    try:
        window = 30
        if len(df) < window:
            return {"match": False, "desc": "לא מספיק נתונים לתבנית"}
        w = df.tail(window)
        highs = w["High"].values
        lows = w["Low"].values
        step_h = max(1, len(highs) // 3)
        step_l = max(1, len(lows) // 3)
        peaks = [highs[i] for i in range(0, len(highs), step_h)]
        troughs = [lows[i] for i in range(0, len(lows), step_l)]

        lower_highs = len(peaks) >= 2 and all(peaks[i] > peaks[i + 1] for i in range(len(peaks) - 1))
        higher_lows = len(troughs) >= 2 and all(troughs[i] < troughs[i + 1] for i in range(len(troughs) - 1))

        std_vals = w["Close"].rolling(10).std().dropna()
        std_trend = np.polyfit(range(len(std_vals)), std_vals, 1)[0] if len(std_vals) > 2 else 0
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
        return {"match": False, "desc": "שגיאה בזיהוי תבנית"}

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
    cols = ["Ticker", "SavedAt", "stat_count", "stat_successes", "stat_rate", "pattern_match", "pattern_desc", "ml_prob"]
    if not os.path.exists(PREDICTIONS_FILE):
        return pd.DataFrame(columns=cols)
    try:
        return pd.read_csv(PREDICTIONS_FILE)
    except Exception:
        return pd.DataFrame(columns=cols)

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
# שמירת תוצאות סריקה ותמיכה במחיקה
# ============================

def save_single_scan_result(record):
    try:
        df = pd.DataFrame([record])
        header = not os.path.exists(SCAN_RESULTS_FILE)
        df.to_csv(SCAN_RESULTS_FILE, mode='a', header=header, index=False)
        return True
    except Exception:
        return False

def load_saved_scan_results():
    cols = ["Ticker", "Score", "Confidence", "Risk", "Price", "Note", "SavedAt"]
    if not os.path.exists(SCAN_RESULTS_FILE):
        return pd.DataFrame(columns=cols)
    try:
        return pd.read_csv(SCAN_RESULTS_FILE)
    except Exception:
        return pd.DataFrame(columns=cols)

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
# תיק השקעות
# ============================

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    try:
        df = pd.read_csv(PORTFOLIO_FILE)
        if df.empty:
            return pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        return df
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df

def add_to_portfolio(ticker, price):
    """הוספת טיקר לתיק, עם מניעת כפילויות פתוחות לאותו טיקר באותו יום."""
    existing = get_portfolio_df()
    today = datetime.now().strftime('%Y-%m-%d')
    dup = ((existing['Ticker'] == ticker) & (existing['Date'] == today)).any() if not existing.empty else False
    if dup:
        return False, "המניה כבר נוספה לתיק היום"
    new_row = pd.DataFrame({'Ticker': [ticker], 'Date': [today], 'EntryPrice': [price]})
    new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0, index=False)
    return True, "נוספה בהצלחה"

def score_color(score):
    if score >= 75:
        return "#1fc46a"
    if score >= 55:
        return "#e2b93b"
    return "#e2543b"

def score_badge_html(score):
    color = score_color(score)
    return f'<span class="score-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{score}</span>'

def show_buttons(ticker):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.link_button("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}", use_container_width=True)
    with c2: st.link_button("Finviz", f"https://finviz.com/quote.ashx?t={ticker}", use_container_width=True)
    with c3: st.link_button("Investing.com", f"https://www.investing.com/search/?q={ticker}", use_container_width=True)
    with c4: st.link_button("Webull", f"https://www.webull.com/quote/{ticker}", use_container_width=True)

# ============================
# גרף מפורט
# ============================

def plot_advanced(df, ticker, show_macd=False, show_obv=False, show_bands=False, days=90):
    """
    גרף נקי בברירת מחדל: מחיר + MA20 + נפח בלבד.
    MACD / OBV / רצועות בולינגר הם אופציונליים כדי למנוע עומס ויזואלי.
    days: כמות ימי המסחר האחרונים שיוצגו (זום פנימי - מונע גרף "דחוס").
    """
    df = df.tail(days).copy()

    panels = ["price", "volume"]
    if show_macd:
        panels.append("macd")
    if show_obv:
        panels.append("obv")

    heights = {"price": 0.62, "volume": 0.18, "macd": 0.20, "obv": 0.20}
    total = sum(heights[p] for p in panels)
    row_heights = [heights[p] / total for p in panels]

    fig = make_subplots(rows=len(panels), cols=1, shared_xaxes=True,
                         vertical_spacing=0.04, row_heights=row_heights)
    row_of = {p: i + 1 for i, p in enumerate(panels)}

    # --- מחיר ---
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="מחיר", increasing_line_color="#1fc46a", decreasing_line_color="#e2543b",
        increasing_fillcolor="#1fc46a", decreasing_fillcolor="#e2543b", line_width=1
    ), row=row_of["price"], col=1)

    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="#f2c94c", width=1.6),
                                  name="ממוצע נע 20"), row=row_of["price"], col=1)

    if show_bands and "UpperBB" in df.columns and "LowerBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="#3d4a68", width=1),
                                  name="רצועה עליונה", showlegend=False), row=row_of["price"], col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="#3d4a68", width=1),
                                  name="רצועות בולינגר", fill='tonexty', fillcolor='rgba(108,140,255,0.06)'),
                      row=row_of["price"], col=1)

    # --- נפח ---
    vol_colors = np.where(df["Close"] >= df["Open"], "rgba(31,196,106,0.55)", "rgba(226,84,59,0.55)")
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="נפח", marker_color=vol_colors, showlegend=False),
                  row=row_of["volume"], col=1)

    # --- MACD (אופציונלי) ---
    if show_macd and "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#6c8cff", width=1.4)),
                      row=row_of["macd"], col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal", line=dict(color="#e2b93b", width=1.4)),
                      row=row_of["macd"], col=1)

    # --- OBV (אופציונלי) ---
    if show_obv and "OBV" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV", line=dict(color="#c88cff", width=1.4)),
                      row=row_of["obv"], col=1)

    fig.update_layout(
        height=460 + 130 * (len(panels) - 2),
        template="plotly_dark", paper_bgcolor="#131722", plot_bgcolor="#131722",
        font=dict(size=12, color="#c7cede"),
        legend=dict(orientation="h", y=1.05, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=30, b=10, l=10, r=10),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        bargap=0.15,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(title_text="מחיר", row=row_of["price"], col=1)
    fig.update_yaxes(title_text="נפח", row=row_of["volume"], col=1)

    return fig

# ============================
# ממשק משתמש — טאבים
# ============================

tab1, tab2, tab3, tab4 = st.tabs(["📊 סורק פריצה משופר", "💼 תיק השקעות", "🔮 תחזיות שמורות", "🗂️ ניהול סריקות שמורות"])

# --- טאב הסורק ---
with tab1:
    st.sidebar.header("⚙️ מקורות טיקרים לסורק")
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
                    tickers = dfu[col].dropna().astype(str).str.upper().str.strip().tolist()
                elif 'symbol' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'symbol'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().str.strip().tolist()
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

    if st.sidebar.button("🗑️ נקה מטמון מחירים (רענון נתונים)"):
        load_history.clear()
        st.sidebar.success("המטמון נוקה — הריצה הבאה תביא נתונים עדכניים")

    st.sidebar.markdown("---")
    run_scan = st.sidebar.button("🚀 הרץ סריקת פריצה", use_container_width=True, type="primary")

    if run_scan:
        if not tickers:
            st.error("לא נבחרו טיקרים")
        else:
            tickers = list(dict.fromkeys(tickers))[:int(max_tickers)]  # ייחודיים בלבד + הגבלה
            results = []
            details = {}
            progress = st.progress(0, text="מתחיל סריקה...")
            total = len(tickers)
            errors = []

            for i, ticker in enumerate(tickers):
                progress.progress((i + 1) / total, text=f"בודק {ticker} ({i+1}/{total})")
                try:
                    df = load_history(ticker, period="12mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                         "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        continue
                    df = add_indicators(df)
                    res = compute_breakout_decision(df)
                    last_close = safe_last(df["Close"])
                    results.append({
                        "Ticker": ticker,
                        "Score": res["score"],
                        "Confidence": res["confidence"],
                        "Risk": res["risk"],
                        "Price": round(float(last_close), 2) if not is_bad(last_close) else np.nan,
                        "Note": res["note"],
                        "SavedAt": ""
                    })
                    details[ticker] = {"res": res, "df_tail": df.tail(120)}
                except Exception as e:
                    results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                     "Price": np.nan, "Note": "שגיאה", "SavedAt": ""})
                    errors.append(f"{ticker}: {e}")

            progress.empty()
            if errors:
                with st.expander(f"⚠️ {len(errors)} טיקרים נכשלו בסריקה — לחץ לפרטים"):
                    for e in errors:
                        st.caption(e)

            st.session_state["scan_results"] = results
            st.session_state["scan_details"] = details

    # --- הצגת תוצאות אחרונות (נשמר ב-session_state כדי לשרוד ריענונים) ---
    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        df_res_full = pd.DataFrame(st.session_state["scan_results"]).sort_values("Score", ascending=False).reset_index(drop=True)
        df_res = df_res_full[df_res_full["Score"] >= min_score]
        details = st.session_state.get("scan_details", {})

        if df_res.empty:
            st.info("לא נמצאו מניות מתאימות לפי הקריטריונים.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("סה\"כ נסרקו", len(df_res_full))
            c2.metric("עומדים בסף", len(df_res))
            c3.metric("ציון ממוצע (עומדים בסף)", round(df_res["Score"].mean(), 1))

            st.subheader("📋 תוצאות סריקה")
            st.dataframe(
                df_res,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d"),
                    "Confidence": st.column_config.ProgressColumn("ביטחון", min_value=0, max_value=100, format="%d"),
                    "Risk": st.column_config.ProgressColumn("סיכון (נמוך=טוב)", min_value=0, max_value=100, format="%d"),
                    "Price": st.column_config.NumberColumn("מחיר", format="$%.2f"),
                }
            )

            st.divider()
            col_save1, col_save2 = st.columns([3, 1])
            with col_save1:
                save_note = st.text_input("הערה לשמירה (אופציונלי):", "")
            with col_save2:
                st.write("")
                if st.button("💾 שמור תוצאות", use_container_width=True):
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
                st.write("")
                if st.button("➕ הוסף לתיק ההשקעות", use_container_width=True):
                    try:
                        price = df_res[df_res['Ticker'] == to_view]['Price'].values[0]
                    except Exception:
                        price = None
                    ok, msg = add_to_portfolio(to_view, price)
                    (st.success if ok else st.warning)(f"{to_view}: {msg}")

            # דוח מפורט לטיקר הנבחר
            st.subheader(f"🔎 דוח מפורט — {to_view}")
            info = details.get(to_view)
            if info:
                res = info["res"]
                m1, m2, m3 = st.columns(3)
                m1.metric("ציון פריצה", res["score"])
                m2.metric("ביטחון", f'{res["confidence"]}%')
                m3.metric("מדד סיכון", res["risk"])

                st.markdown(f"**סטטוס:** {score_badge_html(res['score'])}", unsafe_allow_html=True)

                with st.expander("📊 רכיבי ניקוד מפורטים"):
                    comp_df = pd.DataFrame.from_dict(res["components"], orient="index", columns=["ערך"]).sort_values("ערך", ascending=False)
                    st.dataframe(comp_df, use_container_width=True,
                                 column_config={"ערך": st.column_config.ProgressColumn("ערך", min_value=0, max_value=100, format="%d")})

                st.info(f"**הערות:** {res['note']}")

                df_plot = info["df_tail"].copy()
                gc1, gc2, gc3, gc4 = st.columns(4)
                days_view = gc1.select_slider("טווח ימים בגרף", options=[30, 60, 90, 120], value=90, key=f"days_{to_view}")
                show_bands = gc2.checkbox("רצועות בולינגר", value=False, key=f"bands_{to_view}")
                show_macd = gc3.checkbox("MACD", value=False, key=f"macd_{to_view}")
                show_obv = gc4.checkbox("OBV", value=False, key=f"obv_{to_view}")
                st.plotly_chart(
                    plot_advanced(df_plot, to_view, show_macd=show_macd, show_obv=show_obv,
                                  show_bands=show_bands, days=days_view),
                    use_container_width=True
                )

                show_buttons(to_view)

                # ---------- חיזוי ----------
                st.markdown("---")
                st.markdown("### 🔮 חיזוי תנועות עבר")
                colp1, colp2 = st.columns([3, 1])
                with colp1:
                    lookahead = st.selectbox("חלון חיזוי (ימים):", [3, 5, 7], index=1, key=f"look_{to_view}")
                    stat_tol = st.slider("סף דמיון סטטיסטי (אחוזי שונות):", 5, 50, 15, key=f"tol_{to_view}")
                with colp2:
                    st.write("")
                    run_pred = st.button("הרץ חיזוי", key=f"pred_btn_{to_view}", use_container_width=True)

                if run_pred:
                    with st.spinner("מריץ חיזוי..."):
                        try:
                            hist_full = load_history(to_view, period="24mo")
                            if hist_full.empty:
                                st.error("אין היסטוריית מחירים מספקת לחיזוי")
                            else:
                                hist_full = add_indicators(hist_full)
                                stat = statistical_similarity_prediction(hist_full, tolerance=stat_tol / 100.0, lookahead=lookahead)
                                pat = pattern_detection_vcp_like(hist_full)
                                model = train_logistic_model(hist_full)
                                ml_prob = logistic_predict_probability(model, hist_full)

                                if ml_prob is None:
                                    comps = res["components"]
                                    heur_weights = {"compression": 0.25, "rvol": 0.25, "trend": 0.2, "macd": 0.15, "proximity": 0.15}
                                    wsum = sum(comps.get(k, 0) * w for k, w in heur_weights.items())
                                    wtot = sum(heur_weights.values())
                                    ml_prob = float(min(0.99, max(0.01, wsum / (wtot * 100))))

                                st.success("חיזוי הושלם")
                                pc1, pc2, pc3 = st.columns(3)
                                pc1.metric("שיעור הצלחה סטטיסטי", f"{round(stat['rate']*100,1)}%", f"{stat['count']} מקרים דומים")
                                pc2.metric("תבנית VCP", "✅ נמצאה" if pat["match"] else "❌ לא נמצאה")
                                pc3.metric(f"הסתברות פריצה ({lookahead} ימים)", f"{round(ml_prob*100,1)}%")
                                st.caption(f"תבנית: {pat['desc']}")

                                rec = {
                                    "Ticker": to_view,
                                    "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "stat_count": stat["count"], "stat_successes": stat["successes"], "stat_rate": stat["rate"],
                                    "pattern_match": pat["match"], "pattern_desc": pat["desc"], "ml_prob": ml_prob
                                }
                                if save_prediction_record(rec):
                                    st.caption("✅ תחזית נשמרה ב-predictions.csv")

                                last_close_full = safe_last(hist_full["Close"])
                                scan_row = {
                                    "Ticker": to_view, "Score": res["score"], "Confidence": res["confidence"], "Risk": res["risk"],
                                    "Price": round(float(last_close_full), 2) if not is_bad(last_close_full) else np.nan,
                                    "Note": res["note"] + " | prediction",
                                    "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                save_single_scan_result(scan_row)
                        except Exception as e:
                            st.error(f"שגיאה בהרצת חיזוי: {e}")
            else:
                st.warning("אין פרטים לטיקר זה")

            st.divider()
            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ הורד תוצאות כ-CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")
    else:
        st.info("👈 בחר מקור טיקרים בסרגל הצד ולחץ על 'הרץ סריקת פריצה' כדי להתחיל.")

# --- טאב תיק ההשקעות ---
with tab2:
    st.subheader("💼 תיק ההשקעות שלי")
    portfolio = get_portfolio_df()

    with st.expander("➕ הוסף מניה ידנית לתיק"):
        with st.form("add_manual_stock_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            new_ticker = fc1.text_input("טיקר").strip().upper()
            new_date = fc2.date_input("תאריך כניסה", value=datetime.now())
            new_price = fc3.number_input("מחיר כניסה", min_value=0.0, step=0.01, format="%.2f")
            submitted = st.form_submit_button("הוסף לתיק", use_container_width=True)
            if submitted:
                if not new_ticker:
                    st.warning("נא להזין טיקר")
                else:
                    new_row = pd.DataFrame({'Ticker': [new_ticker], 'Date': [new_date.strftime('%Y-%m-%d')], 'EntryPrice': [new_price]})
                    new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0, index=False)
                    st.success(f"{new_ticker} נוספה בהצלחה לתיק!")
                    st.rerun()

    if not portfolio.empty:
        with st.spinner("מעדכן מחירים נוכחיים..."):
            for i, row in portfolio.iterrows():
                try:
                    hist = yf.Ticker(row['Ticker']).history(period="1d")
                    if hist.empty:
                        raise ValueError("no data")
                    curr = float(hist['Close'].iloc[-1])
                    portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                    entry = row['EntryPrice']
                    if not is_bad(entry) and float(entry) != 0:
                        portfolio.loc[i, 'Performance'] = round(((curr - float(entry)) / float(entry)) * 100, 2)
                    else:
                        portfolio.loc[i, 'Performance'] = np.nan
                except Exception:
                    portfolio.loc[i, 'CurrentPrice'] = np.nan
                    portfolio.loc[i, 'Performance'] = np.nan

        total_perf = portfolio['Performance'].dropna()
        if not total_perf.empty:
            pc1, pc2 = st.columns(2)
            pc1.metric("מספר החזקות", len(portfolio))
            pc2.metric("ביצוע ממוצע", f"{round(total_perf.mean(), 2)}%")

        st.dataframe(
            portfolio, use_container_width=True, hide_index=True,
            column_config={
                "EntryPrice": st.column_config.NumberColumn("מחיר כניסה", format="$%.2f"),
                "CurrentPrice": st.column_config.NumberColumn("מחיר נוכחי", format="$%.2f"),
                "Performance": st.column_config.NumberColumn("ביצוע %", format="%.2f%%"),
            }
        )

        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        show_buttons(to_manage)

        if st.button("🗑️ מחק מניה מהתיק"):
            portfolio_raw = get_portfolio_df()
            portfolio_raw = portfolio_raw[portfolio_raw['Ticker'] != to_manage]
            portfolio_raw.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_manage} הוסר מהתיק")
            st.rerun()
    else:
        st.info("התיק ריק. הוסף מניות מהסורק או ידנית למעלה.")

# --- טאב תחזיות שמורות ---
with tab3:
    st.subheader("🔮 תחזיות שמורות")
    preds = load_predictions()
    if preds.empty:
        st.info("אין תחזיות שמורות כרגע.")
    else:
        st.dataframe(
            preds, use_container_width=True, hide_index=True,
            column_config={
                "stat_rate": st.column_config.ProgressColumn("שיעור הצלחה סטטיסטי", min_value=0, max_value=1, format="%.2f"),
                "ml_prob": st.column_config.ProgressColumn("הסתברות מודל", min_value=0, max_value=1, format="%.2f"),
            }
        )
        st.divider()
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            to_delete = st.multiselect("בחר טיקרים למחיקה מהתחזיות השמורות:", options=sorted(preds['Ticker'].unique().tolist()))
        with col_del2:
            st.write("")
            if st.button("מחק נבחרים", use_container_width=True):
                if not to_delete:
                    st.warning("לא נבחרו טיקרים למחיקה")
                elif delete_prediction_tickers(to_delete):
                    st.success("התחזיות נמחקו")
                    st.rerun()
                else:
                    st.error("שגיאה במחיקה")

        if st.button("נקה את כל התחזיות השמורות"):
            if clear_all_predictions():
                st.success("כל התחזיות נמחקו")
                st.rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")

        csv_all = preds.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד את כל התחזיות כ-CSV", csv_all, file_name="saved_predictions.csv", mime="text/csv")

        st.markdown("---")
        st.subheader("➕ הוספה מהתחזיות לתיק ההשקעות")
        saved_preds = sorted(preds['Ticker'].unique().tolist())
        pcol1, pcol2 = st.columns([3, 1])
        with pcol1:
            pick = st.selectbox("בחר טיקר להוספה לתיק:", saved_preds)
        with pcol2:
            st.write("")
            if st.button("הוסף לתיק", key="add_from_preds", use_container_width=True):
                try:
                    hist_full = load_history(pick, period="12mo")
                    last_close = safe_last(hist_full["Close"]) if not hist_full.empty else np.nan
                    price = round(float(last_close), 2) if not is_bad(last_close) else None
                    ok, msg = add_to_portfolio(pick, price)
                    (st.success if ok else st.warning)(f"{pick}: {msg}")
                except Exception as e:
                    st.error(f"שגיאה בהוספה לתיק: {e}")

# --- טאב ניהול תוצאות סריקה שמורות ---
with tab4:
    st.subheader("🗂️ ניהול תוצאות סריקה שמורות")
    saved_scans = load_saved_scan_results()
    if saved_scans.empty:
        st.info("אין תוצאות סריקה שמורות.")
    else:
        st.dataframe(
            saved_scans, use_container_width=True, hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d"),
                "Confidence": st.column_config.ProgressColumn("ביטחון", min_value=0, max_value=100, format="%d"),
                "Price": st.column_config.NumberColumn("מחיר", format="$%.2f"),
            }
        )
        st.divider()
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            to_del = st.multiselect("בחר טיקרים למחיקה מקובץ הסריקות:", options=sorted(saved_scans['Ticker'].unique().tolist()))
        with col_del2:
            st.write("")
            if st.button("מחק נבחרים מסריקות", use_container_width=True):
                if not to_del:
                    st.warning("לא נבחרו טיקרים")
                elif delete_saved_scan_tickers(to_del):
                    st.success("הפריטים נמחקו מקובץ הסריקות")
                    st.rerun()
                else:
                    st.error("שגיאה במחיקה")

        if st.button("נקה את כל קובץ הסריקות"):
            if clear_all_saved_scans():
                st.success("קובץ הסריקות נוקה")
                st.rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")

        csv_all_scans = saved_scans.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד את כל הסריקות כ-CSV", csv_all_scans, file_name="saved_scans.csv", mime="text/csv")

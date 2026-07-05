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

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro — עם חיזוי וניהול סיכון", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף — סורק פריצה + חיזוי + ניהול פוזיציה")

PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
PREDICTIONS_FILE = 'predictions.csv'
SETTINGS_FILE = 'account_settings.csv'

PORTFOLIO_COLUMNS = ['Ticker', 'Date', 'EntryPrice', 'StopLoss', 'Shares',
                      'RiskAmount', 'TargetPrice', 'Notes']

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

def is_bad_number(x):
    """True אם x הוא None / NaN / לא ניתן להמרה למספר."""
    try:
        if x is None:
            return True
        return bool(np.isnan(float(x)))
    except Exception:
        return True

def safe_div(a, b, default=1.0):
    """חילוק בטוח שמטפל גם ב-0 וגם ב-NaN (הבאג המקורי לא תפס NaN)."""
    try:
        if is_bad_number(a) or is_bad_number(b) or float(b) == 0.0:
            return default
        return float(a) / float(b)
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

@st.cache_data(ttl=900)
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
    hl_range = (df["High"] - df["Low"]).replace(0, np.nan)
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / hl_range * df["Volume"]
    df["AD_Cum"] = ad.fillna(0).cumsum()

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    mfi_ratio = pos_flow / neg_flow.replace(0, np.nan)
    df["MFI"] = 100 - (100 / (1 + mfi_ratio))

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
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
        if is_bad_number(value):
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

BENCHMARK_TICKER = "SPY"

@st.cache_data(ttl=900)
def load_benchmark_history(period="12mo"):
    return load_history(BENCHMARK_TICKER, period=period)

def compute_relative_strength(df, benchmark_df, lookback=63):
    """
    עוצמה יחסית מול מדד ייחוס (ברירת מחדל SPY): משווה את התשואה של המניה
    לתשואת המדד על פני אותו טווח (ברירת מחדל כ-3 חודשי מסחר).
    מחזיר יחס: >1 אומר שהמניה חזקה מהמדד, <1 חלשה ממנו.
    """
    try:
        if df is None or benchmark_df is None or df.empty or benchmark_df.empty:
            return np.nan
        n = min(lookback, len(df) - 1, len(benchmark_df) - 1)
        if n < 5:
            return np.nan
        stock_ret = safe_div(df["Close"].iloc[-1], df["Close"].iloc[-n - 1], default=np.nan) - 1
        bench_ret = safe_div(benchmark_df["Close"].iloc[-1], benchmark_df["Close"].iloc[-n - 1], default=np.nan) - 1
        if is_bad_number(stock_ret) or is_bad_number(bench_ret):
            return np.nan
        return (1 + stock_ret) / (1 + bench_ret) if (1 + bench_ret) != 0 else np.nan
    except Exception:
        return np.nan

def compute_avg_dollar_volume(df, lookback=20):
    """מחזור מסחר ממוצע בדולרים - סינון נזילות בסיסי."""
    try:
        if df is None or df.empty or "Volume" not in df.columns or "Close" not in df.columns:
            return np.nan
        tail = df.tail(lookback)
        dollar_vol = (tail["Close"] * tail["Volume"]).mean()
        return float(dollar_vol) if not is_bad_number(dollar_vol) else np.nan
    except Exception:
        return np.nan

def passes_liquidity_filter(df, min_price=5.0, min_avg_dollar_volume=5_000_000.0):
    """בודק שהטיקר עומד בסף נזילות ומחיר מינימלי לפני שהוא בכלל מקבל ציון."""
    last_close = safe_last(df["Close"]) if df is not None and "Close" in df.columns else np.nan
    if is_bad_number(last_close) or last_close < min_price:
        return False, f"מחיר מתחת לסף ({min_price})"
    adv = compute_avg_dollar_volume(df)
    if is_bad_number(adv) or adv < min_avg_dollar_volume:
        return False, f"מחזור מסחר ממוצע נמוך מהסף ({min_avg_dollar_volume:,.0f}$)"
    return True, None

COMPONENT_LABELS_HE = {
    "compression": "דחיסת מחיר (Squeeze)",
    "rvol": "נפח יחסי (RVOL)",
    "trend": "מגמה (EMA20/50)",
    "macd": "מומנטום (MACD)",
    "rsi": "RSI",
    "institutional": "כסף מוסדי (OBV/AD)",
    "proximity": "קרבה לפריצה (52W High)",
    "squeeze": "Squeeze (BB/KC)",
    "risk": "רמת סיכון (ATR%)",
    "relative_strength": "עוצמה יחסית לשוק (RS)"
}

def traffic_light(value, green_th=70, yellow_th=40):
    """ממיר ציון 0-100 לרמזור: ירוק (טוב) / צהוב (בינוני) / אדום (חלש)."""
    try:
        v = float(value)
        if is_bad_number(v):
            return "⚪", "לא זמין"
    except Exception:
        return "⚪", "לא זמין"
    if v >= green_th:
        return "🟢", "טוב"
    elif v >= yellow_th:
        return "🟡", "בינוני"
    else:
        return "🔴", "חלש"

def overall_traffic_badge(score, label_prefix="מצב כללי"):
    emoji, label = traffic_light(score)
    st.markdown(f"#### {emoji} {label_prefix}: **{label}** (ציון {score}/100)")

def render_component_traffic_lights(components):
    """מציג את רכיבי הניקוד כרמזור צבעוני, כדי לאפשר סריקה מהירה במקום טבלת מספרים גולמית."""
    rows = sorted(components.items(), key=lambda x: x[1], reverse=True)
    html = "<table style='width:100%; border-collapse: collapse;'>"
    for key, val in rows:
        emoji, label = traffic_light(val)
        name = COMPONENT_LABELS_HE.get(key, key)
        html += (
            "<tr style='border-bottom:1px solid rgba(128,128,128,0.3);'>"
            f"<td style='padding:6px 10px; font-size:20px; width:40px;'>{emoji}</td>"
            f"<td style='padding:6px 10px;'>{name}</td>"
            f"<td style='padding:6px 10px; text-align:left; opacity:0.65; width:70px;'>{int(val)}/100</td>"
            f"<td style='padding:6px 10px; text-align:left; width:70px;'>{label}</td>"
            "</tr>"
        )
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

def render_breakout_summary(res):
    """תצוגה מרוכזת: רמזור כללי + ביטחון/סיכון + טבלת רכיבים כרמזור."""
    overall_traffic_badge(res["score"], label_prefix="מצב כללי לפריצה")
    col1, col2 = st.columns(2)
    with col1:
        conf_emoji, conf_label = traffic_light(res["confidence"])
        st.markdown(f"**ביטחון בסיגנל:** {conf_emoji} {conf_label} ({res['confidence']}/100)")
    with col2:
        risk_emoji, risk_label = traffic_light(res["risk"])
        st.markdown(f"**רמת בטיחות (ATR):** {risk_emoji} {risk_label} ({res['risk']}/100)")
    st.write("**רכיבי ניקוד**")
    render_component_traffic_lights(res["components"])
    with st.expander("הצג ערכים גולמיים (למשתמשים מתקדמים)"):
        comp_df = pd.DataFrame.from_dict(res["components"], orient="index", columns=["Value"]).sort_values("Value", ascending=False)
        st.table(comp_df)


    ok, msg = validate_df(df, ["High", "Low", "Close", "Volume", "EMA20", "EMA50", "ATR", "STD20",
                                "OBV", "AD_Cum", "MACD", "Signal", "RSI", "MA20", "UpperBB",
                                "LowerBB", "UpperKC", "LowerKC", "VOL_MA20"])
    if not ok:
        return {"score": 0, "confidence": 0, "risk": 100, "components": {}, "note": "נתונים חסרים"}

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
    obv_gain = 1 if (not is_bad_number(obv_now) and not is_bad_number(obv_prev) and obv_now > obv_prev) else 0
    ad_gain = 1 if (not is_bad_number(ad_now) and not is_bad_number(ad_prev) and ad_now > ad_prev) else 0
    comps["institutional"] = int(round(((obv_gain + ad_gain) / 2) * 100))

    high20 = df["High"].rolling(20).max()
    prox = safe_div(safe_last(df["Close"]), safe_last(high20), default=0.0)
    comps["proximity"] = score_component(prox, 0.9, 1.02)

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad_number(ubb) and not is_bad_number(ukc) and not is_bad_number(lbb) and not is_bad_number(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    # עוצמה יחסית מול השוק (SPY) - מניה שמתחזקת יחסית למדד היא אות חזק יותר
    # מ"פריצה" שהיא בעצם רק תזוזה כללית של השוק כולו.
    rs_ratio = compute_relative_strength(df, benchmark_df) if benchmark_df is not None else np.nan
    comps["relative_strength"] = score_component(rs_ratio, 0.9, 1.25)

    weights = {
        "compression": 0.17, "rvol": 0.17, "trend": 0.13, "macd": 0.08, "rsi": 0.05,
        "institutional": 0.08, "proximity": 0.08, "squeeze": 0.04, "risk": 0.05,
        "relative_strength": 0.15
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
    if comps.get("relative_strength", 0) >= 70: notes.append("חזקה יחסית לשוק (RS)")
    elif comps.get("relative_strength", 0) <= 20: notes.append("חלשה יחסית לשוק — זהירות")
    if prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric,
            "components": comps, "note": note}

# ============================
# חיזוי — פונקציות עיקריות
# ============================

def _true_rsi_last(window_series, period=14):
    """חישוב RSI אמיתי (התיקון: הגרסה הקודמת חישבה רק ממוצע עליות ולא RSI בפועל)."""
    delta = window_series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1] if len(rsi) > 0 else np.nan
    return val

def compute_features_for_ml(df, window=20):
    rows = []
    for end in range(window, len(df) - 5):
        w = df.iloc[end - window:end]
        vol_ma20_last = w["Volume"].rolling(20).mean().iloc[-1]
        ema50_last = w["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
        feat = {
            "close_last": w["Close"].iloc[-1],
            "std20": w["Close"].rolling(20).std().iloc[-1] if len(w) >= 20 else np.nan,
            "rvol": safe_div(w["Volume"].iloc[-1], vol_ma20_last, default=1.0),
            "ema20_ema50": safe_div(w["Close"].ewm(span=20, adjust=False).mean().iloc[-1], ema50_last, default=1.0),
            "macd_diff": w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
            "rsi": _true_rsi_last(w["Close"], period=14) if len(w) >= 14 else np.nan,
            "atr_pct": safe_div((w["High"] - w["Low"]).rolling(14).mean().iloc[-1], w["Close"].iloc[-1], default=0.0),
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
        cleaned = feats.dropna()
        if cleaned.empty:
            return None
        last = cleaned.iloc[-1].drop(labels=["label"])
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
        cleaned = feats.dropna()
        if cleaned.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}
        target = cleaned.iloc[-1]
        candidates = cleaned.iloc[:-1]
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
        n_segments = 4
        seg_size = max(1, len(highs) // n_segments)
        peaks = [highs[i:i + seg_size].max() for i in range(0, len(highs), seg_size) if len(highs[i:i + seg_size]) > 0]
        troughs = [lows[i:i + seg_size].min() for i in range(0, len(lows), seg_size) if len(lows[i:i + seg_size]) > 0]
        lower_highs = len(peaks) >= 2 and all(peaks[i] >= peaks[i + 1] for i in range(len(peaks) - 1))
        higher_lows = len(troughs) >= 2 and all(troughs[i] <= troughs[i + 1] for i in range(len(troughs) - 1))
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
# שמירת תוצאות סריקה
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
# גרף מפורט
# ============================

def plot_advanced(df, ticker, stop_loss=None, target=None):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                         row_heights=[0.5, 0.12, 0.18, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                                  close=df["Close"], name="Price"), row=1, col=1)
    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="blue"), name="MA20"), row=1, col=1)
    if "UpperBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="lightblue"), name="UpperBB"), row=1, col=1)
    if "LowerBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="lightblue"), name="LowerBB"), row=1, col=1)
    if stop_loss is not None and not is_bad_number(stop_loss):
        fig.add_hline(y=stop_loss, line=dict(color="red", dash="dash"), annotation_text="Stop Loss", row=1, col=1)
    if target is not None and not is_bad_number(target):
        fig.add_hline(y=target, line=dict(color="green", dash="dash"), annotation_text="Target", row=1, col=1)
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
# הגדרות חשבון / ניהול סיכון
# ============================

DEFAULT_SETTINGS = {"account_size": 100000.0, "risk_per_trade_pct": 1.0, "max_portfolio_heat_pct": 6.0}

def load_account_settings():
    if not os.path.exists(SETTINGS_FILE):
        pd.DataFrame([DEFAULT_SETTINGS]).to_csv(SETTINGS_FILE, index=False)
        return dict(DEFAULT_SETTINGS)
    try:
        df = pd.read_csv(SETTINGS_FILE)
        if df.empty:
            return dict(DEFAULT_SETTINGS)
        row = df.iloc[0].to_dict()
        merged = dict(DEFAULT_SETTINGS)
        merged.update({k: v for k, v in row.items() if k in DEFAULT_SETTINGS and not is_bad_number(v)})
        return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)

def save_account_settings(settings):
    try:
        pd.DataFrame([settings]).to_csv(SETTINGS_FILE, index=False)
        return True
    except Exception:
        return False

def calculate_position_size(account_size, risk_pct, entry_price, stop_price):
    """מחשב גודל פוזיציה לפי סיכון קבוע באחוזים מהחשבון."""
    risk_amount = float(account_size) * (float(risk_pct) / 100.0)
    per_share_risk = abs(float(entry_price) - float(stop_price))
    if per_share_risk <= 0:
        return {"shares": 0, "risk_amount": risk_amount, "position_value": 0.0, "per_share_risk": 0.0}
    shares = int(risk_amount // per_share_risk)
    position_value = shares * float(entry_price)
    return {"shares": shares, "risk_amount": round(risk_amount, 2),
            "position_value": round(position_value, 2), "per_share_risk": round(per_share_risk, 2)}

def suggest_stop_loss(df, entry_price, atr_multiplier=1.5):
    atr = safe_last(df["ATR"]) if (df is not None and "ATR" in df.columns) else np.nan
    if is_bad_number(atr) or is_bad_number(entry_price):
        return round(float(entry_price) * 0.95, 2) if not is_bad_number(entry_price) else np.nan
    return round(float(entry_price) - float(atr) * atr_multiplier, 2)

# ============================
# תיק השקעות
# ============================

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        df = pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    try:
        df = pd.read_csv(PORTFOLIO_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    # מיגרציה: תמיכה בקבצי תיק ישנים שנשמרו לפני שהוספנו עמודות ניהול סיכון
    for col in PORTFOLIO_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    return df[PORTFOLIO_COLUMNS]

def append_position_to_portfolio(ticker, entry_price, stop_loss, shares, risk_amount, target_price=None, notes=""):
    new_row = pd.DataFrame([{
        "Ticker": ticker,
        "Date": datetime.now().strftime('%Y-%m-%d'),
        "EntryPrice": entry_price,
        "StopLoss": stop_loss,
        "Shares": shares,
        "RiskAmount": risk_amount,
        "TargetPrice": target_price if target_price is not None else np.nan,
        "Notes": notes
    }])
    portfolio = get_portfolio_df()
    portfolio = pd.concat([portfolio, new_row], ignore_index=True)
    portfolio.to_csv(PORTFOLIO_FILE, index=False)

def show_buttons(ticker):
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"[Yahoo](https://finance.yahoo.com/quote/{ticker})")
    with c2: st.markdown(f"[Finviz](https://finviz.com/quote.ashx?t={ticker})")
    c3, c4 = st.columns(2)
    with c3: st.markdown(f"[Investing](https://www.investing.com/search/?q={ticker})")
    with c4: st.markdown(f"[Webull](https://www.webull.com/quote/{ticker})")

def render_add_to_portfolio_form(ticker, price, df, key_suffix, settings):
    """
    טופס מאוחד להוספת פוזיציה לתיק עם ניהול סיכון מובנה.
    שימוש ב-st.form פותר את הבאג המקורי שבו כפתור בתוך כפתור
    נעלם מיד עקב rerun של Streamlit לפני שהמשתמש הספיק להזין נתונים.
    """
    if price is None or is_bad_number(price):
        st.warning("אין מחיר תקף עבור טיקר זה, לא ניתן להוסיף לתיק.")
        return

    suggested_stop = suggest_stop_loss(df, price) if df is not None else round(price * 0.95, 2)

    with st.form(key=f"add_form_{key_suffix}"):
        st.write(f"**הוספת {ticker} לתיק עם ניהול סיכון**")
        col1, col2 = st.columns(2)
        with col1:
            entry_price = st.number_input("מחיר כניסה", value=float(price), min_value=0.01, key=f"entry_{key_suffix}")
            risk_pct = st.number_input("סיכון לעסקה (% מהחשבון)", value=float(settings["risk_per_trade_pct"]),
                                        min_value=0.1, max_value=20.0, step=0.1, key=f"riskpct_{key_suffix}")
        with col2:
            stop_default = suggested_stop if not is_bad_number(suggested_stop) else round(float(price) * 0.95, 2)
            stop_loss = st.number_input("סטופ לוס (מוצע לפי ATR)", value=float(stop_default),
                                         min_value=0.01, key=f"stop_{key_suffix}")
            target_price = st.number_input("יעד מחיר (אופציונלי, 0=ללא)", value=0.0, min_value=0.0,
                                            key=f"target_{key_suffix}")
        notes = st.text_input("הערות (אופציונלי)", "", key=f"notes_{key_suffix}")

        sizing = calculate_position_size(settings["account_size"], risk_pct, entry_price, stop_loss)
        st.caption(
            f"💰 סכום בסיכון: {sizing['risk_amount']:.2f} | "
            f"📦 מס' מניות מוצע: {sizing['shares']} | "
            f"💵 שווי פוזיציה: {sizing['position_value']:.2f} | "
            f"⚠️ סיכון למניה: {sizing['per_share_risk']:.2f}"
        )
        if entry_price <= stop_loss:
            st.warning("שים לב: מחיר הכניסה נמוך או שווה לסטופ — בדוק את הכיוון של העסקה.")

        submitted = st.form_submit_button("הוסף לתיק ✅")
        if submitted:
            if sizing["shares"] <= 0:
                st.error("לא ניתן לחשב גודל פוזיציה תקין (בדוק את הסטופ לוס).")
            else:
                append_position_to_portfolio(
                    ticker=ticker,
                    entry_price=round(entry_price, 2),
                    stop_loss=round(stop_loss, 2),
                    shares=sizing["shares"],
                    risk_amount=sizing["risk_amount"],
                    target_price=round(target_price, 2) if target_price > 0 else None,
                    notes=notes
                )
                st.success(f"{ticker} נוסף לתיק: {sizing['shares']} מניות, סיכון {sizing['risk_amount']:.2f}")

# ============================
# ממשק משתמש — טאבים
# ============================

account_settings = load_account_settings()

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 סורק פריצה משופר", "💼 תיק השקעות", "💾 תוצאות שמורות", "🎯 ניהול סיכון"]
)

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
    st.sidebar.subheader("סינון נזילות ואיכות")
    min_price_filter = st.sidebar.number_input("מחיר מינימלי ($):", min_value=0.0, value=5.0, step=1.0)
    min_dollar_vol_filter = st.sidebar.number_input(
        "מחזור מסחר ממוצע יומי מינימלי ($):", min_value=0.0, value=5_000_000.0, step=500_000.0, format="%.0f"
    )
    use_rs_filter = st.sidebar.checkbox("סנן החוצה מניות חלשות מהשוק (RS)", value=False,
                                         help="אם מסומן, מניות עם עוצמה יחסית חלשה מ-SPY לא יופיעו בתוצאות כלל.")

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

            benchmark_df = load_benchmark_history(period="12mo")
            if benchmark_df.empty:
                st.warning(f"לא ניתן היה לטעון נתוני מדד ייחוס ({BENCHMARK_TICKER}) — ציון העוצמה היחסית (RS) יידלג.")
                benchmark_df = None

            for i, ticker in enumerate(tickers):
                try:
                    df = load_history(ticker, period="12mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                         "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        progress.progress((i + 1) / total, text=f"נסרקו {i+1}/{total} מניות")
                        continue

                    # סינון נזילות/איכות - לפני חישוב ציון, כדי לא לבזבז ציון גבוה על מניה לא סחירה
                    liquid_ok, liquid_reason = passes_liquidity_filter(
                        df, min_price=min_price_filter, min_avg_dollar_volume=min_dollar_vol_filter
                    )
                    if not liquid_ok:
                        last_close_raw = safe_last(df["Close"])
                        results.append({
                            "Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                            "Price": round(float(last_close_raw), 2) if not is_bad_number(last_close_raw) else np.nan,
                            "Note": f"סונן: {liquid_reason}", "SavedAt": ""
                        })
                        progress.progress((i + 1) / total, text=f"נסרקו {i+1}/{total} מניות")
                        continue

                    df = add_indicators(df)
                    res = compute_breakout_decision(df, benchmark_df=benchmark_df)

                    if use_rs_filter and res["components"].get("relative_strength", 0) < 40:
                        progress.progress((i + 1) / total, text=f"נסרקו {i+1}/{total} מניות")
                        continue

                    last_close = safe_last(df["Close"])
                    results.append({
                        "Ticker": ticker,
                        "Score": res["score"],
                        "Confidence": res["confidence"],
                        "Risk": res["risk"],
                        "Price": round(float(last_close), 2) if not is_bad_number(last_close) else np.nan,
                        "Note": res["note"],
                        "SavedAt": ""
                    })
                    details[ticker] = {"res": res, "df_tail": df.tail(120)}
                except Exception:
                    results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                     "Price": np.nan, "Note": "שגיאה", "SavedAt": ""})
                progress.progress((i + 1) / total, text=f"נסרקו {i+1}/{total} מניות")

            st.session_state["scan_results"] = results
            st.session_state["scan_details"] = details
            progress.progress(1.0, text=f"הסריקה הושלמה — {total} מניות נבדקו")
            st.success(f"סריקה הושלמה: {total} מניות נבדקו")

    # שימוש בתוצאות שמורות ב-session_state כדי לשרוד בין אינטראקציות (טפסים וכו')
    results = st.session_state.get("scan_results", [])
    details = st.session_state.get("scan_details", {})

    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False).reset_index(drop=True)
        df_res = df_res[df_res["Score"] >= min_score]

        if df_res.empty:
            st.info("לא נמצאו מניות מתאימות לפי הקריטריונים.")
        else:
            st.subheader("תוצאות סריקה")
            df_res_display = df_res.copy()
            df_res_display.insert(1, "מצב", df_res_display["Score"].apply(lambda s: traffic_light(s)[0]))
            st.dataframe(df_res_display, use_container_width=True)

            st.divider()
            col_save1, col_save2 = st.columns([3, 1])
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
            to_view = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].tolist())

            st.subheader("דוח מפורט לטיקר")
            sel = to_view
            info = details.get(sel)
            if info:
                res = info["res"]
                render_breakout_summary(res)
                st.write("**הערות**")
                st.info(res["note"])

                df_plot = info["df_tail"].copy()
                sel_price_row = df_res[df_res['Ticker'] == sel]
                sel_price = float(sel_price_row['Price'].values[0]) if not sel_price_row.empty and not is_bad_number(sel_price_row['Price'].values[0]) else np.nan
                sel_stop = suggest_stop_loss(df_plot, sel_price) if not is_bad_number(sel_price) else None
                st.plotly_chart(plot_advanced(df_plot, sel, stop_loss=sel_stop), use_container_width=True)

                show_buttons(sel)

                # ---------- לחצן חיזוי ----------
                st.markdown("---")
                st.markdown("### 🔮 חיזוי תנועות עבר")
                colp1, colp2 = st.columns([3, 1])
                with colp1:
                    lookahead = st.selectbox("חלון חיזוי (ימים):", [3, 5, 7], index=1, key=f"look_{sel}")
                    stat_tol = st.slider("סף דמיון סטטיסטי (אחוזי שונות):", 5, 50, 15, key=f"tol_{sel}")
                with colp2:
                    if st.button("הרץ חיזוי עבור " + sel, key=f"pred_btn_{sel}"):
                        with st.spinner("מריץ חיזוי..."):
                            try:
                                hist_full = load_history(sel, period="24mo")
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
                                        wsum, wtot = 0, 0
                                        heur_weights = {"compression": 0.25, "rvol": 0.25, "trend": 0.2, "macd": 0.15, "proximity": 0.15}
                                        for k, wght in heur_weights.items():
                                            wtot += wght
                                            wsum += comps.get(k, 0) * wght
                                        ml_prob = float(min(0.99, max(0.01, wsum / (wtot * 100))))
                                    st.success("חיזוי הושלם")
                                    st.write("**חיזוי סטטיסטי**")
                                    st.write(f"מספר חלונות דומים בעבר: **{stat['count']}**, הצלחות: **{stat['successes']}**, שיעור הצלחה: **{round(stat['rate']*100,1)}%**")
                                    st.write("**זיהוי תבנית (VCP-like)**")
                                    st.write(f"מצב: **{pat['match']}** — {pat['desc']}")
                                    st.write("**חיזוי הסתברותי (מודל)**")
                                    st.write(f"הסתברות לפריצה בתוך {lookahead} ימים: **{round(ml_prob*100,1)}%**")
                                    rec = {
                                        "Ticker": sel, "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "stat_count": stat["count"], "stat_successes": stat["successes"],
                                        "stat_rate": stat["rate"], "pattern_match": pat["match"],
                                        "pattern_desc": pat["desc"], "ml_prob": ml_prob
                                    }
                                    if save_prediction_record(rec):
                                        st.info("תחזית נשמרה ב־predictions.csv")
                                    last_close_full = safe_last(hist_full["Close"])
                                    scan_row = {
                                        "Ticker": sel, "Score": res["score"], "Confidence": res["confidence"],
                                        "Risk": res["risk"],
                                        "Price": round(float(last_close_full), 2) if not is_bad_number(last_close_full) else np.nan,
                                        "Note": res["note"] + " | prediction",
                                        "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    if save_single_scan_result(scan_row):
                                        st.info("שורת סריקה נשמרה ב־scan_results.csv")
                                    else:
                                        st.warning("לא הצלחנו לשמור את שורת הסריקה")
                            except Exception as e:
                                st.error(f"שגיאה בהרצת חיזוי: {e}")

                # ---------- הוספה לתיק עם ניהול סיכון ----------
                st.markdown("---")
                render_add_to_portfolio_form(sel, sel_price, df_plot, key_suffix=f"scan_{sel}", settings=account_settings)
            else:
                st.warning("אין פרטים לטיקר זה")

            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("הורד תוצאות כ־CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")
    else:
        st.info("הרץ סריקה כדי לראות תוצאות.")

# --- טאב תיק ההשקעות ---
with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        total_risk_open = 0.0
        for i, row in portfolio.iterrows():
            try:
                curr = float(yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1])
            except Exception:
                curr = np.nan
            portfolio.loc[i, 'CurrentPrice'] = round(curr, 2) if not is_bad_number(curr) else np.nan

            entry = row.get('EntryPrice', np.nan)
            stop = row.get('StopLoss', np.nan)
            shares = row.get('Shares', np.nan)
            risk_amount = row.get('RiskAmount', np.nan)

            if not is_bad_number(entry) and not is_bad_number(curr) and entry != 0:
                portfolio.loc[i, 'Performance'] = f"{round(((curr - entry) / entry) * 100, 2)}%"
            else:
                portfolio.loc[i, 'Performance'] = "N/A"

            if not is_bad_number(entry) and not is_bad_number(stop) and entry != stop and not is_bad_number(curr):
                r_multiple = (curr - entry) / (entry - stop)
                portfolio.loc[i, 'R_Multiple'] = round(r_multiple, 2)
            else:
                portfolio.loc[i, 'R_Multiple'] = np.nan

            if not is_bad_number(shares) and not is_bad_number(curr):
                portfolio.loc[i, 'PositionValue'] = round(shares * curr, 2)
            else:
                portfolio.loc[i, 'PositionValue'] = np.nan

            # פוזיציה נחשבת "בסיכון פעיל" אם המחיר הנוכחי עדיין מעל הסטופ (long)
            still_at_risk = (not is_bad_number(curr) and not is_bad_number(stop) and curr > stop)
            if still_at_risk and not is_bad_number(risk_amount):
                total_risk_open += float(risk_amount)
                portfolio.loc[i, 'Status'] = "🟢 פעיל"
            elif not is_bad_number(stop) and not is_bad_number(curr) and curr <= stop:
                portfolio.loc[i, 'Status'] = "🔴 מתחת לסטופ"
            else:
                portfolio.loc[i, 'Status'] = "⚪ לא ידוע"

        st.dataframe(portfolio, use_container_width=True)

        st.divider()
        st.subheader("🎯 חשיפת סיכון כוללת בתיק (Portfolio Heat)")
        heat_pct = safe_div(total_risk_open, account_settings["account_size"], default=0.0) * 100
        max_heat = account_settings["max_portfolio_heat_pct"]
        c1, c2, c3 = st.columns(3)
        c1.metric("סיכון פתוח כולל", f"{total_risk_open:,.2f}")
        c2.metric("אחוז מהחשבון בסיכון", f"{heat_pct:.2f}%")
        c3.metric("תקרת סיכון מותרת", f"{max_heat:.2f}%")
        if heat_pct > max_heat:
            st.error(f"⚠️ חריגה מתקרת הסיכון! החשיפה הנוכחית ({heat_pct:.2f}%) גבוהה מהמותר ({max_heat:.2f}%). שקול לצמצם פוזיציות.")
        else:
            st.success("החשיפה הכוללת בתיק בטווח התקין.")

        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        show_buttons(to_manage)

        row_sel = portfolio[portfolio['Ticker'] == to_manage].iloc[-1]
        st.markdown("**עדכון סטופ לוס (טריילינג סטופ)**")
        current_stop = row_sel.get('StopLoss', np.nan)
        with st.form(key="update_stop_form"):
            new_stop = st.number_input("סטופ לוס חדש:", value=float(current_stop) if not is_bad_number(current_stop) else 0.0)
            update_submitted = st.form_submit_button("עדכן סטופ")
            if update_submitted:
                full_pf = get_portfolio_df()
                idxs = full_pf[full_pf['Ticker'] == to_manage].index
                if len(idxs) > 0:
                    full_pf.loc[idxs[-1], 'StopLoss'] = new_stop
                    # עדכון סכום הסיכון בהתאם לסטופ החדש
                    entry_v = full_pf.loc[idxs[-1], 'EntryPrice']
                    shares_v = full_pf.loc[idxs[-1], 'Shares']
                    if not is_bad_number(entry_v) and not is_bad_number(shares_v):
                        full_pf.loc[idxs[-1], 'RiskAmount'] = round(abs(entry_v - new_stop) * shares_v, 2)
                    full_pf.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("הסטופ עודכן בהצלחה")
                    st.rerun()

        if st.button("מחק מניה מהתיק 🗑️"):
            full_pf = get_portfolio_df()
            full_pf = full_pf[full_pf['Ticker'] != to_manage]
            full_pf.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_manage} הוסר מהתיק")
            st.rerun()

        st.divider()
        st.markdown("**הוספת מניה חדשה ידנית לתיק (עם ניהול סיכון)**")
        manual_ticker = st.text_input("הזן טיקר להוספה:", key="manual_add_ticker_input")
        if manual_ticker:
            manual_hist = load_history(manual_ticker.strip().upper(), period="6mo")
            if manual_hist.empty:
                st.warning("לא נמצאו נתונים עבור טיקר זה.")
            else:
                manual_hist = add_indicators(manual_hist)
                manual_price = float(safe_last(manual_hist["Close"]))
                render_add_to_portfolio_form(manual_ticker.strip().upper(), manual_price, manual_hist,
                                              key_suffix=f"manual_{manual_ticker.strip().upper()}", settings=account_settings)
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
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            to_delete = st.multiselect("בחר טיקרים למחיקה מהתחזיות השמורות:", options=sorted(preds['Ticker'].unique().tolist()))
        with col_del2:
            if st.button("מחק נבחרים"):
                if not to_delete:
                    st.warning("לא נבחרו טיקרים למחיקה")
                elif delete_prediction_tickers(to_delete):
                    st.success("התחזיות נמחקו")
                    st.rerun()
                else:
                    st.error("שגיאה במחיקה")
        st.divider()
        if st.button("נקה את כל התחזיות השמורות"):
            if clear_all_predictions():
                st.success("כל התחזיות נמחקו")
                st.rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")
        csv_all = preds.to_csv(index=False).encode('utf-8')
        st.download_button("הורד את כל התחזיות כ־CSV", csv_all, file_name="saved_predictions.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("הוספה מהתחזיות לתיק ההשקעות (עם ניהול סיכון)")
    saved_preds = preds['Ticker'].unique().tolist() if not preds.empty else []
    if saved_preds:
        pick = st.selectbox("בחר טיקר להוספה לתיק:", saved_preds)
        pick_hist = load_history(pick, period="6mo")
        if not pick_hist.empty:
            pick_hist = add_indicators(pick_hist)
            pick_price = float(safe_last(pick_hist["Close"]))
            render_add_to_portfolio_form(pick, pick_price, pick_hist, key_suffix=f"predtab_{pick}", settings=account_settings)
        else:
            st.warning("לא נמצאו נתונים עבור טיקר זה.")

# --- טאב ניהול סיכון ---
with tab4:
    st.header("🎯 ניהול סיכון ופוזיציה")

    st.subheader("הגדרות חשבון")
    with st.form(key="settings_form"):
        acc_size = st.number_input("גודל חשבון", value=float(account_settings["account_size"]), min_value=100.0, step=1000.0)
        risk_pct_default = st.number_input("סיכון ברירת מחדל לעסקה (%)", value=float(account_settings["risk_per_trade_pct"]),
                                            min_value=0.1, max_value=20.0, step=0.1)
        max_heat_pct = st.number_input("תקרת סיכון כוללת לתיק (%)", value=float(account_settings["max_portfolio_heat_pct"]),
                                        min_value=1.0, max_value=100.0, step=0.5)
        save_settings = st.form_submit_button("שמור הגדרות")
        if save_settings:
            new_settings = {"account_size": acc_size, "risk_per_trade_pct": risk_pct_default,
                             "max_portfolio_heat_pct": max_heat_pct}
            if save_account_settings(new_settings):
                st.success("ההגדרות נשמרו")
                st.rerun()
            else:
                st.error("שגיאה בשמירת ההגדרות")

    st.divider()
    st.subheader("🧮 מחשבון גודל פוזיציה עצמאי")
    c1, c2 = st.columns(2)
    with c1:
        calc_account = st.number_input("גודל חשבון לחישוב", value=float(account_settings["account_size"]), min_value=100.0, key="calc_acc")
        calc_risk_pct = st.number_input("אחוז סיכון לעסקה", value=float(account_settings["risk_per_trade_pct"]), min_value=0.1, max_value=20.0, step=0.1, key="calc_risk")
    with c2:
        calc_entry = st.number_input("מחיר כניסה", value=100.0, min_value=0.01, key="calc_entry")
        calc_stop = st.number_input("מחיר סטופ לוס", value=95.0, min_value=0.01, key="calc_stop")

    calc_target = st.number_input("מחיר יעד (אופציונלי, 0=ללא)", value=0.0, min_value=0.0, key="calc_target")

    calc_result = calculate_position_size(calc_account, calc_risk_pct, calc_entry, calc_stop)
    st.write("### תוצאות")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("מס' מניות", calc_result["shares"])
    r2.metric("סכום בסיכון", f"{calc_result['risk_amount']:.2f}")
    r3.metric("שווי פוזיציה", f"{calc_result['position_value']:.2f}")
    r4.metric("סיכון למניה", f"{calc_result['per_share_risk']:.2f}")

    if calc_target > 0 and calc_entry != calc_stop:
        rr_ratio = safe_div(abs(calc_target - calc_entry), abs(calc_entry - calc_stop), default=np.nan)
        if not is_bad_number(rr_ratio):
            st.info(f"יחס סיכוי/סיכון (Risk:Reward) = 1:{rr_ratio:.2f}")

    if calc_entry <= calc_stop:
        st.warning("מחיר הכניסה נמוך או שווה לסטופ — ודא שזו אכן עסקת Long תקינה.")

    st.divider()
    st.subheader("📊 סיכום חשיפת סיכון נוכחית בתיק")
    portfolio_for_heat = get_portfolio_df()
    if portfolio_for_heat.empty:
        st.info("אין פוזיציות פתוחות בתיק כרגע.")
    else:
        total_risk = pd.to_numeric(portfolio_for_heat['RiskAmount'], errors='coerce').fillna(0).sum()
        heat = safe_div(total_risk, account_settings["account_size"], default=0.0) * 100
        st.metric("סה״כ סיכון פתוח (הערכה, ללא בדיקת סטופ בזמן אמת)", f"{total_risk:,.2f} ({heat:.2f}% מהחשבון)")
        if heat > account_settings["max_portfolio_heat_pct"]:
            st.error("⚠️ סך הסיכון בתיק (על בסיס כל הפוזיציות הרשומות) חורג מהתקרה שהוגדרה.")

# ============================
# ניהול תוצאות סריקה שמורות (סייד-בר)
# ============================
st.sidebar.markdown("---")
if st.sidebar.button("נהל תוצאות שמורות"):
    st.sidebar.write("ניהול תוצאות שמורות")
    saved_scans = load_saved_scan_results()
    if saved_scans.empty:
        st.sidebar.info("אין תוצאות סריקה שמורות")
    else:
        st.sidebar.dataframe(saved_scans)
        to_del = st.sidebar.multiselect("בחר טיקרים למחיקה מקובץ הסריקות:", options=sorted(saved_scans['Ticker'].unique().tolist()))
        if st.sidebar.button("מחק טיקרים מסריקות"):
            if not to_del:
                st.sidebar.warning("לא נבחרו טיקרים")
            elif delete_saved_scan_tickers(to_del):
                st.sidebar.success("הפריטים נמחקו מקובץ הסריקות")
            else:
                st.sidebar.error("שגיאה במחיקה")
        if st.sidebar.button("נקה את כל קובץ הסריקות"):
            if clear_all_saved_scans():
                st.sidebar.success("קובץ הסריקות נוקה")
            else:
                st.sidebar.error("שגיאה בניקוי הקובץ")

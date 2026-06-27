# app.py - KEISAR Pro Hunter (with PreBreakouts tab + AgGrid lazy load)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import shutil
import glob
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px

# נסיון לטעון AgGrid - אם לא מותקן, נטפל בזה בריצה
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False

# -------------------------
# עיצוב קל ו‑config
# -------------------------
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
st.markdown(
    """
    <style>
    .app-title {font-size:20px; font-weight:700; margin-bottom:0px;}
    .app-sub {font-size:12px; color: #6c757d; margin-top:2px; margin-bottom:12px;}
    .stButton>button {padding:6px 10px;}
    .dataframe td, .dataframe th {padding:6px 8px;}
    .section {padding:8px 12px; border-radius:6px; background:#ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.04);}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# קבצים ושמות
# -------------------------
SCAN_RESULTS_FILE = 'scan_results.csv'
REJECTIONS_FILE = 'scan_rejections.csv'
PORTFOLIO_FILE = 'portfolio.csv'
BACKUP_DIR = "backups"
LOG_FILE = os.path.join(BACKUP_DIR, "backup_log.csv")
MAX_BACKUPS = 30
os.makedirs(BACKUP_DIR, exist_ok=True)

# -------------------------
# פונקציות עזר לנרמול וכפילויות
# -------------------------
def normalize_ticker(t: str) -> str:
    if not isinstance(t, str):
        return ""
    s = t.strip().upper().replace('.', '-')
    s = ''.join(ch for ch in s if ch.isalnum() or ch == '-')
    return s

def dedupe_preserve_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

# -------------------------
# מטמון לקריאות yfinance
# -------------------------
@st.cache_data(ttl=60*30)
def fetch_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if not df.empty:
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60*30)
def fetch_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}

# -------------------------
# אינדיקטורים
# -------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['STD20'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['MA20'] + 2 * df['STD20']
    df['BB_lower'] = df['MA20'] - 2 * df['STD20']
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['MA20']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=13, adjust=False).mean()
    ma_down = down.ewm(com=13, adjust=False).mean()
    rs = ma_up / ma_down
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=10).mean()
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(span=14, adjust=False).mean()
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    cum_vp = (tp * df['Volume']).cumsum()
    cum_vol = df['Volume'].cumsum()
    df['VWAP'] = cum_vp / cum_vol
    return df.dropna()

# -------------------------
# כללי זיהוי פריצה ואישור
# -------------------------
def is_bollinger_squeeze(df: pd.DataFrame, lookback=20, width_thresh=0.05) -> (bool, float):
    recent = df['BB_width'].iloc[-lookback:]
    current = recent.iloc[-1]
    median_width = recent.median()
    ok = current <= width_thresh or current <= 0.6 * median_width
    return ok, float(current)

def macd_confirmation(df: pd.DataFrame, lookback=3) -> (bool, float):
    try:
        hist_now = df['MACD_hist'].iloc[-1]
        hist_past = df['MACD_hist'].iloc[-1 - lookback]
        ok = hist_now > hist_past and df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]
        return ok, float(hist_now)
    except Exception:
        return False, 0.0

def obv_confirmation(df: pd.DataFrame, lookback=10) -> (bool, float):
    try:
        obv_now = df['OBV'].iloc[-1]
        obv_past = df['OBV'].iloc[-1 - lookback]
        ok = obv_now > obv_past
        return ok, float(obv_now - obv_past)
    except Exception:
        return False, 0.0

def rsi_smart_check(df: pd.DataFrame, rvol_now: float, rvol_threshold: float) -> (bool, str):
    try:
        rsi_val = float(df['RSI'].iloc[-1])
        if rsi_val < 50:
            return False, f"RSI נמוך ({rsi_val:.1f})"
        if rsi_val <= 70:
            return True, f"RSI בטווח טוב ({rsi_val:.1f})"
        atr_ok_flag, atr_ratio = atr_expansion(df, lookback=10)
        if rvol_now >= max(1.5, rvol_threshold) and atr_ok_flag:
            return True, f"RSI גבוה ({rsi_val:.1f}) אך מאושר (RVOL {rvol_now:.2f}, ATR_ratio {atr_ratio:.2f})"
        return False, f"RSI גבוה ({rsi_val:.1f}) ללא אישור נפח/ATR"
    except Exception as e:
        return False, f"שגיאת RSI: {e}"

def vwap_confirmation(df: pd.DataFrame) -> (bool, float):
    try:
        ok = df['Close'].iloc[-1] > df['VWAP'].iloc[-1]
        return ok, float(df['Close'].iloc[-1] - df['VWAP'].iloc[-1])
    except Exception:
        return False, 0.0

def atr_expansion(df: pd.DataFrame, lookback=10) -> (bool, float):
    try:
        atr_now = df['ATR'].iloc[-1]
        atr_past = df['ATR'].iloc[-1 - lookback]
        ok = atr_now > atr_past
        return ok, float(atr_now / (atr_past + 1e-9))
    except Exception:
        return False, 0.0

# -------------------------
# בדיקות בסיסיות נוספות
# -------------------------
def marketcap_ok(info: dict, min_cap=300_000_000) -> (bool, str):
    try:
        mc = info.get('marketCap') or info.get('market_cap') or 0
        ok = bool(mc and mc >= min_cap)
        reason = "" if ok else f"שווי שוק קטן מ{min_cap:,}"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת קריאת marketCap: {e}"

def avg_volume_ok(df: pd.DataFrame, min_avg_vol=150_000) -> (bool, str):
    try:
        if len(df) < 20:
            return False, "היסטוריה קצרה לחישוב ממוצע נפח 20"
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        ok = avg_vol >= min_avg_vol
        reason = "" if ok else f"ממוצע נפח 20 יום נמוך ({int(avg_vol)})"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת חישוב ממוצע נפח: {e}"

# -------------------------
# כלי גיבוי/שחזור/לוג
# -------------------------
def _write_log(action: str, files: list, note: str = ""):
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"timestamp": ts, "action": action, "files": ";".join(files), "note": note}
    if os.path.exists(LOG_FILE):
        try:
            log_df = pd.read_csv(LOG_FILE)
            log_df = pd.concat([log_df, pd.DataFrame([row])], ignore_index=True)
        except Exception:
            log_df = pd.DataFrame([row])
    else:
        log_df = pd.DataFrame([row])
    log_df.to_csv(LOG_FILE, index=False)

def list_backups():
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")), reverse=True)
    files = [f for f in files if os.path.basename(f) != os.path.basename(LOG_FILE)]
    return files

def create_backup(files_to_backup: list):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backed = []
    for f in files_to_backup:
        if os.path.exists(f):
            base = os.path.basename(f)
            backup_name = f"{os.path.splitext(base)[0]}_{ts}{os.path.splitext(base)[1]}"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            shutil.copy2(f, backup_path)
            backed.append(backup_path)
    _write_log("backup", backed)
    _prune_backups()
    return backed

def _prune_backups():
    backups = list_backups()
    if len(backups) > MAX_BACKUPS:
        to_remove = backups[MAX_BACKUPS:]
        for r in to_remove:
            try:
                os.remove(r)
            except Exception:
                pass
        _write_log("prune", to_remove, note=f"pruned to {MAX_BACKUPS}")

def restore_backup(backup_file: str, restore_files: list):
    restored = []
    for f in restore_files:
        base = os.path.basename(f)
        if os.path.isfile(backup_file):
            src = backup_file
            dst = f
            try:
                shutil.copy2(src, dst)
                restored.append(dst)
            except Exception as e:
                return False, f"שגיאה בשחזור {dst}: {e}"
        else:
            candidates = [p for p in list_backups() if os.path.basename(p).startswith(os.path.splitext(base)[0])]
            if candidates:
                src = candidates[0]
                try:
                    shutil.copy2(src, f)
                    restored.append(f)
                except Exception as e:
                    return False, f"שגיאה בשחזור {f}: {e}"
            else:
                return False, f"לא נמצא גיבוי עבור {base}"
    _write_log("restore", restored, note=f"from {os.path.basename(backup_file)}")
    return True, restored

# -------------------------
# PreBreakout / Intraday helpers
# -------------------------
def find_squeeze_date(df: pd.DataFrame, lookback=60):
    try:
        recent = df['BB_width'].iloc[-lookback:]
        idx = recent.idxmin()
        return idx if not pd.isna(idx) else None
    except Exception:
        return None

def fetch_intraday_volume_series(ticker: str, period: str = "5d", interval: str = "60m"):
    try:
        df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def intraday_rvol_spike(ticker: str, rvol_thresh=1.3):
    try:
        df = fetch_intraday_volume_series(ticker, period="5d", interval="60m")
        if df.empty or 'Volume' not in df.columns:
            return False, None
        vol = df['Volume']
        rvol = vol / vol.rolling(window=10).mean()
        last_rvol = float(rvol.dropna().iloc[-1]) if len(rvol.dropna())>0 else 0.0
        return last_rvol >= rvol_thresh, last_rvol
    except Exception:
        return False, None

# -------------------------
# ממשק משתמש - כותרת ותיאור
# -------------------------
st.markdown('<div class="app-title">KEISAR Pro Hunter — Breakout Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">סריקה טכנית מתקדמת לזיהוי פריצות ו‑pre‑breakouts. השתמש ב‑sidebar להגדרות מהירות.</div>', unsafe_allow_html=True)

# -------------------------
# Sidebar - הגדרות מסודרות
# -------------------------
with st.sidebar:
    st.header("הגדרות סריקה")
    with st.expander("Basic settings", expanded=True):
        pct_from_low = st.number_input("אחוז מקירוב לשפל 52 שבועות (%)", value=3.0, min_value=0.0, max_value=50.0) / 100.0
        if 'bb_width_thresh' not in st.session_state:
            st.session_state['bb_width_thresh'] = 0.05
        bb_width_thresh = st.number_input("סף רוחב Bollinger (BB width)", value=st.session_state['bb_width_thresh'], min_value=0.001, max_value=1.0, step=0.005, key="bb_width_widget")
        if 'rvol_threshold' not in st.session_state:
            st.session_state['rvol_threshold'] = 1.2
        rvol_threshold = st.number_input("סף RVOL לאיסוף", value=st.session_state['rvol_threshold'], min_value=0.5, max_value=10.0, key="rvol_widget")
        if 'rsi_threshold' not in st.session_state:
            st.session_state['rsi_threshold'] = 75
        rsi_threshold = st.number_input("סף RSI מקסימלי (מוצע)", value=st.session_state['rsi_threshold'], min_value=30, max_value=90, key="rsi_widget")
        if 'min_marketcap' not in st.session_state:
            st.session_state['min_marketcap'] = 300_000_000
        min_marketcap = st.number_input("מינימום שווי שוק (USD)", value=st.session_state['min_marketcap'], step=50_000_000, key="mc_widget")
        if 'min_avg_vol' not in st.session_state:
            st.session_state['min_avg_vol'] = 150_000
        min_avg_vol = st.number_input("ממוצע נפח מינימלי (20 יום)", value=st.session_state['min_avg_vol'], step=10_000, key="avgvol_widget")

    with st.expander("Advanced settings", expanded=False):
        if 'chunk_size' not in st.session_state:
            st.session_state['chunk_size'] = 25
        chunk_size = st.number_input("גודל קבוצה לסריקה (chunk size)", min_value=5, max_value=200, value=st.session_state['chunk_size'], step=5, key="chunk_widget")
        DEBUG_MODE = st.checkbox("מצב Debug - הצג Warnings (אל תדחה אוטומטית)", value=False, key="debug_widget")
        enable_intraday = st.checkbox("הפעל בדיקות אינטרדייליות (איטי)", value=False, help="הפעל רק אם רוצים RVOL אינטרדיילי; עלול להאט")

    with st.expander("PreBreakout / Intraday", expanded=False):
        prebreak_squeeze_lookback = st.number_input("ימים לחיפוש squeeze (PreBreakout)", min_value=5, max_value=120, value=14, step=1)
        intraday_rvol_thresh = st.number_input("סף RVOL אינטרדיילי לזיהוי spike", min_value=1.0, max_value=5.0, value=1.3, step=0.1)

    st.markdown("---")
    st.write("קבצים")
    uploaded_sidebar = st.file_uploader("העלה קובץ CSV (טיקר בכל שורה)", accept_multiple_files=True, type="csv", key="sidebar_uploader")
    st.markdown("---")
    st.write("פעולות")
    run_scan_btn = st.button("הפעל סריקה", key="run_scan_sidebar")
    scan_single_btn = st.button("סרוק קובץ נבחר", key="scan_single_sidebar")

# -------------------------
# בחירת קובץ יחיד ותצוגה מקדימה
# -------------------------
col_left, col_right = st.columns([1, 3])
with col_left:
    st.markdown("**בחר קובץ CSV לסריקה (אופציונלי)**")
    local_csvs = sorted([f for f in os.listdir('.') if f.endswith('.csv') and f not in [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]])
    selected_local = st.selectbox("קבצי CSV בתיקייה", ["-- בחר קובץ --"] + local_csvs) if local_csvs else None
    if selected_local == "-- בחר קובץ --":
        selected_local = None
    uploaded_single = st.file_uploader("או העלה קובץ CSV חדש", accept_multiple_files=False, type="csv", key="single_uploader_main")
    preview_placeholder = st.empty()
    def read_tickers_from_fileobj(fileobj):
        try:
            if isinstance(fileobj, str):
                df = pd.read_csv(fileobj, header=None, dtype=str)
            else:
                fileobj.seek(0)
                df = pd.read_csv(fileobj, header=None, dtype=str)
            raw = df.iloc[:, 0].dropna().astype(str).tolist()
            normalized = [normalize_ticker(t) for t in raw]
            normalized = [t for t in normalized if t]
            return dedupe_preserve_order(normalized)
        except Exception:
            return []
    preview_tickers = []
    if uploaded_single:
        preview_tickers = read_tickers_from_fileobj(uploaded_single)
        preview_placeholder.write(f"קובץ שהועלה: {uploaded_single.name} — {len(preview_tickers)} טיקרים")
        preview_placeholder.dataframe(pd.DataFrame(preview_tickers, columns=["Ticker"]).head(50), use_container_width=True)
    elif selected_local:
        try:
            preview_tickers = read_tickers_from_fileobj(selected_local)
            preview_placeholder.write(f"קובץ מקומי: {selected_local} — {len(preview_tickers)} טיקרים")
            preview_placeholder.dataframe(pd.DataFrame(preview_tickers, columns=["Ticker"]).head(50), use_container_width=True)
        except Exception:
            preview_placeholder.warning("לא ניתן לקרוא את הקובץ המקומי שנבחר.")

with col_right:
    st.markdown("**סיכום מהיר**")
    m1, m2, m3 = st.columns(3)
    m1.metric("טיקרים לניתוח", "—")
    m2.metric("תוצאות (עברו סינון)", "—")
    m3.metric("PreBreakouts", "—")

# -------------------------
# טעינת טיקרים כללית
# -------------------------
tickers = []
if uploaded_sidebar:
    for f in uploaded_sidebar:
        try:
            tdf = pd.read_csv(f, header=None, dtype=str)
            raw = tdf.iloc[:, 0].dropna().astype(str).tolist()
            normalized = [normalize_ticker(t) for t in raw]
            tickers.extend(normalized)
        except Exception:
            continue
elif uploaded_single:
    tickers = read_tickers_from_fileobj(uploaded_single)
elif selected_local:
    tickers = read_tickers_from_fileobj(selected_local)
else:
    local_files = [f for f in os.listdir('.') if f.endswith('.csv') and f not in [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]]
    for file in local_files:
        try:
            tdf = pd.read_csv(file, header=None, dtype=str)
            raw = tdf.iloc[:, 0].dropna().astype(str).tolist()
            normalized = [normalize_ticker(t) for t in raw]
            tickers.extend(normalized)
        except Exception:
            continue

tickers = [t for t in tickers if t]
tickers = dedupe_preserve_order(tickers)
st.session_state['tickers'] = tickers
st.session_state['last_ticker_count'] = len(tickers)
with col_right:
    m1.metric("טיקרים לניתוח", f"{len(tickers)}")

# -------------------------
# פונקציית סריקה (עם תמיכה ב‑enable_intraday)
# -------------------------
def run_scan_on_list(tickers_list, chunk_size=25, enable_intraday_flag=False):
    total = len(tickers_list)
    progress = st.progress(0)
    results = []
    rejections = []
    prebreak_count = 0
    for i in range(0, total, chunk_size):
        batch = tickers_list[i:i+chunk_size]
        for t in batch:
            reasons = []
            prebreak_flag = False
            intraday_spike = False
            intraday_rvol = None
            info = fetch_info(t)
            hist = fetch_history(t, period="1y", interval="1d")
            if hist.empty or len(hist) < 60:
                reasons.append("היסטוריה חסרה/קצרה")
                if not DEBUG_MODE:
                    rejections.append({"Ticker": t, "Reasons": "; ".join(reasons)})
                    continue
            if not hist.empty:
                df = add_indicators(hist)
            else:
                df = None

            if df is not None:
                ok_mc, r = marketcap_ok(info, min_marketcap)
                if not ok_mc: reasons.append(r)
                ok_volavg, r = avg_volume_ok(df, min_avg_vol)
                if not ok_volavg: reasons.append(r)

                squeeze_ok, squeeze_val = is_bollinger_squeeze(df, lookback=20, width_thresh=bb_width_thresh)
                if not squeeze_ok:
                    reasons.append(f"לא דחיסה (BB width {squeeze_val:.3f})")

                obv_ok, obv_delta = obv_confirmation(df, lookback=10)
                if not obv_ok:
                    reasons.append("OBV לא מאשר איסוף")

                rvol_now = float(df['RVOL'].iloc[-1])
                if rvol_now < rvol_threshold:
                    reasons.append(f"RVOL נמוך ({rvol_now:.2f})")

                macd_ok, macd_hist = macd_confirmation(df, lookback=3)
                if not macd_ok:
                    reasons.append("MACD לא מאשר")

                rsi_ok_flag, rsi_msg = rsi_smart_check(df, rvol_now, rvol_threshold)
                if not rsi_ok_flag:
                    reasons.append(rsi_msg)
                else:
                    if rsi_msg.startswith("Warning"):
                        reasons.append(rsi_msg)

                vwap_ok_flag, vwap_diff = vwap_confirmation(df)
                if not vwap_ok_flag:
                    reasons.append("מחיר מתחת ל‑VWAP")

                atr_ok, atr_ratio = atr_expansion(df, lookback=10)
                if not atr_ok:
                    reasons.append(f"ATR לא מראה הרחבה ({atr_ratio:.2f})")

                # PreBreakout logic
                squeeze_date = find_squeeze_date(df, lookback=60)
                days_since_squeeze = None
                if squeeze_date is not None:
                    days_since_squeeze = (df.index[-1].date() - squeeze_date.date()).days
                if enable_intraday_flag:
                    intraday_spike, intraday_rvol = intraday_rvol_spike(t, rvol_thresh=intraday_rvol_thresh)
                # תנאי PreBreakout: squeeze קרוב, OBV עולה, RVOL מתחיל לעלות או spike אינטרדיילי
                if squeeze_date is not None and days_since_squeeze is not None and days_since_squeeze <= prebreak_squeeze_lookback:
                    if obv_ok and (rvol_now >= max(1.05, rvol_threshold*0.8) or intraday_spike):
                        prebreak_flag = True

            if reasons and not DEBUG_MODE:
                rejections.append({"Ticker": t, "Reasons": "; ".join(reasons)})
                continue

            if df is not None:
                obv_change = float(df['OBV'].iloc[-1] - df['OBV'].iloc[-11]) if len(df) > 11 else 0.0
                results.append({
                    "Ticker": t,
                    "Price": float(df['Close'].iloc[-1]),
                    "52w_low": float(df['Close'].min()),
                    "BB_width": float(df['BB_width'].iloc[-1]),
                    "RVOL": float(df['RVOL'].iloc[-1]),
                    "OBV_change_10d": obv_change,
                    "MACD_hist": float(df['MACD_hist'].iloc[-1]),
                    "RSI": float(df['RSI'].iloc[-1]),
                    "VWAP_diff": float(df['Close'].iloc[-1] - df['VWAP'].iloc[-1]),
                    "ATR": float(df['ATR'].iloc[-1]),
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": float(df['Volume'].rolling(20).mean().iloc[-1]),
                    "PreBreakout": prebreak_flag,
                    "IntradayRVOL": float(intraday_rvol) if intraday_rvol is not None else None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })
                if prebreak_flag:
                    prebreak_count += 1
            else:
                results.append({
                    "Ticker": t,
                    "Price": None,
                    "52w_low": None,
                    "BB_width": None,
                    "RVOL": None,
                    "OBV_change_10d": None,
                    "MACD_hist": None,
                    "RSI": None,
                    "VWAP_diff": None,
                    "ATR": None,
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": None,
                    "PreBreakout": prebreak_flag,
                    "IntradayRVOL": None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })

            time.sleep(0.03)
        progress.progress(min(1.0, (i + chunk_size) / total))
    progress.empty()
    return results, rejections, prebreak_count

# -------------------------
# כפתורי הפעלה מרכזיים
# -------------------------
run_scan_main = st.button("הפעל סריקה (מרכז)", key="run_scan_main")
scan_single_main = st.button("סרוק קובץ נבחר (מרכז)", key="scan_single_main")

do_scan = run_scan_btn or run_scan_main
do_scan_single = scan_single_btn or scan_single_main

# -------------------------
# ביצוע סריקה לפי בחירה
# -------------------------
df_res = pd.DataFrame()
df_rej = pd.DataFrame()
if do_scan_single:
    if uploaded_single:
        tickers_to_scan = read_tickers_from_fileobj(uploaded_single)
    elif selected_local:
        tickers_to_scan = read_tickers_from_fileobj(selected_local)
    else:
        st.warning("לא נבחר קובץ יחיד. בחר קובץ או העלה קובץ.")
        tickers_to_scan = []

    if tickers_to_scan:
        st.info(f"מריץ סריקה על {len(tickers_to_scan)} טיקרים מהקובץ הנבחר...")
        results, rejections, prebreak_count = run_scan_on_list(tickers_to_scan, chunk_size=int(chunk_size), enable_intraday_flag=enable_intraday)
        # הסרת כפילויות בתוצאות
        seen = set()
        unique_results = []
        for r in results:
            t = normalize_ticker(r.get('Ticker', ''))
            if not t or t in seen:
                continue
            seen.add(t)
            r['Ticker'] = t
            unique_results.append(r)
        df_res = pd.DataFrame(unique_results).sort_values(by=['PreBreakout','OBV_change_10d','RVOL'], ascending=[False,False,False], na_position='last')
        df_res.to_csv(SCAN_RESULTS_FILE, index=False)
        with col_right:
            m2.metric("תוצאות (עברו סינון)", f"{len(df_res)}")
            pre_count = int(df_res['PreBreakout'].sum()) if 'PreBreakout' in df_res.columns else 0
            m3.metric("PreBreakouts", f"{pre_count}")
        st.subheader("תוצאות סריקה (קובץ נבחר)")
        # טאב להצגה: All / PreBreakouts / AgGrid
        tab_all, tab_pre, tab_ag = st.tabs(["All results", "PreBreakouts", "AgGrid (Interactive)"])
        with tab_all:
            st.dataframe(df_res, use_container_width=True)
        with tab_pre:
            if 'PreBreakout' in df_res.columns:
                df_pre = df_res[df_res['PreBreakout'] == True]
                st.write(f"נמצאו {len(df_pre)} PreBreakouts")
                st.dataframe(df_pre, use_container_width=True)
            else:
                st.info("אין שדה PreBreakout בתוצאות.")
        with tab_ag:
            if not AGGRID_AVAILABLE:
                st.warning("AgGrid לא מותקן. להרצה אינטראקטיבית התקן: pip install streamlit-aggrid")
            else:
                if df_res.empty:
                    st.info("אין תוצאות להצגה ב‑AgGrid.")
                else:
                    gb = GridOptionsBuilder.from_dataframe(df_res)
                    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
                    gb.configure_selection(selection_mode="single", use_checkbox=True)
                    grid_options = gb.build()
                    AgGrid(df_res, gridOptions=grid_options, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

        if rejections:
            rej_norm = []
            seen_r = set()
            for rr in rejections:
                t = normalize_ticker(rr.get('Ticker', ''))
                if not t:
                    continue
                if t in seen_r:
                    continue
                seen_r.add(t)
                rej_norm.append({"Ticker": t, "Reasons": rr.get('Reasons', '')})
            df_rej = pd.DataFrame(rej_norm)
            df_rej['PrimaryReason'] = df_rej['Reasons'].apply(lambda x: x.split(';')[0] if isinstance(x, str) and x else '')
            df_rej.to_csv(REJECTIONS_FILE, index=False)
            st.subheader("טיקרים שנדחו וסיבות")
            st.dataframe(df_rej, use_container_width=True)
            st.download_button("⬇️ הורד דחיות CSV", data=df_rej.to_csv(index=False), file_name=REJECTIONS_FILE, mime='text/csv')
    else:
        st.info("אין טיקרים לקובץ הנבחר.")

elif do_scan:
    if not st.session_state.get('tickers'):
        st.warning("אין טיקרים להרצה. העלה קובץ CSV או הנח קבצי CSV בתיקייה.")
    else:
        st.info(f"מריץ סריקה על {len(st.session_state['tickers'])} טיקרים...")
        results, rejections, prebreak_count = run_scan_on_list(st.session_state['tickers'], chunk_size=int(chunk_size), enable_intraday_flag=enable_intraday)
        seen = set()
        unique_results = []
        for r in results:
            t = normalize_ticker(r.get('Ticker', ''))
            if not t or t in seen:
                continue
            seen.add(t)
            r['Ticker'] = t
            unique_results.append(r)
        df_res = pd.DataFrame(unique_results).sort_values(by=['PreBreakout','OBV_change_10d','RVOL'], ascending=[False,False,False], na_position='last')
        df_res.to_csv(SCAN_RESULTS_FILE, index=False)
        with col_right:
            m2.metric("תוצאות (עברו סינון)", f"{len(df_res)}")
            pre_count = int(df_res['PreBreakout'].sum()) if 'PreBreakout' in df_res.columns else 0
            m3.metric("PreBreakouts", f"{pre_count}")
        st.subheader("תוצאות סריקה")
        tab_all, tab_pre, tab_ag = st.tabs(["All results", "PreBreakouts", "AgGrid (Interactive)"])
        with tab_all:
            st.dataframe(df_res, use_container_width=True)
        with tab_pre:
            if 'PreBreakout' in df_res.columns:
                df_pre = df_res[df_res['PreBreakout'] == True]
                st.write(f"נמצאו {len(df_pre)} PreBreakouts")
                st.dataframe(df_pre, use_container_width=True)
            else:
                st.info("אין שדה PreBreakout בתוצאות.")
        with tab_ag:
            if not AGGRID_AVAILABLE:
                st.warning("AgGrid לא מותקן. להרצה אינטראקטיבית התקן: pip install streamlit-aggrid")
            else:
                if df_res.empty:
                    st.info("אין תוצאות להצגה ב‑AgGrid.")
                else:
                    gb = GridOptionsBuilder.from_dataframe(df_res)
                    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
                    gb.configure_selection(selection_mode="single", use_checkbox=True)
                    grid_options = gb.build()
                    AgGrid(df_res, gridOptions=grid_options, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

        if rejections:
            rej_norm = []
            seen_r = set()
            for rr in rejections:
                t = normalize_ticker(rr.get('Ticker', ''))
                if not t or t in seen_r:
                    continue
                seen_r.add(t)
                rej_norm.append({"Ticker": t, "Reasons": rr.get('Reasons', '')})
            df_rej = pd.DataFrame(rej_norm)
            df_rej['PrimaryReason'] = df_rej['Reasons'].apply(lambda x: x.split(';')[0] if isinstance(x, str) and x else '')
            df_rej.to_csv(REJECTIONS_FILE, index=False)
            st.subheader("טיקרים שנדחו וסיבות")
            st.dataframe(df_rej, use_container_width=True)
            st.download_button("⬇️ הורד דחיות CSV", data=df_rej.to_csv(index=False), file_name=REJECTIONS_FILE, mime='text/csv')

# -------------------------
# הצגת תוצאות קודמות וגרפים
# -------------------------
st.markdown("---")
if os.path.exists(SCAN_RESULTS_FILE):
    st.subheader("תוצאות סריקה קודמות")
    try:
        df_prev = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_prev, use_container_width=True)
        sel = st.selectbox("בחר מניה להצגה מתוך תוצאות קודמות", df_prev['Ticker'].tolist(), key="prev_select")
        if st.button("הצג גרף מהתוצאות הקודמות"):
            hist = fetch_history(sel, period="1y")
            if hist.empty:
                st.warning("היסטוריה לא זמינה להצגה.")
            else:
                df_plot = add_indicators(hist)
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5, 0.15, 0.15, 0.2])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                             low=df_plot['Low'], close=df_plot['Close'], name='Candles'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], line=dict(color='blue'), name='MA20'), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='lightgrey'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RVOL'], line=dict(color='orange'), name='RVOL'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['OBV'], line=dict(color='green'), name='OBV'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD_hist'], line=dict(color='purple'), name='MACD_hist'), row=4, col=1)
                fig.update_layout(height=900, showlegend=True, title_text=f"{sel} - גרף מפורט")
                st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("לא ניתן לקרוא את קובץ התוצאות הקודם.")

st.markdown("---")
st.write("הערה: זהו כלי מחקר טכני בלבד ולא ייעוץ השקעות.")

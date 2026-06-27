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

# -------------------------
# הגדרות כלליות
# -------------------------
st.set_page_config(page_title="KEISAR Pro Hunter - Breakout Scanner", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
REJECTIONS_FILE = 'scan_rejections.csv'
PORTFOLIO_FILE = 'portfolio.csv'
BACKUP_DIR = "backups"
LOG_FILE = os.path.join(BACKUP_DIR, "backup_log.csv")
MAX_BACKUPS = 30
os.makedirs(BACKUP_DIR, exist_ok=True)

# -------------------------
# עזרי נרמול וכפילויות
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
        # שימוש ב‑yfinance history
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        # ודא אינדקס מסוג datetime
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
        # RSI > 70 -> דרוש אישור נפח/ATR
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
# פונקציות PreBreakout / Intraday
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
        # שימוש ב‑yf.download כדי לקבל נתוני אינטרדיי
        df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def intraday_rvol_spike(ticker: str, rvol_thresh=1.3):
    """
    מחזיר True אם יש spike בנפח אינטרדיילי ב‑period האחרון.
    מחשב RVOL על בסיס ממוצע 10 של נפח אינטרדיילי.
    """
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
# UI - הגדרות סריקה
# -------------------------
st.title("◈ KEISAR Pro Hunter — Breakout Scanner (with PreBreakout)")

left, right = st.columns([1, 3])
with left:
    st.subheader("הגדרות סריקה")
    if 'bb_width_thresh' not in st.session_state:
        st.session_state['bb_width_thresh'] = 0.05
    if 'rvol_threshold' not in st.session_state:
        st.session_state['rvol_threshold'] = 1.2
    if 'rsi_threshold' not in st.session_state:
        st.session_state['rsi_threshold'] = 75
    if 'min_marketcap' not in st.session_state:
        st.session_state['min_marketcap'] = 300_000_000
    if 'min_avg_vol' not in st.session_state:
        st.session_state['min_avg_vol'] = 150_000
    if 'chunk_size' not in st.session_state:
        st.session_state['chunk_size'] = 25

    pct_from_low = st.number_input("אחוז מקירוב לשפל 52 שבועות (%) — לא חובה כאן", value=3.0, min_value=0.0, max_value=50.0) / 100.0
    bb_width_thresh = st.number_input("סף רוחב Bollinger (BB width) לפריצה", value=st.session_state['bb_width_thresh'], min_value=0.001, max_value=1.0, step=0.005, key="bb_width_widget")
    rvol_threshold = st.number_input("סף RVOL לאיסוף", value=st.session_state['rvol_threshold'], min_value=0.5, max_value=10.0, key="rvol_widget")
    rsi_threshold = st.number_input("סף RSI מקסימלי לאישור פריצה", value=st.session_state['rsi_threshold'], min_value=30, max_value=90, key="rsi_widget")
    min_marketcap = st.number_input("מינימום שווי שוק (USD)", value=st.session_state['min_marketcap'], step=50_000_000, key="mc_widget")
    min_avg_vol = st.number_input("ממוצע נפח מינימלי (20 יום)", value=st.session_state['min_avg_vol'], step=10_000, key="avgvol_widget")
    chunk_size = st.number_input("גודל קבוצה לסריקה (chunk size)", min_value=5, max_value=200, value=st.session_state['chunk_size'], step=5, key="chunk_widget")
    prebreak_squeeze_lookback = st.number_input("מספר ימים לחיפוש squeeze (PreBreakout)", min_value=5, max_value=120, value=14, step=1)
    intraday_rvol_thresh = st.number_input("סף RVOL אינטרדיילי לזיהוי spike", min_value=1.0, max_value=5.0, value=1.3, step=0.1)
    DEBUG_MODE = st.checkbox("מצב Debug - אל תדחה אוטומטית, הצג Warnings", value=False, key="debug_widget")
    run_scan = st.button("הפעל סריקה")

with right:
    st.subheader("תוצאות וסריקה")
    results_placeholder = st.empty()

# -------------------------
# בחירת קובץ CSV יחיד לסריקה
# -------------------------
st.markdown("### בחר קובץ CSV לסריקה (סריקה על קובץ יחיד)")
col_file, col_preview = st.columns([2, 3])

local_csvs = sorted([f for f in os.listdir('.') if f.endswith('.csv') and f not in [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]])

with col_file:
    st.write("**בחר קובץ מקומי**")
    selected_local = None
    if local_csvs:
        selected_local = st.selectbox("קבצי CSV בתיקייה", ["-- בחר קובץ --"] + local_csvs, key="local_select")
        if selected_local == "-- בחר קובץ --":
            selected_local = None
    else:
        st.info("לא נמצאו קבצי CSV בתיקייה.")

    st.write("או העלה קובץ CSV חדש")
    uploaded_single = st.file_uploader("העלה קובץ CSV (טיקר בכל שורה)", accept_multiple_files=False, type="csv", key="single_uploader")

    scan_single = st.button("🔎 סרוק קובץ נבחר")

with col_preview:
    st.write("**תצוגת טיקרים (דוגמה)**")
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

# -------------------------
# טעינת טיקרים כללית (אם לא משתמשים בסריקה על קובץ יחיד)
# -------------------------
if not scan_single:
    uploaded = st.file_uploader("העלה קבצי CSV (טיקר בכל שורה) או השאר ריק לקריאה מקבצים בתיקייה", accept_multiple_files=True, type="csv", key="multi_uploader")
    tickers = []
    if uploaded:
        for f in uploaded:
            try:
                tdf = pd.read_csv(f, header=None, dtype=str)
                raw = tdf.iloc[:, 0].dropna().astype(str).tolist()
                normalized = [normalize_ticker(t) for t in raw]
                tickers.extend(normalized)
            except Exception:
                continue
    else:
        local_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'scan' not in f and 'rejection' not in f and 'portfolio' not in f]
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
    st.write(f"נמצאו {len(tickers)} טיקרים (מכל הקבצים) לאחר נרמול והסרת כפילויות")
    st.session_state['tickers'] = tickers

# -------------------------
# פונקציית סריקה ב‑chunks עם כללי פריצה + PreBreakout
# -------------------------
def run_scan_on_list(tickers_list, chunk_size=25):
    total = len(tickers_list)
    progress = st.progress(0)
    results = []
    rejections = []
    for i in range(0, total, chunk_size):
        batch = tickers_list[i:i+chunk_size]
        for t in batch:
            reasons = []
            prebreak_flag = False
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

                # RSI חכם
                rsi_ok_flag, rsi_msg = rsi_smart_check(df, rvol_now, rvol_threshold)
                if not rsi_ok_flag:
                    reasons.append(rsi_msg)
                else:
                    # אם זה warning - הוסף כ‑warning (לא דחייה)
                    if rsi_msg.startswith("Warning"):
                        reasons.append(rsi_msg)

                vwap_ok_flag, vwap_diff = vwap_confirmation(df)
                if not vwap_ok_flag:
                    reasons.append("מחיר מתחת ל‑VWAP")

                atr_ok, atr_ratio = atr_expansion(df, lookback=10)
                if not atr_ok:
                    reasons.append(f"ATR לא מראה הרחבה ({atr_ratio:.2f})")

                # --- PreBreakout logic ---
                squeeze_date = find_squeeze_date(df, lookback=60)
                days_since_squeeze = None
                if squeeze_date is not None:
                    days_since_squeeze = (df.index[-1].date() - squeeze_date.date()).days
                # בדיקת intraday RVOL spike (מהירה)
                intraday_spike, intraday_rvol = intraday_rvol_spike(t, rvol_thresh=intraday_rvol_thresh)
                # תנאי PreBreakout: squeeze קרוב, OBV עולה, RVOL מתחיל לעלות או spike אינטרדיילי
                if squeeze_date is not None and days_since_squeeze is not None and days_since_squeeze <= prebreak_squeeze_lookback:
                    if obv_ok and (rvol_now >= max(1.05, rvol_threshold*0.8) or intraday_spike):
                        prebreak_flag = True

            if reasons and not DEBUG_MODE:
                rejections.append({"Ticker": t, "Reasons": "; ".join(reasons)})
                continue

            # הוספת שורה לתוצאות (כולל PreBreakout)
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
                    "IntradayRVOL": float(intraday_rvol) if 'intraday_rvol' in locals() and intraday_rvol is not None else None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })
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

            time.sleep(0.05)
        progress.progress(min(1.0, (i + chunk_size) / total))
    progress.empty()
    return results, rejections

# -------------------------
# הפעלת סריקה על קובץ יחיד אם נבחר
# -------------------------
if scan_single:
    if uploaded_single:
        tickers_to_scan = read_tickers_from_fileobj(uploaded_single)
        st.success(f"טוען {len(tickers_to_scan)} טיקרים מהקובץ שהועלה.")
    elif selected_local:
        tickers_to_scan = read_tickers_from_fileobj(selected_local)
        st.success(f"טוען {len(tickers_to_scan)} טיקרים מההקובץ המקומי: {selected_local}")
    else:
        st.warning("לא נבחר קובץ לסריקה. בחר קובץ מקומי או העלה קובץ.")
        tickers_to_scan = []

    st.session_state['tickers'] = tickers_to_scan

    if tickers_to_scan:
        with st.spinner("מריץ סריקה על הקובץ הנבחר..."):
            results, rejections = run_scan_on_list(tickers_to_scan, chunk_size=int(chunk_size))
        if results:
            # הסרת כפילויות בתוצאות לפי טיקר לפני שמירה
            seen = set()
            unique_results = []
            for r in results:
                t = normalize_ticker(r.get('Ticker', ''))
                if not t:
                    continue
                if t in seen:
                    continue
                seen.add(t)
                r['Ticker'] = t
                unique_results.append(r)
            df_res = pd.DataFrame(unique_results).sort_values(by=['PreBreakout','OBV_change_10d','RVOL'], ascending=[False,False,False], na_position='last')
            df_res.to_csv(SCAN_RESULTS_FILE, index=False)
            st.success(f"סריקה הושלמה: {len(df_res)} תוצאות.")
            st.dataframe(df_res, use_container_width=True)
            st.download_button("⬇️ הורד תוצאות CSV", data=df_res.to_csv(index=False), file_name=SCAN_RESULTS_FILE, mime='text/csv')
        else:
            st.info("לא נמצאו תוצאות שעברו את כל הקריטריונים בקובץ זה.")
        if rejections:
            # נרמול דחיות והסרת כפילויות
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
            st.write("אין דחיות להציג.")

# -------------------------
# הפעלת סריקה רגילה (אם המשתמש לחץ על כפתור ההפעלה הראשי)
# -------------------------
if run_scan and not scan_single:
    if not st.session_state.get('tickers'):
        st.warning("אין טיקרים להרצה. העלה קובץ CSV או הנח קבצי CSV בתיקייה.")
    else:
        with st.spinner("מריץ סריקה ב‑chunks..."):
            results, rejections = run_scan_on_list(st.session_state['tickers'], chunk_size=int(chunk_size))
        if results:
            # הסרת כפילויות בתוצאות לפי טיקר לפני שמירה
            seen = set()
            unique_results = []
            for r in results:
                t = normalize_ticker(r.get('Ticker', ''))
                if not t:
                    continue
                if t in seen:
                    continue
                seen.add(t)
                r['Ticker'] = t
                unique_results.append(r)
            df_res = pd.DataFrame(unique_results).sort_values(by=['PreBreakout','OBV_change_10d','RVOL'], ascending=[False,False,False], na_position='last')
            df_res.to_csv(SCAN_RESULTS_FILE, index=False)
            results_placeholder.success(f"סריקה הושלמה: {len(df_res)} תוצאות (כולל DEBUG).")
            st.subheader("תוצאות שעברו סינון")
            st.dataframe(df_res, use_container_width=True)
            st.download_button("⬇️ הורד תוצאות CSV", data=df_res.to_csv(index=False), file_name=SCAN_RESULTS_FILE, mime='text/csv')
            for idx, row in df_res.reset_index(drop=True).iterrows():
                cols = st.columns([1,1,1,1,1,1,1])
                with cols[0]:
                    st.write(f"**{row['Ticker']}**")
                with cols[1]:
                    st.write(f"מחיר: {row['Price']:.2f}" if pd.notna(row['Price']) else "N/A")
                with cols[2]:
                    st.write(f"RSI: {row['RSI']:.1f}" if pd.notna(row['RSI']) else "N/A")
                with cols[3]:
                    st.write(f"RVOL: {row['RVOL']:.2f}" if pd.notna(row['RVOL']) else "N/A")
                with cols[4]:
                    st.write(f"BBw: {row['BB_width']:.3f}" if pd.notna(row['BB_width']) else "N/A")
                with cols[5]:
                    st.write(f"PreBreakout: {'Yes' if row.get('PreBreakout') else 'No'}")
                btn_key = f"show_{row['Ticker']}_{idx}"
                with cols[6]:
                    if st.button("הצג גרף", key=btn_key):
                        hist = fetch_history(row['Ticker'], period="1y")
                        if hist.empty:
                            st.warning("היסטוריה לא זמינה להצגה.")
                        else:
                            df_plot = add_indicators(hist)
                            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5, 0.15, 0.15, 0.2])
                            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                                         low=df_plot['Low'], close=df_plot['Close'], name='Candles'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], line=dict(color='blue'), name='MA20'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_upper'], line=dict(color='lightgrey'), name='BB_upper', opacity=0.5), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_lower'], line=dict(color='lightgrey'), name='BB_lower', opacity=0.5), row=1, col=1)
                            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='lightgrey'), row=2, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RVOL'], line=dict(color='orange'), name='RVOL'), row=2, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['OBV'], line=dict(color='green'), name='OBV'), row=3, col=1)
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD_hist'], line=dict(color='purple'), name='MACD_hist'), row=4, col=1)
                            fig.update_layout(height=900, showlegend=True, title_text=f"{row['Ticker']} - גרף מפורט")
                            st.plotly_chart(fig, use_container_width=True)
                            st.write(f"מחיר נוכחי: **{row['Price']:.2f}** | RSI: **{row['RSI']:.1f}** | RVOL: **{row['RVOL']:.2f}**")
                            add_key = f"add_{row['Ticker']}_{idx}"
                            if st.button("הוסף לתיק", key=add_key):
                                # מניעת כפילויות בעת הוספה לתיק
                                ticker_to_add = normalize_ticker(row['Ticker'])
                                if os.path.exists(PORTFOLIO_FILE):
                                    p_df = pd.read_csv(PORTFOLIO_FILE, dtype=str)
                                    existing = set(p_df['Ticker'].astype(str).str.upper().tolist()) if 'Ticker' in p_df.columns else set()
                                else:
                                    p_df = pd.DataFrame(columns=["Ticker","AddedAt","Price"])
                                    existing = set()
                                if ticker_to_add in existing:
                                    st.info(f"{ticker_to_add} כבר בתיק — לא נוסף שוב.")
                                else:
                                    p_row = {"Ticker": ticker_to_add, "AddedAt": datetime.utcnow().isoformat(), "Price": row['Price']}
                                    p_df = pd.concat([p_df, pd.DataFrame([p_row])], ignore_index=True)
                                    p_df.to_csv(PORTFOLIO_FILE, index=False)
                                    st.success(f"{ticker_to_add} נוסף לתיק.")
        else:
            results_placeholder.info("לא נמצאו תוצאות שעברו את כל הקריטריונים.")
            df_res = pd.DataFrame(columns=["Ticker","Price","52w_low","BB_width","RVOL","OBV_change_10d","MACD_hist","RSI","VWAP_diff","ATR","MarketCap","AvgVol20","PreBreakout","IntradayRVOL","Warnings"])

        if rejections:
            # נרמול דחיות והסרת כפילויות
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
            st.write("אין דחיות להציג.")

# -------------------------
# Auto-Tune: ניתוח ספים אוטומטי על דגימה של טיקרים
# -------------------------
def compute_indicator_sample_stats(tickers_sample, max_samples=300):
    rows = []
    count = 0
    for t in tickers_sample:
        if count >= max_samples:
            break
        hist = fetch_history(t, period="1y", interval="1d")
        if hist.empty or len(hist) < 60:
            continue
        try:
            df = add_indicators(hist)
        except Exception:
            continue
        try:
            bbw = float(df['BB_width'].iloc[-1])
            rvol = float(df['RVOL'].iloc[-1])
            avgvol = float(df['Volume'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
            rsi = float(df['RSI'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])
            rows.append({"Ticker": t, "BB_width": bbw, "RVOL": rvol, "AvgVol20": avgvol, "RSI": rsi, "ATR": atr})
            count += 1
        except Exception:
            continue
    return pd.DataFrame(rows)

def suggest_thresholds_from_stats(df_stats, percentiles=None):
    if percentiles is None:
        percentiles = {
            "BB_width": 20,
            "RVOL": 75,
            "AvgVol20": 50,
            "RSI": 90,
            "ATR": 60
        }
    suggestions = {}
    for k, p in percentiles.items():
        if k not in df_stats.columns or df_stats[k].dropna().empty:
            suggestions[k] = None
            continue
        val = float(np.percentile(df_stats[k].dropna(), p))
        suggestions[k] = val
    return suggestions

st.markdown("### Auto‑Tune — כוונון ספים אוטומטי")
with st.expander("הפעל Auto‑Tune כדי לקבל המלצות ספים לפי דגימה של הטיקרים"):
    st.write("הפיצ׳ר ינתח דגימה של הטיקרים (עד N) ויחזיר המלצות לפרמטרים: BB width, RVOL, AvgVol20, RSI, ATR.")
    sample_size = st.number_input("גודל דגימה לניתוח (max)", min_value=50, max_value=2000, value=500, step=50, key="autotune_sample")
    percentile_bb = st.slider("פרסנטיל ל‑BB width (קטן = דחיסה יותר קפדנית)", min_value=1, max_value=50, value=20, key="autotune_bb")
    percentile_rvol = st.slider("פרסנטיל ל‑RVOL (גבוה = דרוש נפח חזק יותר)", min_value=50, max_value=100, value=75, key="autotune_rvol")
    percentile_avgvol = st.slider("פרסנטיל ל‑AvgVol20 (ממוצע נפח מינימלי)", min_value=10, max_value=90, value=50, key="autotune_avgvol")
    percentile_rsi = st.slider("פרסנטיל ל‑RSI (מקסימום מקובל)", min_value=60, max_value=100, value=90, key="autotune_rsi")
    percentile_atr = st.slider("פרסנטיל ל‑ATR (אישור הרחבת תנודתיות)", min_value=10, max_value=100, value=60, key="autotune_atr")
    run_autotune = st.button("Auto‑Tune — נתח והצע ספים", key="run_autotune")

    if run_autotune:
        all_tickers = st.session_state.get('tickers', None)
        if not all_tickers or len(all_tickers) == 0:
            local_files = [f for f in os.listdir('.') if f.endswith('.csv') and f not in [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]]
            tickers = []
            for file in local_files:
                try:
                    tdf = pd.read_csv(file, header=None)
                    tickers += tdf.iloc[:,0].dropna().astype(str).str.strip().tolist()
                except Exception:
                    continue
            tickers = [normalize_ticker(t) for t in tickers if isinstance(t, str) and t.strip()!='']
            tickers = dedupe_preserve_order(tickers)
            all_tickers = tickers

        if not all_tickers:
            st.warning("לא נמצאו טיקרים לניתוח. העלה קובץ CSV או הנח קבצי CSV בתיקייה.")
        else:
            st.info(f"מריץ ניתוח על עד {sample_size} טיקרים (דגימה מתוך {len(all_tickers)}) — זה עלול לקחת זמן.")
            np.random.seed(42)
            sample = list(np.random.choice(all_tickers, size=min(sample_size, len(all_tickers)), replace=False))
            stats_df = compute_indicator_sample_stats(sample, max_samples=sample_size)
            if stats_df.empty:
                st.error("לא התקבלו מדדים מהדגימה — בדוק שהטיקרים תקינים ו‑yfinance מחזיר היסטוריה.")
            else:
                st.success(f"נבדקו {len(stats_df)} טיקרים בדגימה.")
                st.write("סטטיסטיקה תמציתית לדגימה:")
                st.dataframe(stats_df.describe().T[['count','mean','50%','std']].rename(columns={'50%':'median'}), use_container_width=True)

                percentiles = {
                    "BB_width": percentile_bb,
                    "RVOL": percentile_rvol,
                    "AvgVol20": percentile_avgvol,
                    "RSI": percentile_rsi,
                    "ATR": percentile_atr
                }
                suggestions = suggest_thresholds_from_stats(stats_df, percentiles=percentiles)
                st.markdown("**המלצות ספים (מוצע)**")
                sug_df = pd.DataFrame([suggestions])
                if sug_df['AvgVol20'].notna().any():
                    sug_df['AvgVol20'] = sug_df['AvgVol20'].apply(lambda x: int(x) if pd.notna(x) else x)
                if sug_df['RSI'].notna().any():
                    sug_df['RSI'] = sug_df['RSI'].apply(lambda x: round(x,1) if pd.notna(x) else x)
                st.table(sug_df.T.rename(columns={0:'Suggested'}))

                st.markdown("**התפלגויות (דגימה)**")
                cols = st.columns(3)
                with cols[0]:
                    fig_bbw = px.histogram(stats_df, x='BB_width', nbins=40, title='BB width (sample)')
                    st.plotly_chart(fig_bbw, use_container_width=True)
                with cols[1]:
                    fig_rvol = px.histogram(stats_df, x='RVOL', nbins=40, title='RVOL (sample)')
                    st.plotly_chart(fig_rvol, use_container_width=True)
                with cols[2]:
                    fig_avgv = px.histogram(stats_df.dropna(subset=['AvgVol20']), x='AvgVol20', nbins=40, title='AvgVol20 (sample)')
                    st.plotly_chart(fig_avgv, use_container_width=True)

                cols2 = st.columns(2)
                with cols2[0]:
                    fig_rsi = px.histogram(stats_df, x='RSI', nbins=40, title='RSI (sample)')
                    st.plotly_chart(fig_rsi, use_container_width=True)
                with cols2[1]:
                    fig_atr = px.histogram(stats_df, x='ATR', nbins=40, title='ATR (sample)')
                    st.plotly_chart(fig_atr, use_container_width=True)

                if st.button("החל את ההמלצות כערכי ברירת מחדל"):
                    if suggestions.get('BB_width') is not None:
                        st.session_state['bb_width_thresh'] = float(suggestions['BB_width'])
                    if suggestions.get('RVOL') is not None:
                        st.session_state['rvol_threshold'] = float(suggestions['RVOL'])
                    if suggestions.get('AvgVol20') is not None:
                        st.session_state['min_avg_vol'] = int(suggestions['AvgVol20'])
                    if suggestions.get('RSI') is not None:
                        st.session_state['rsi_threshold'] = float(suggestions['RSI'])
                    _write_log("auto_tune_apply", [f"{k}:{v}" for k,v in suggestions.items()], note=f"applied from sample {len(stats_df)}")
                    st.success("ההמלצות נשמרו ב‑session והחליפו את ברירות המחדל. הדף ירענן כדי להציג את הערכים החדשים.")
                    st.experimental_rerun()

# -------------------------
# ניהול קבצים: גיבוי/שחזור/מחיקה
# -------------------------
st.markdown("---")
st.markdown("### ניהול קבצי סריקה")
with st.expander("גיבוי, שחזור ומחיקה של קבצי סריקה"):
    st.write("גיבוי נוצר אוטומטית לפני מחיקה. ניתן לשחזר גיבוי אחרון או לבחור גיבוי ספציפי.")
    files_available = [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]
    file_checks = {}
    cols = st.columns(len(files_available))
    for i, f in enumerate(files_available):
        with cols[i]:
            file_checks[f] = st.checkbox(os.path.basename(f), value=(os.path.exists(f)))

    if st.button("גבה עכשיו"):
        to_backup = [f for f, checked in file_checks.items() if checked and os.path.exists(f)]
        if not to_backup:
            st.warning("אין קבצים זמינים לגיבוי.")
        else:
            backed = create_backup(to_backup)
            if backed:
                st.success(f"גובו {len(backed)} קבצים לתיקיית {BACKUP_DIR}.")
                for b in backed:
                    st.write(f"- {b}")
            else:
                st.info("לא נוצרו גיבויים (ייתכן שהקבצים לא קיימים).")

    st.markdown("---")
    backups = list_backups()
    if backups:
        st.write(f"נמצאו {len(backups)} גיבויים אחרונים:")
        sel = st.selectbox("בחר גיבוי לשחזור", backups, format_func=lambda x: os.path.basename(x))
        restore_checks = {}
        rcols = st.columns(len(files_available))
        for i, f in enumerate(files_available):
            with rcols[i]:
                restore_checks[f] = st.checkbox(f"שחזר {os.path.basename(f)}", value=False)
        if st.button("שחזר גיבוי שנבחר"):
            to_restore = [f for f, checked in restore_checks.items() if checked]
            if not to_restore:
                st.warning("בחר לפחות קובץ אחד לשחזור.")
            else:
                ok, info = restore_backup(sel, to_restore)
                if ok:
                    st.success(f"שוחזרו {len(info)} קבצים.")
                    for r in info:
                        st.write(f"- {r}")
                else:
                    st.error(f"שגיאה בשחזור: {info}")
    else:
        st.info("אין גיבויים זמינים כרגע.")

    st.markdown("---")
    delete_confirm = st.checkbox("אני מאשר/ת למחוק את הקבצים שנבחרו (גיבוי ייווצר אוטומטית)")
    include_portfolio = st.checkbox("כלול גם portfolio.csv במחיקה (ברירת מחדל: לא)", value=False)
    if st.button("מחק קבצי סריקה שנבחרו"):
        if not delete_confirm:
            st.warning("יש לסמן את תיבת האישור לפני המחיקה.")
        else:
            to_remove = [SCAN_RESULTS_FILE, REJECTIONS_FILE]
            if include_portfolio:
                to_remove.append(PORTFOLIO_FILE)
            existing = [f for f in to_remove if os.path.exists(f)]
            if existing:
                backed = create_backup(existing)
                st.write(f"גובו לפני מחיקה: {len(backed)} קבצים.")
            else:
                st.write("לא נמצאו קבצים קיימים לגיבוי לפני מחיקה.")
            removed = []
            errors = []
            for f in to_remove:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                        removed.append(f)
                    except Exception as e:
                        errors.append(f"{f}: {e}")
                else:
                    errors.append(f"{f}: לא נמצא")
            _write_log("delete", removed + errors)
            if removed:
                st.success("הקבצים הוסרו:")
                for r in removed:
                    st.write(f"- {r}")
            if errors:
                st.error("חלק מהקבצים לא נמחו או לא נמצאו:")
                for err in errors:
                    st.write(f"- {err}")

    st.markdown("---")
    if os.path.exists(LOG_FILE):
        try:
            log_df = pd.read_csv(LOG_FILE).sort_values(by='timestamp', ascending=False).head(50)
            st.write("לוג גיבויים (50 רשומות אחרונות):")
            st.dataframe(log_df, use_container_width=True)
            if st.button("הורד לוג גיבויים"):
                st.download_button("הורד לוג", data=log_df.to_csv(index=False), file_name=os.path.basename(LOG_FILE), mime='text/csv')
        except Exception:
            st.write("לא ניתן לקרוא את קובץ הלוג.")
    else:
        st.write("אין לוג גיבויים להצגה.")

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

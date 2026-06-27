# app.py - KEISAR Pro Hunter (PreBreakout highlight + AgGrid actions + Icons + Undo)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import shutil
import glob
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px

# נסיון לטעון AgGrid
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False

# -------------------------
# קונפיג בסיסי ו‑CSS
# -------------------------
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
st.markdown(
    """
    <style>
    .app-title {font-size:20px; font-weight:700; margin-bottom:0px;}
    .app-sub {font-size:12px; color: #6c757d; margin-top:2px; margin-bottom:12px;}
    .stButton>button {padding:6px 10px;}
    .dataframe td, .dataframe th {padding:6px 8px;}
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
# פונקציות עזר
# -------------------------
def is_bollinger_squeeze(df, lookback=20, width_thresh=0.05):
    recent = df['BB_width'].iloc[-lookback:]
    current = recent.iloc[-1]
    median_width = recent.median()
    ok = current <= width_thresh or current <= 0.6 * median_width
    return ok, float(current)

def obv_confirmation(df, lookback=10):
    try:
        obv_now = df['OBV'].iloc[-1]
        obv_past = df['OBV'].iloc[-1 - lookback]
        return obv_now > obv_past, float(obv_now - obv_past)
    except Exception:
        return False, 0.0

def macd_confirmation(df, lookback=3):
    try:
        hist_now = df['MACD_hist'].iloc[-1]
        hist_past = df['MACD_hist'].iloc[-1 - lookback]
        ok = hist_now > hist_past and df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]
        return ok, float(hist_now)
    except Exception:
        return False, 0.0

def atr_expansion(df, lookback=10):
    try:
        atr_now = df['ATR'].iloc[-1]
        atr_past = df['ATR'].iloc[-1 - lookback]
        return atr_now > atr_past, float(atr_now / (atr_past + 1e-9))
    except Exception:
        return False, 0.0

def vwap_confirmation(df):
    try:
        ok = df['Close'].iloc[-1] > df['VWAP'].iloc[-1]
        return ok, float(df['Close'].iloc[-1] - df['VWAP'].iloc[-1])
    except Exception:
        return False, 0.0

def rsi_smart_check(df, rvol_now, rvol_threshold):
    try:
        rsi_val = float(df['RSI'].iloc[-1])
        if rsi_val < 50:
            return False, f"RSI נמוך ({rsi_val:.1f})"
        if rsi_val <= 70:
            return True, f"RSI בטווח טוב ({rsi_val:.1f})"
        atr_ok, atr_ratio = atr_expansion(df, lookback=10)
        if rvol_now >= max(1.5, rvol_threshold) and atr_ok:
            return True, f"RSI גבוה ({rsi_val:.1f}) אך מאושר"
        return False, f"RSI גבוה ({rsi_val:.1f}) ללא אישור"
    except Exception as e:
        return False, f"שגיאת RSI: {e}"

def find_squeeze_date(df, lookback=60):
    try:
        recent = df['BB_width'].iloc[-lookback:]
        idx = recent.idxmin()
        return idx if not pd.isna(idx) else None
    except Exception:
        return None

def fetch_intraday_volume_series(ticker, period="5d", interval="60m"):
    try:
        df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def intraday_rvol_spike(ticker, rvol_thresh=1.3):
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
# UI - כותרת ותפריט צדדי
# -------------------------
st.markdown('<div class="app-title">KEISAR Pro Hunter — Breakout Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">סריקה טכנית לזיהוי פריצות ו‑PreBreakouts. Sidebar להגדרות.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("הגדרות")
    pct_from_low = st.number_input("אחוז מקירוב לשפל 52 שבועות (%)", value=3.0, min_value=0.0, max_value=50.0) / 100.0
    bb_width_thresh = st.number_input("BB width לפריצה", value=0.05, min_value=0.001, max_value=1.0, step=0.005)
    rvol_threshold = st.number_input("RVOL סף", value=1.2, min_value=0.5, max_value=10.0)
    min_marketcap = st.number_input("מינימום שווי שוק (USD)", value=300_000_000, step=50_000_000)
    min_avg_vol = st.number_input("ממוצע נפח מינימלי (20 יום)", value=150_000, step=10_000)
    chunk_size = st.number_input("גודל קבוצה (chunk)", min_value=5, max_value=200, value=25)
    prebreak_squeeze_lookback = st.number_input("ימים לחיפוש squeeze", min_value=5, max_value=120, value=14)
    intraday_rvol_thresh = st.number_input("RVOL אינטרדיילי לזיהוי spike", min_value=1.0, max_value=5.0, value=1.3)
    DEBUG_MODE = st.checkbox("Debug - אל תדחה אוטומטית", value=False)
    enable_intraday = st.checkbox("הפעל בדיקות אינטרדייליות (איטי)", value=False)
    st.markdown("---")
    uploaded_sidebar = st.file_uploader("העלה קבצי CSV (טיקר בכל שורה)", accept_multiple_files=True, type="csv")
    st.markdown("---")
    run_scan_btn = st.button("הפעל סריקה (Sidebar)")

# -------------------------
# בחירת קובץ יחיד ותצוגה מקדימה
# -------------------------
col_left, col_right = st.columns([1, 3])
with col_left:
    st.markdown("**קובץ CSV אופציונלי**")
    local_csvs = sorted([f for f in os.listdir('.') if f.endswith('.csv') and f not in [SCAN_RESULTS_FILE, REJECTIONS_FILE, PORTFOLIO_FILE]])
    selected_local = st.selectbox("קבצים בתיקייה", ["-- בחר --"] + local_csvs) if local_csvs else None
    if selected_local == "-- בחר --":
        selected_local = None
    uploaded_single = st.file_uploader("או העלה קובץ CSV יחיד", accept_multiple_files=False, type="csv", key="single_uploader")
    preview = st.empty()

    def read_tickers_from_fileobj(fileobj):
        try:
            if isinstance(fileobj, str):
                df = pd.read_csv(fileobj, header=None, dtype=str)
            else:
                fileobj.seek(0)
                df = pd.read_csv(fileobj, header=None, dtype=str)
            raw = df.iloc[:, 0].dropna().astype(str).tolist()
            normalized = [normalize_ticker(t) for t in raw]
            return dedupe_preserve_order([t for t in normalized if t])
        except Exception:
            return []

    if uploaded_single:
        pts = read_tickers_from_fileobj(uploaded_single)
        preview.write(f"קובץ שהועלה: {uploaded_single.name} — {len(pts)} טיקרים")
        preview.dataframe(pd.DataFrame(pts, columns=["Ticker"]).head(50), use_container_width=True)
    elif selected_local:
        pts = read_tickers_from_fileobj(selected_local)
        preview.write(f"קובץ מקומי: {selected_local} — {len(pts)} טיקרים")
        preview.dataframe(pd.DataFrame(pts, columns=["Ticker"]).head(50), use_container_width=True)

with col_right:
    st.markdown("**סיכום מהיר**")
    m1, m2, m3 = st.columns(3)
    m1.metric("טיקרים לניתוח", "—")
    m2.metric("תוצאות (עברו סינון)", "—")
    m3.metric("PreBreakouts", "—")

# -------------------------
# טעינת טיקרים
# -------------------------
tickers = []
if uploaded_sidebar:
    for f in uploaded_sidebar:
        try:
            tdf = pd.read_csv(f, header=None, dtype=str)
            raw = tdf.iloc[:,0].dropna().astype(str).tolist()
            tickers.extend([normalize_ticker(x) for x in raw])
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
            raw = tdf.iloc[:,0].dropna().astype(str).tolist()
            tickers.extend([normalize_ticker(x) for x in raw])
        except Exception:
            continue

tickers = dedupe_preserve_order([t for t in tickers if t])
st.session_state['tickers'] = tickers
m1.metric("טיקרים לניתוח", f"{len(tickers)}")

# -------------------------
# פונקציית סריקה
# -------------------------
def run_scan_on_list(tickers_list, chunk_size=25, enable_intraday_flag=False):
    total = len(tickers_list)
    progress = st.progress(0)
    results = []
    rejections = []
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
                ok_mc = bool(info.get('marketCap') and info.get('marketCap') >= min_marketcap)
                if not ok_mc: reasons.append("שווי שוק קטן")
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1] if len(df)>=20 else 0
                if avg_vol < min_avg_vol: reasons.append("ממוצע נפח נמוך")

                squeeze_ok, squeeze_val = is_bollinger_squeeze(df, lookback=20, width_thresh=bb_width_thresh)
                if not squeeze_ok: reasons.append(f"לא דחיסה (BBw {squeeze_val:.3f})")

                obv_ok, _ = obv_confirmation(df, lookback=10)
                if not obv_ok: reasons.append("OBV לא מאשר")

                rvol_now = float(df['RVOL'].iloc[-1])
                if rvol_now < rvol_threshold: reasons.append(f"RVOL נמוך ({rvol_now:.2f})")

                macd_ok, _ = macd_confirmation(df, lookback=3)
                if not macd_ok: reasons.append("MACD לא מאשר")

                rsi_ok, rsi_msg = rsi_smart_check(df, rvol_now, rvol_threshold)
                if not rsi_ok: reasons.append(rsi_msg)

                vwap_ok, _ = vwap_confirmation(df)
                if not vwap_ok: reasons.append("מחיר מתחת ל‑VWAP")

                atr_ok, _ = atr_expansion(df, lookback=10)
                if not atr_ok: reasons.append("ATR לא מראה הרחבה")

                squeeze_date = find_squeeze_date(df, lookback=60)
                days_since_squeeze = None
                if squeeze_date is not None:
                    days_since_squeeze = (df.index[-1].date() - squeeze_date.date()).days
                if enable_intraday_flag:
                    intraday_spike, intraday_rvol = intraday_rvol_spike(t, rvol_thresh=intraday_rvol_thresh)
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
                    "BB_width": float(df['BB_width'].iloc[-1]),
                    "RVOL": float(df['RVOL'].iloc[-1]),
                    "OBV_change_10d": obv_change,
                    "MACD_hist": float(df['MACD_hist'].iloc[-1]),
                    "RSI": float(df['RSI'].iloc[-1]),
                    "ATR": float(df['ATR'].iloc[-1]),
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": float(df['Volume'].rolling(20).mean().iloc[-1]) if len(df)>=20 else None,
                    "PreBreakout": prebreak_flag,
                    "IntradayRVOL": float(intraday_rvol) if intraday_rvol is not None else None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })
            else:
                results.append({
                    "Ticker": t,
                    "Price": None,
                    "BB_width": None,
                    "RVOL": None,
                    "OBV_change_10d": None,
                    "MACD_hist": None,
                    "RSI": None,
                    "ATR": None,
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": None,
                    "PreBreakout": prebreak_flag,
                    "IntradayRVOL": None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })
            time.sleep(0.02)
        progress.progress(min(1.0, (i + chunk_size) / total))
    progress.empty()
    return results, rejections

# -------------------------
# הפעלת סריקה
# -------------------------
run_scan_main = st.button("הפעל סריקה (מרכז)")
do_scan = run_scan_btn or run_scan_main

# וודא שיש מקום לזכור הוספות אחרונות ל‑Undo
if 'last_added' not in st.session_state:
    st.session_state['last_added'] = []

df_res = pd.DataFrame()
df_rej = pd.DataFrame()
if do_scan:
    if not st.session_state.get('tickers'):
        st.warning("אין טיקרים להרצה.")
    else:
        st.info(f"מריץ סריקה על {len(st.session_state['tickers'])} טיקרים...")
        results, rejections = run_scan_on_list(st.session_state['tickers'], chunk_size=int(chunk_size), enable_intraday_flag=enable_intraday)
        # הסרת כפילויות ונרמול
        seen = set()
        unique_results = []
        for r in results:
            t = normalize_ticker(r.get('Ticker',''))
            if not t or t in seen:
                continue
            seen.add(t)
            r['Ticker'] = t
            # הוספת עמודת Signal עם אייקון
            r['Signal'] = "🚀" if r.get('PreBreakout') else ""
            unique_results.append(r)
        df_res = pd.DataFrame(unique_results).sort_values(by=['PreBreakout','OBV_change_10d','RVOL'], ascending=[False,False,False], na_position='last')
        df_res.to_csv(SCAN_RESULTS_FILE, index=False)
        with col_right:
            m2.metric("תוצאות (עברו סינון)", f"{len(df_res)}")
            pre_count = int(df_res['PreBreakout'].sum()) if 'PreBreakout' in df_res.columns else 0
            m3.metric("PreBreakouts", f"{pre_count}")

        # טאב: All / PreBreakouts / AgGrid
        tab_all, tab_pre, tab_ag = st.tabs(["All results", "PreBreakouts", "AgGrid (Interactive)"])
        with tab_all:
            st.dataframe(df_res, use_container_width=True)

        with tab_pre:
            if 'PreBreakout' in df_res.columns:
                df_pre = df_res[df_res['PreBreakout'] == True].reset_index(drop=True)
                st.write(f"נמצאו {len(df_pre)} PreBreakouts")
                st.dataframe(df_pre, use_container_width=True)

                # כפתורי פעולה מהירים עבור PreBreakouts
                cols = st.columns([1,1,1,1])
                with cols[0]:
                    if st.button("הוסף כל ה‑PreBreakouts לתיק"):
                        if os.path.exists(PORTFOLIO_FILE):
                            p_df = pd.read_csv(PORTFOLIO_FILE, dtype=str)
                        else:
                            p_df = pd.DataFrame(columns=["Ticker","AddedAt","Price"])
                        existing = set(p_df['Ticker'].astype(str).str.upper().tolist()) if 'Ticker' in p_df.columns else set()
                        added = []
                        for _, row in df_pre.iterrows():
                            t = normalize_ticker(row['Ticker'])
                            if t and t not in existing:
                                p_row = {"Ticker": t, "AddedAt": datetime.utcnow().isoformat(), "Price": row['Price']}
                                p_df = pd.concat([p_df, pd.DataFrame([p_row])], ignore_index=True)
                                existing.add(t)
                                added.append(t)
                        p_df.to_csv(PORTFOLIO_FILE, index=False)
                        # שמירת הוספות ל‑Undo
                        st.session_state['last_added'] = added
                        st.success(f"הוספו {len(added)} טיקרים לתיק.")
                with cols[1]:
                    if st.button("ייצא PreBreakouts ל‑CSV"):
                        st.download_button("⬇️ הורד CSV", data=df_pre.to_csv(index=False), file_name="prebreakouts.csv", mime='text/csv')
                with cols[2]:
                    if st.button("סמן כ'בדוק ידנית' (ייצוא CSV)"):
                        fname = f"prebreakouts_check_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
                        df_pre.to_csv(fname, index=False)
                        st.success(f"נוצר קובץ: {fname}")
                with cols[3]:
                    if st.button("Undo הוספות אחרונות לתיק"):
                        last = st.session_state.get('last_added', [])
                        if not last:
                            st.info("אין הוספות אחרונות לבטל.")
                        else:
                            if os.path.exists(PORTFOLIO_FILE):
                                p_df = pd.read_csv(PORTFOLIO_FILE, dtype=str)
                                before = len(p_df)
                                p_df = p_df[~p_df['Ticker'].astype(str).str.upper().isin([t.upper() for t in last])]
                                p_df.to_csv(PORTFOLIO_FILE, index=False)
                                removed = before - len(p_df)
                                st.session_state['last_added'] = []
                                st.success(f"בוטלו {removed} הוספות לתיק.")
                            else:
                                st.info("קובץ תיק לא קיים.")
            else:
                st.info("אין שדה PreBreakout בתוצאות.")

        with tab_ag:
            if not AGGRID_AVAILABLE:
                st.warning("AgGrid לא מותקן. התקן: pip install streamlit-aggrid")
            else:
                if df_res.empty:
                    st.info("אין תוצאות להצגה ב‑AgGrid.")
                else:
                    # בניית GridOptions עם הדגשת PreBreakout ועמודת Signal עם אייקון
                    gb = GridOptionsBuilder.from_dataframe(df_res)
                    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
                    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
                    # conditional style JS: הדגשת שורות PreBreakout בירוק בהיר
                    js_row_style = JsCode("""
                    function(params) {
                        if (params.data && params.data.PreBreakout === true) {
                            return {'backgroundColor': '#e6ffed'};
                        }
                        return null;
                    };
                    """)
                    # cell renderer JS for Signal column to show big emoji
                    js_signal = JsCode("""
                    class SignalRenderer {
                      init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.fontSize = '18px';
                        this.eGui.style.textAlign = 'center';
                        this.eGui.innerHTML = params.value ? params.value : '';
                      }
                      getGui() {
                        return this.eGui;
                      }
                    }
                    """)
                    gb.configure_column("Signal", header_name="Signal", cellRenderer=js_signal)
                    gb.configure_grid_options(getRowStyle=js_row_style)
                    grid_options = gb.build()
                    grid_response = AgGrid(
                        df_res,
                        gridOptions=grid_options,
                        enable_enterprise_modules=False,
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                        fit_columns_on_grid_load=True,
                        height=420
                    )
                    selected = grid_response.get('selected_rows', [])
                    st.write(f"נבחרו {len(selected)} שורות")
                    # כפתורי פעולה על שורות נבחרות
                    a1, a2, a3 = st.columns([1,1,1])
                    with a1:
                        if st.button("הוסף נבחרים לתיק (AgGrid)"):
                            if not selected:
                                st.info("בחר שורות קודם.")
                            else:
                                if os.path.exists(PORTFOLIO_FILE):
                                    p_df = pd.read_csv(PORTFOLIO_FILE, dtype=str)
                                else:
                                    p_df = pd.DataFrame(columns=["Ticker","AddedAt","Price"])
                                existing = set(p_df['Ticker'].astype(str).str.upper().tolist()) if 'Ticker' in p_df.columns else set()
                                added = []
                                for row in selected:
                                    t = normalize_ticker(row.get('Ticker',''))
                                    price = row.get('Price', None)
                                    if t and t not in existing:
                                        p_row = {"Ticker": t, "AddedAt": datetime.utcnow().isoformat(), "Price": price}
                                        p_df = pd.concat([p_df, pd.DataFrame([p_row])], ignore_index=True)
                                        existing.add(t)
                                        added.append(t)
                                p_df.to_csv(PORTFOLIO_FILE, index=False)
                                # שמירת הוספות ל‑Undo
                                st.session_state['last_added'] = added
                                st.success(f"הוספו {len(added)} טיקרים לתיק.")
                    with a2:
                        if st.button("ייצא נבחרים ל‑CSV (AgGrid)"):
                            if not selected:
                                st.info("בחר שורות קודם.")
                            else:
                                sel_df = pd.DataFrame(selected).drop(columns=['_selectedRowNodeInfo'], errors='ignore')
                                st.download_button("⬇️ הורד CSV נבחרים", data=sel_df.to_csv(index=False), file_name="selected_prebreakouts.csv", mime='text/csv')
                    with a3:
                        if st.button("Undo הוספות נבחרות"):
                            last = st.session_state.get('last_added', [])
                            if not last:
                                st.info("אין הוספות אחרונות לבטל.")
                            else:
                                if os.path.exists(PORTFOLIO_FILE):
                                    p_df = pd.read_csv(PORTFOLIO_FILE, dtype=str)
                                    before = len(p_df)
                                    p_df = p_df[~p_df['Ticker'].astype(str).str.upper().isin([t.upper() for t in last])]
                                    p_df.to_csv(PORTFOLIO_FILE, index=False)
                                    removed = before - len(p_df)
                                    st.session_state['last_added'] = []
                                    st.success(f"בוטלו {removed} הוספות לתיק.")
                                else:
                                    st.info("קובץ תיק לא קיים.")

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
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5,0.15,0.15,0.2])
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
st.write("הערה: כלי מחקר טכני בלבד — לא ייעוץ השקעות.")

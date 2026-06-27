import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="KEISAR Pro Hunter - 52w Low Scanner (Fixed)", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
REJECTIONS_FILE = 'scan_rejections.csv'
PORTFOLIO_FILE = 'portfolio.csv'

# -------------------------
# מטמון לקריאות yfinance
# -------------------------
@st.cache_data(ttl=60*30)
def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period)
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
# אינדיקטורים ועזרים
# -------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['MA20'] + 2 * df['STD']
    df['BB_lower'] = df['MA20'] - 2 * df['STD']
    df['Squeeze'] = (df['BB_upper'] - df['BB_lower']) / df['MA20']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    # RSI 14 (EMA)
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=13, adjust=False).mean()
    ma_down = down.ewm(com=13, adjust=False).mean()
    rs = ma_up / ma_down
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=10).mean()
    return df.dropna()

def is_52w_low(df: pd.DataFrame, pct_from_low=0.01) -> (bool, str):
    try:
        low_52 = df['Close'].min()
        current = df['Close'].iloc[-1]
        ok = (current - low_52) / low_52 <= pct_from_low
        reason = "" if ok else f"לא קרוב לשפל 52w (הפרש {(current-low_52)/low_52:.2%})"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת חישוב 52w: {e}"

def is_sideways_week(df: pd.DataFrame, days=5, max_range_pct=0.02) -> (bool, str):
    try:
        if len(df) < days:
            return False, f"היסטוריה קצרה ל־{days} ימים"
        recent = df['Close'].iloc[-days:]
        price_range = recent.max() - recent.min()
        ref = recent.mean()
        ok = (price_range / ref) <= max_range_pct
        reason = "" if ok else f"לא תנועה צידית ב{days} ימים (טווח {(price_range/ref):.2%})"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת חישוב תנועה צידית: {e}"

def institutional_accumulation(df: pd.DataFrame, obv_days=10, rvol_thresh=1.5) -> (bool, str):
    try:
        if len(df) < obv_days + 2:
            return False, "טווח היסטוריה קצר ל‑OBV"
        obv_now = df['OBV'].iloc[-1]
        obv_past = df['OBV'].iloc[-(obv_days+1)]
        rvol_now = df['RVOL'].iloc[-1]
        vol_now = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(window=20).mean().iloc[-1]
        ok = (obv_now > obv_past) and (rvol_now >= rvol_thresh) and (vol_now >= vol_avg)
        reasons = []
        if not (obv_now > obv_past): reasons.append("OBV לא עולה")
        if not (rvol_now >= rvol_thresh): reasons.append(f"RVOL נמוך ({rvol_now:.2f})")
        if not (vol_now >= vol_avg): reasons.append("נפח יומי נמוך מהממוצע 20")
        return ok, "; ".join(reasons)
    except Exception as e:
        return False, f"שגיאת חישוב OBV/RVOL/נפח: {e}"

def macd_rising(df: pd.DataFrame, lookback=3) -> (bool, str):
    try:
        if len(df) < lookback + 2:
            return False, "טווח היסטוריה קצר ל‑MACD"
        ok = df['MACD'].iloc[-1] > df['MACD'].iloc[-1 - lookback]
        reason = "" if ok else "MACD לא בעל מגמה עולה"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת חישוב MACD: {e}"

def rsi_not_overbought(df: pd.DataFrame, threshold=70) -> (bool, str):
    try:
        ok = df['RSI'].iloc[-1] < threshold
        reason = "" if ok else f"RSI גבוה ({df['RSI'].iloc[-1]:.1f})"
        return ok, reason
    except Exception as e:
        return False, f"שגיאת חישוב RSI: {e}"

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
# UI - הגדרות
# -------------------------
st.title("KEISAR Pro Hunter - 52 Week Low + Accumulation Scanner")

left, right = st.columns([1, 3])
with left:
    st.subheader("הגדרות סריקה")
    pct_from_low = st.number_input("אחוז מקירוב לשפל 52 שבועות (%)", value=3.0, min_value=0.0, max_value=50.0) / 100.0
    sideways_range_pct = st.number_input("מקסימום טווח תנועה בשבוע (%)", value=4.0, min_value=0.1, max_value=50.0) / 100.0
    rvol_threshold = st.number_input("סף RVOL לאיסוף", value=1.2, min_value=0.5, max_value=10.0)
    rsi_threshold = st.number_input("סף RSI מקסימלי", value=70, min_value=30, max_value=90)
    min_marketcap = st.number_input("מינימום שווי שוק (USD)", value=300_000_000, step=50_000_000)
    min_avg_vol = st.number_input("ממוצע נפח מינימלי (20 יום)", value=150_000, step=10_000)
    chunk_size = st.number_input("גודל קבוצה לסריקה (chunk size)", min_value=5, max_value=200, value=25, step=5)
    DEBUG_MODE = st.checkbox("מצב Debug - אל תדחה אוטומטית, הצג Warnings", value=False)
    run_scan = st.button("הפעל סריקה")

with right:
    st.subheader("תוצאות וסריקה")
    results_placeholder = st.empty()

# -------------------------
# טעינת טיקרים מ‑CSV (uploader או תיקייה)
# -------------------------
uploaded = st.file_uploader("העלה קבצי CSV (טיקר בכל שורה) או השאר ריק לקריאה מקבצים בתיקייה", accept_multiple_files=True, type="csv")
tickers = []

# קריאה מקבצים שהועלו
if uploaded:
    for f in uploaded:
        try:
            tdf = pd.read_csv(f, header=None)
            tickers += tdf.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        except Exception:
            continue
else:
    # קריאה מקבצים מקומיים בתיקייה (שלא שמורים כ־scan/rejections/portfolio)
    local_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'scan' not in f and 'rejection' not in f and 'portfolio' not in f]
    for file in local_files:
        try:
            tdf = pd.read_csv(file, header=None)
            tickers += tdf.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        except Exception:
            continue

# ניקוי, המרה והסרת כפילויות
tickers = [t.replace('.', '-').upper() for t in tickers if isinstance(t, str) and t.strip() != ""]
tickers = list(dict.fromkeys(tickers))  # שומר סדר ומסיר כפילויות
st.write(f"נמצאו {len(tickers)} טיקרים")
st.session_state['tickers'] = tickers

# -------------------------
# פונקציית סריקה ב‑chunks
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
            info = fetch_info(t)
            hist = fetch_history(t, period="1y")
            if hist.empty or len(hist) < 60:
                reasons.append("היסטוריה חסרה/קצרה")
                if not DEBUG_MODE:
                    rejections.append({"Ticker": t, "Reasons": "; ".join(reasons)})
                    continue
            if not hist.empty:
                df = add_indicators(hist)
            else:
                df = None

            # בדיקות קריטריונים
            if df is not None:
                ok_mc, r = marketcap_ok(info, min_marketcap)
                if not ok_mc: reasons.append(r)
                ok_volavg, r = avg_volume_ok(df, min_avg_vol)
                if not ok_volavg: reasons.append(r)
                ok_52, r = is_52w_low(df, pct_from_low=pct_from_low)
                if not ok_52: reasons.append(r)
                ok_side, r = is_sideways_week(df, days=5, max_range_pct=sideways_range_pct)
                if not ok_side: reasons.append(r)
                ok_inst, r = institutional_accumulation(df, obv_days=10, rvol_thresh=rvol_threshold)
                if not ok_inst: reasons.append(r)
                ok_macd, r = macd_rising(df, lookback=3)
                if not ok_macd: reasons.append(r)
                ok_rsi, r = rsi_not_overbought(df, threshold=rsi_threshold)
                if not ok_rsi: reasons.append(r)
            else:
                # אם אין df, כבר הוספנו סיבת דחייה למעלה
                pass

            if reasons and not DEBUG_MODE:
                rejections.append({"Ticker": t, "Reasons": "; ".join(reasons)})
                continue

            # אם DEBUG_MODE: אפשר להוסיף גם תוצאות עם Warnings
            if df is not None:
                obv_change = float(df['OBV'].iloc[-1] - df['OBV'].iloc[-11]) if len(df) > 11 else 0.0
                results.append({
                    "Ticker": t,
                    "Price": float(df['Close'].iloc[-1]),
                    "52w_low": float(df['Close'].min()),
                    "RVOL": float(df['RVOL'].iloc[-1]),
                    "OBV_change_10d": obv_change,
                    "MACD": float(df['MACD'].iloc[-1]),
                    "RSI": float(df['RSI'].iloc[-1]),
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": float(df['Volume'].rolling(20).mean().iloc[-1]),
                    "Warnings": "; ".join(reasons) if reasons else ""
                })
            else:
                # במקרה של df None וה‑DEBUG_MODE, הוסף שורה עם מידע מינימלי
                results.append({
                    "Ticker": t,
                    "Price": None,
                    "52w_low": None,
                    "RVOL": None,
                    "OBV_change_10d": None,
                    "MACD": None,
                    "RSI": None,
                    "MarketCap": info.get('marketCap', None),
                    "AvgVol20": None,
                    "Warnings": "; ".join(reasons) if reasons else ""
                })

            # הימנעות מקצב גבוה מדי
            time.sleep(0.05)
        # עדכון פרוגרס אחרי כל batch
        progress.progress(min(1.0, (i + chunk_size) / total))
    progress.empty()
    return results, rejections

# -------------------------
# הפעלת סריקה
# -------------------------
if run_scan:
    if not st.session_state.get('tickers'):
        st.warning("אין טיקרים להרצה. העלה קובץ CSV או הנח קבצי CSV בתיקייה.")
    else:
        with st.spinner("מריץ סריקה ב‑chunks..."):
            results, rejections = run_scan_on_list(st.session_state['tickers'], chunk_size=int(chunk_size))
        # שמירה והצגה
        if results:
            df_res = pd.DataFrame(results).sort_values(by=['OBV_change_10d','RVOL'], ascending=False, na_position='last')
            df_res.to_csv(SCAN_RESULTS_FILE, index=False)
            results_placeholder.success(f"סריקה הושלמה: {len(df_res)} תוצאות (כולל DEBUG).")
            st.subheader("תוצאות שעברו סינון")
            st.dataframe(df_res, use_container_width=True)
            st.download_button("⬇️ הורד תוצאות CSV", data=df_res.to_csv(index=False), file_name=SCAN_RESULTS_FILE, mime='text/csv')
        else:
            df_res = pd.DataFrame(columns=["Ticker","Price","52w_low","RVOL","OBV_change_10d","MACD","RSI","MarketCap","AvgVol20","Warnings"])
            results_placeholder.info("לא נמצאו תוצאות שעברו את כל הקריטריונים.")

        if rejections:
            df_rej = pd.DataFrame(rejections)
            # הוספת סיבת דחייה עיקרית
            df_rej['PrimaryReason'] = df_rej['Reasons'].apply(lambda x: x.split(';')[0] if isinstance(x, str) and x else '')
            df_rej.to_csv(REJECTIONS_FILE, index=False)
            st.subheader("טיקרים שנדחו וסיבות")
            st.dataframe(df_rej, use_container_width=True)
            st.download_button("⬇️ הורד דחיות CSV", data=df_rej.to_csv(index=False), file_name=REJECTIONS_FILE, mime='text/csv')
        else:
            st.write("אין דחיות להציג.")

# -------------------------
# הצגת תוצאות קודמות וגרפים
# -------------------------
if os.path.exists(SCAN_RESULTS_FILE) and not run_scan:
    st.subheader("תוצאות סריקה קודמות")
    try:
        df_prev = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_prev, use_container_width=True)
        sel = st.selectbox("בחר מניה להצגה מתוך תוצאות קודמות", df_prev['Ticker'].tolist())
        if st.button("הצג גרף מהתוצאות הקודמות"):
            hist = fetch_history(sel, period="1y")
            if hist.empty:
                st.warning("היסטוריה לא זמינה להצגה.")
            else:
                df_plot = add_indicators(hist)
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5, 0.15, 0.15, 0.2])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                             low=df_plot['Low'], close=df_plot['Close'], name='Candles'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], line=dict(color='blue'), name='MA20'), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='lightgrey'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RVOL'], line=dict(color='orange'), name='RVOL'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['OBV'], line=dict(color='green'), name='OBV'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD'], line=dict(color='purple'), name='MACD'), row=4, col=1)
                fig.update_layout(height=900, showlegend=True, title_text=f"{sel} - גרף מפורט")
                st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("לא ניתן לקרוא את קובץ התוצאות הקודם.")

# -------------------------
# סיום
# -------------------------
st.markdown("---")
st.write("הערה: זהו כלי מחקר טכני בלבד ולא ייעוץ השקעות.")

# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from trend_prediction import render_trend_prediction

# Optional ML import
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# ============================
# הגדרות דף + עיצוב מודרני
# ============================
st.set_page_config(page_title="Wyckoff Pro — Swing Scanner", layout="wide", page_icon="◈")

ACCENT = "#f2a93b"      # כתום-ענבר — צבע אקסנט ראשי (בהשראת עיצוב SwingAI)
ACCENT_DARK = "#d98f1f"
BG = "#0b0f17"          # רקע ראשי כהה
PANEL = "#12161f"       # רקע כרטיסים/פאנלים
PANEL_ALT = "#171c28"   # רקע שדות קלט
BORDER = "#242a38"      # גבולות עדינים
TEXT_MUTED = "#8891a5"
BUY_COLOR = "#22c55e"   # ירוק - קנייה
SELL_COLOR = "#ef4444"  # אדום - מכירה

st.markdown(f"""
<style>
    html, body, [class*="css"] {{ font-family: 'Segoe UI', 'Rubik', sans-serif; }}

    /* ---------- רקע כללי ---------- */
    .stApp {{
        background: {BG} !important;
    }}
    .main .block-container {{
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }}

    /* ---------- סרגל צד ---------- */
    section[data-testid="stSidebar"] {{
        background: {PANEL} !important;
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{
        font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px; color: {TEXT_MUTED};
    }}

    /* ---------- כותרת עליונה ---------- */
    .app-header {{
        display: flex; align-items: center; justify-content: space-between;
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 18px;
    }}
    .app-header .title {{
        font-size: 24px; font-weight: 800; color: #f2f4f8; letter-spacing: -0.3px;
        display: flex; align-items: center; gap: 10px;
    }}
    .app-header .title .accent {{ color: {ACCENT}; }}
    .app-header .subtitle {{ color: {TEXT_MUTED}; font-size: 13px; margin-top: 2px; }}
    .status-chip {{
        background: rgba(242,169,59,0.12);
        border: 1px solid rgba(242,169,59,0.35);
        color: {ACCENT};
        padding: 7px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 13px;
        white-space: nowrap;
    }}

    /* ---------- שורת מדדי שוק (Ticker) ---------- */
    .ticker-row {{
        display: flex; gap: 10px; overflow-x: auto; padding: 4px 2px 14px 2px;
        margin-bottom: 4px;
    }}
    .ticker-card {{
        flex: 0 0 auto;
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 10px 16px;
        min-width: 108px;
        text-align: center;
    }}
    .ticker-name {{ font-size: 11px; color: {TEXT_MUTED}; font-weight: 700; letter-spacing: 0.4px; }}
    .ticker-val {{ font-size: 17px; font-weight: 800; color: #f2f4f8; margin-top: 2px; }}
    .ticker-chg {{ font-size: 12px; font-weight: 700; margin-top: 2px; }}

    /* ---------- שורת סטטיסטיקות (Pills) ---------- */
    .stat-pill-row {{ display: flex; gap: 10px; margin: 6px 0 16px 0; flex-wrap: wrap; }}
    .stat-pill {{
        flex: 1; min-width: 90px; text-align: center;
        background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 8px;
    }}
    .stat-pill .num {{ font-size: 22px; font-weight: 800; }}
    .stat-pill .lbl {{ font-size: 11.5px; color: {TEXT_MUTED}; margin-top: 2px; }}

    /* ---------- כרטיס מניה בפיד ---------- */
    .stock-card {{
        background: {PANEL}; border: 1px solid {BORDER}; border-radius: 16px;
        padding: 16px 18px; margin-bottom: 12px;
    }}
    .stock-card-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
    .stock-ticker {{ font-size: 19px; font-weight: 800; color: #f2f4f8; }}
    .stock-sub {{ font-size: 12.5px; color: {TEXT_MUTED}; margin-top: 2px; }}
    .tag {{
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 11.5px; font-weight: 700; margin-inline-end: 6px;
    }}
    .tag-buy {{ background: rgba(34,197,94,0.14); color: {BUY_COLOR}; border: 1px solid rgba(34,197,94,0.35); }}
    .tag-sell {{ background: rgba(239,68,68,0.14); color: {SELL_COLOR}; border: 1px solid rgba(239,68,68,0.35); }}
    .tag-neutral {{ background: rgba(148,163,184,0.14); color: #94a3b8; border: 1px solid rgba(148,163,184,0.30); }}
    .tag-strength {{ background: {PANEL_ALT}; color: #cbd5e1; border: 1px solid {BORDER}; }}

    .stock-note {{ color: #b7c0d8; font-size: 13px; margin: 10px 0 12px 0; line-height: 1.6; }}

    .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }}
    .stat-box {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px 6px; text-align: center; }}
    .stat-box .lbl {{ font-size: 10.5px; color: {TEXT_MUTED}; }}
    .stat-box .val {{ font-size: 14px; font-weight: 800; margin-top: 2px; }}

    .ai-gauge {{
        width: 58px; height: 58px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
    }}
    .ai-gauge-inner {{
        width: 46px; height: 46px; border-radius: 50%; background: {PANEL};
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }}
    .ai-gauge-inner .score {{ font-size: 15px; font-weight: 800; line-height: 1; }}
    .ai-gauge-inner .lbl {{ font-size: 8px; color: {TEXT_MUTED}; margin-top: 1px; letter-spacing: 0.5px; }}

    /* ---------- באנר אזהרה ---------- */
    .top-banner {{
        background: {PANEL_ALT};
        border: 1px solid {BORDER};
        border-right: 3px solid {ACCENT};
        border-radius: 10px;
        padding: 10px 16px;
        margin-bottom: 18px;
        color: #b7c0d8;
        font-size: 13.5px;
    }}

    /* ---------- כותרות פנימיות ---------- */
    h1 {{ font-weight: 800; letter-spacing: -0.5px; color: #f2f4f8; }}
    h2, h3 {{ color: #e6e9f0; font-weight: 700; }}

    /* ---------- כרטיסי מדדים (st.metric) ---------- */
    div[data-testid="stMetric"] {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    }}
    div[data-testid="stMetric"] label {{ color: {TEXT_MUTED} !important; font-size: 12.5px !important; }}
    div[data-testid="stMetricValue"] {{ color: #f2f4f8 !important; font-weight: 800 !important; }}

    /* ---------- טאבים בסגנון pill ---------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: {PANEL};
        padding: 6px;
        border-radius: 14px;
        border: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        border-radius: 10px;
        font-size: 14.5px;
        font-weight: 600;
        color: {TEXT_MUTED};
        background: transparent;
        padding: 0 18px;
    }}
    .stTabs [aria-selected="true"] {{
        background: rgba(0,224,143,0.12) !important;
        color: {ACCENT} !important;
        border: 1px solid rgba(0,224,143,0.35);
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent !important; }}
    .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

    /* ---------- רדיו אופקי בסגנון "פילים" (לסינון/מיון מהיר) ---------- */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        flex-direction: row !important;
        gap: 8px;
        flex-wrap: wrap;
    }}
    div[data-testid="stRadio"] label {{
        background: {PANEL_ALT};
        border: 1px solid {BORDER};
        border-radius: 30px;
        padding: 6px 16px;
        margin: 0 !important;
        transition: all 0.15s ease-in-out;
    }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        background: rgba(242,169,59,0.14) !important;
        border-color: {ACCENT} !important;
    }}
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {{
        color: {TEXT_MUTED}; font-weight: 600; font-size: 13.5px;
    }}
    div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {{
        color: {ACCENT} !important;
    }}
    div[data-testid="stRadio"] label > div:first-child {{ display: none; }}

    /* ---------- כרטיסי סיכום עליונים (עולות/יורדות/פריצה/ציון ממוצע) ---------- */
    .top-stat-row {{ display: flex; gap: 10px; margin: 4px 0 18px 0; flex-wrap: wrap; }}
    .top-stat-card {{
        flex: 1; min-width: 130px; border-radius: 16px; padding: 16px 10px;
        text-align: center; border: 1px solid {BORDER};
    }}
    .top-stat-card .icon {{ font-size: 20px; margin-bottom: 4px; }}
    .top-stat-card .num {{ font-size: 26px; font-weight: 800; line-height: 1; }}
    .top-stat-card .lbl {{ font-size: 12px; color: {TEXT_MUTED}; margin-top: 4px; }}

    /* ---------- טבעת ציון גדולה (בסגנון הכרטיס המעודכן) ---------- */
    .score-ring-big {{
        width: 64px; height: 64px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
    }}
    .score-ring-big-inner {{
        width: 52px; height: 52px; border-radius: 50%; background: {PANEL};
        display: flex; align-items: center; justify-content: center;
    }}
    .score-ring-big-inner .score {{ font-size: 19px; font-weight: 800; }}

    /* ---------- ספארקליין מיני בכרטיס ---------- */
    .sparkline-wrap {{ height: 44px; margin-bottom: 4px; }}

    /* ---------- כרטיס מניה מעודכן (v2) ---------- */
    .stock-card-v2 {{
        background: {PANEL}; border: 1px solid {BORDER}; border-radius: 18px;
        padding: 16px 18px 14px 18px; margin-bottom: 14px;
    }}
    .stock-card-v2-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }}
    .stock-card-v2-ticker {{ font-size: 19px; font-weight: 800; color: #f2f4f8; }}
    .stock-card-v2-price {{ font-size: 22px; font-weight: 800; color: #f2f4f8; margin-top: 6px; }}
    .stock-card-v2-chg {{ font-size: 13px; font-weight: 700; margin-inline-start: 8px; }}
    .stat-row-v2 {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; margin-top: 12px;
                     border-top: 1px solid {BORDER}; padding-top: 10px; }}
    .stat-row-v2 .item {{ text-align: center; }}
    .stat-row-v2 .item .lbl {{ font-size: 10px; color: {TEXT_MUTED}; }}
    .stat-row-v2 .item .val {{ font-size: 13px; font-weight: 800; color: #e6e9f0; margin-top: 2px; }}

    /* ---------- כפתורים ---------- */
    div.stButton > button {{
        border-radius: 10px;
        font-weight: 700;
        border: 1px solid {BORDER};
        background: {PANEL_ALT};
        color: #e6e9f0;
        transition: all 0.15s ease-in-out;
    }}
    div.stButton > button:hover {{
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    div.stButton > button[kind="primary"] {{
        background: {ACCENT} !important;
        color: #06120c !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(0,224,143,0.25);
    }}
    div.stButton > button[kind="primary"]:hover {{
        background: {ACCENT_DARK} !important;
        color: #06120c !important;
    }}
    a[data-testid="stBaseLinkButton-secondary"] {{
        border-radius: 10px; border: 1px solid {BORDER}; background: {PANEL_ALT};
    }}

    /* ---------- שדות קלט ---------- */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
        background: {PANEL_ALT} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        color: #e6e9f0 !important;
    }}
    .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
        background: {PANEL_ALT} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 1px {ACCENT} !important;
    }}

    /* ---------- כרטיסים / expander ---------- */
    div[data-testid="stExpander"] {{
        background: {PANEL};
        border: 1px solid {BORDER} !important;
        border-radius: 14px !important;
        overflow: hidden;
    }}
    div[data-testid="stExpander"] summary {{ font-weight: 600; color: #e6e9f0; }}

    /* ---------- containers עם border ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {PANEL};
        border: 1px solid {BORDER} !important;
        border-radius: 14px !important;
    }}

    /* ---------- טבלאות ---------- */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
    }}

    /* ---------- progress bar כללי ---------- */
    div[data-testid="stProgress"] > div > div {{ background-color: {ACCENT} !important; }}

    /* ---------- badge לציון ---------- */
    .score-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 13px;
    }}

    /* ---------- info/success/warning boxes ---------- */
    div[data-testid="stAlertContainer"] {{
        border-radius: 12px !important;
        border: 1px solid {BORDER} !important;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="app-header">
    <div>
        <div class="title">◈ Wyckoff Pro <span class="accent">Swing Scanner</span></div>
        <div class="subtitle">סורק פריצה מבוסס וייקוף · אינדיקטורים טכניים · חיזוי סטטיסטי</div>
    </div>
    <div class="status-chip">⚡ כלי תמיכה בהחלטה</div>
</div>
""", unsafe_allow_html=True)

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

def safe_div_series(numerator, denominator):
    """חילוק בטוח בין שני Series - מחליף מכנה 0/NaN ב-NaN במקום לזרוק שגיאה."""
    try:
        denom = denominator.replace(0, np.nan)
        return numerator / denom
    except Exception:
        return pd.Series(np.nan, index=numerator.index if hasattr(numerator, "index") else None)

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

BENCHMARK_TICKER = "SPY"

@st.cache_data(ttl=300, show_spinner=False)
def load_benchmark(period="24mo"):
    """טעינת מדד ייחוס (SPY) לחישוב חוזק יחסי."""
    return load_history(BENCHMARK_TICKER, period=period)

@st.cache_data(ttl=300, show_spinner=False)
def load_market_indices():
    """
    טוען מדדי שוק מרכזיים לשורת הטיקר העליונה (בהשראת עיצוב SwingAI).
    כל מדד: (מחיר אחרון, שינוי יומי ב-%). כשל בטיקר בודד לא מפיל את כל השורה.
    """
    indices = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "USD/ILS": "ILS=X"}
    out = {}
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if len(hist) >= 2:
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg_pct = ((last - prev) / prev * 100) if prev != 0 else 0.0
                out[name] = (last, chg_pct)
        except Exception:
            continue
    return out

def render_market_ticker():
    """מציג שורת כרטיסי מדדים עליונה, בסגנון SwingAI."""
    idx = load_market_indices()
    if not idx:
        return
    cards_html = ""
    for name, (val, chg) in idx.items():
        color = BUY_COLOR if chg >= 0 else SELL_COLOR
        sign = "+" if chg >= 0 else ""
        val_fmt = f"{val:,.2f}" if val < 100 else f"{val:,.0f}"
        cards_html += f"""
        <div class="ticker-card">
            <div class="ticker-name">{name}</div>
            <div class="ticker-val">{val_fmt}</div>
            <div class="ticker-chg" style="color:{color};">{sign}{chg:.2f}%</div>
        </div>"""
    st.markdown(f'<div class="ticker-row">{cards_html}</div>', unsafe_allow_html=True)

# ============================
# מד פחד ותאוות בצע — CNN Fear & Greed Index
# ============================
FNG_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
FNG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}
FNG_RATING_HE = {
    "extreme fear": "פחד קיצוני",
    "fear": "פחד",
    "neutral": "ניטרלי",
    "greed": "תאוות בצע",
    "extreme greed": "תאוות בצע קיצונית",
}
FNG_RATING_COLOR = {
    "extreme fear": "#e0392b",
    "fear": "#f2994a",
    "neutral": "#f2d24c",
    "greed": "#a3c644",
    "extreme greed": "#27ae60",
}

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fear_greed_index():
    """שולף את מדד הפחד/תאוות הבצע העדכני של CNN (ציון 0-100 + דירוג + השוואות תקופתיות)."""
    try:
        r = requests.get(FNG_API_URL, headers=FNG_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        fg = data.get("fear_and_greed", {})
        if not fg or "score" not in fg or fg["score"] is None:
            return None
        return {
            "score": float(fg["score"]),
            "rating": str(fg.get("rating", "")).lower().strip(),
            "timestamp": fg.get("timestamp"),
            "previous_close": float(fg["previous_close"]) if fg.get("previous_close") is not None else None,
            "previous_1_week": float(fg["previous_1_week"]) if fg.get("previous_1_week") is not None else None,
            "previous_1_month": float(fg["previous_1_month"]) if fg.get("previous_1_month") is not None else None,
            "previous_1_year": float(fg["previous_1_year"]) if fg.get("previous_1_year") is not None else None,
        }
    except Exception:
        return None

def render_fear_greed_gauge():
    """מד-מחוג חצי-עיגולי של מדד הפחד/תאוות הבצע, בסגנון זהה לאפליקציית CNN Business."""
    fng = fetch_fear_greed_index()
    if not fng:
        st.info("⚠️ לא ניתן לטעון כרגע את מדד הפחד/תאוות הבצע (CNN) — ייתכן חסימת רשת זמנית. נסה 'נקה מטמון' בסיידבר.")
        return

    score = fng["score"]
    rating = fng["rating"]
    rating_he = FNG_RATING_HE.get(rating, rating or "—")
    color = FNG_RATING_COLOR.get(rating, ACCENT)

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": "rgba(0,0,0,0)", "thickness": 0},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20], "color": "#e0392b"},
                {"range": [20, 40], "color": "#f2994a"},
                {"range": [40, 60], "color": "#f2d24c"},
                {"range": [60, 80], "color": "#a3c644"},
                {"range": [80, 100], "color": "#27ae60"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 5},
                "thickness": 0.82,
                "value": score,
            },
        }
    ))
    fig.update_layout(
        height=200,
        margin=dict(t=10, b=0, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6e9f0"),
    )

    ago_txt = ""
    try:
        ts = pd.to_datetime(fng["timestamp"])
        now = pd.Timestamp.now(tz=ts.tzinfo) if ts.tzinfo is not None else pd.Timestamp.now()
        diff_sec = (now - ts).total_seconds()
        hours = int(diff_sec // 3600)
        minutes = int((diff_sec % 3600) // 60)
        ago_txt = f"לפני {hours} שעות" if hours >= 1 else f"לפני {max(minutes, 1)} דקות"
    except Exception:
        ago_txt = ""

    delta_html = ""
    prev_close = fng.get("previous_close")
    if prev_close is not None:
        delta = score - prev_close
        d_color = BUY_COLOR if delta >= 0 else SELL_COLOR
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<span style="color:{d_color}; font-weight:700;">{arrow} {abs(delta):.1f} נקודות</span>'

    st.markdown(f"""
    <div style="background:{PANEL}; border:1px solid {BORDER}; border-radius:16px 16px 0 0;
                padding:14px 18px 0 18px; margin-top:2px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-weight:800; font-size:15px; color:#f2f4f8;">😨 מדד פחד ותאוות בצע — שוק המניות</div>
            <div style="font-size:11.5px; color:{TEXT_MUTED};">מקור: CNN</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f"""
    <div style="background:{PANEL}; border:1px solid {BORDER}; border-top:none; border-radius:0 0 16px 16px;
                text-align:center; padding:0 18px 16px 18px; margin-top:-28px; margin-bottom:18px;">
        <div style="font-size:42px; font-weight:800; color:#f2f4f8; line-height:1;">{score:.0f}</div>
        <div style="font-size:18px; font-weight:700; color:{color}; margin-top:2px;">{rating_he}</div>
        <div style="display:flex; justify-content:center; gap:14px; margin-top:8px; font-size:12.5px; color:{TEXT_MUTED};">
            <span>{ago_txt}</span>
            {delta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📊 השוואה לתקופות קודמות"):
        cols = st.columns(3)
        for col, (key, label) in zip(cols, [("previous_1_week", "לפני שבוע"), ("previous_1_month", "לפני חודש"), ("previous_1_year", "לפני שנה")]):
            val = fng.get(key)
            col.metric(label, f"{val:.0f}" if val is not None else "—")
# ============================
# חדשות ודירוגי אנליסטים — Yahoo Finance (דרך yfinance)
# ============================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_stock_news(ticker, max_items=8):
    """
    שולף כותרות חדשות אחרונות עבור הטיקר. תומך בשני הפורמטים שיfinance
    מחזירה בגרסאות שונות (ישן: שדות שטוחים; חדש: מקונן תחת מפתח 'content').
    """
    try:
        raw = yf.Ticker(ticker).news or []
        items = []
        for it in raw[:max_items]:
            content = it.get("content", it) if isinstance(it, dict) else {}
            title = content.get("title") or (it.get("title") if isinstance(it, dict) else None)
            if not title:
                continue
            publisher = None
            provider = content.get("provider")
            if isinstance(provider, dict):
                publisher = provider.get("displayName")
            publisher = publisher or content.get("publisher") or it.get("publisher") or "מקור לא ידוע"
            link = None
            click_url = content.get("clickThroughUrl") or content.get("canonicalUrl")
            if isinstance(click_url, dict):
                link = click_url.get("url")
            link = link or it.get("link") or "#"
            pub_raw = content.get("pubDate") or content.get("displayTime") or it.get("providerPublishTime")
            items.append({"title": title, "publisher": publisher, "link": link, "pub_raw": pub_raw})
        return items
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_analyst_data(ticker):
    """שולף התפלגות המלצות אנליסטים (strongBuy/buy/hold/sell/strongSell) ויעדי מחיר, מ-Yahoo Finance."""
    result = {"recs": None, "targets": None, "error": None}
    try:
        t = yf.Ticker(ticker)
        try:
            rec_df = t.recommendations
            if rec_df is not None and not rec_df.empty:
                row = rec_df.iloc[0]
                result["recs"] = {
                    "strongBuy": int(row.get("strongBuy", 0) or 0),
                    "buy": int(row.get("buy", 0) or 0),
                    "hold": int(row.get("hold", 0) or 0),
                    "sell": int(row.get("sell", 0) or 0),
                    "strongSell": int(row.get("strongSell", 0) or 0),
                }
        except Exception:
            pass
        try:
            targets = t.analyst_price_targets
            if targets:
                result["targets"] = {
                    "current": targets.get("current"), "low": targets.get("low"),
                    "high": targets.get("high"), "mean": targets.get("mean"),
                }
        except Exception:
            pass
        if result["recs"] is None and result["targets"] is None:
            result["error"] = "אין נתוני אנליסטים זמינים למניה זו ב-Yahoo Finance"
        return result
    except Exception as e:
        result["error"] = f"שגיאה בשליפת נתוני אנליסטים: {e}"
        return result

def _news_time_ago(pub_raw):
    """ממיר חותמת זמן (unix timestamp או מחרוזת תאריך) ל'לפני X שעות' בעברית."""
    try:
        if pub_raw is None:
            return ""
        if isinstance(pub_raw, (int, float)):
            dt = datetime.fromtimestamp(pub_raw)
        else:
            dt = pd.to_datetime(pub_raw)
            if hasattr(dt, "tz_localize") and dt.tzinfo is not None:
                dt = dt.tz_localize(None)
        diff_h = (datetime.now() - dt).total_seconds() / 3600
        if diff_h < 1:
            return "לפני פחות משעה"
        if diff_h < 24:
            return f"לפני {int(diff_h)} שעות"
        return f"לפני {int(diff_h // 24)} ימים"
    except Exception:
        return ""

def render_news_and_analysts(ticker):
    """מציג כותרות חדשות אחרונות + התפלגות המלצות אנליסטים ויעדי מחיר, בסגנון Investing.com."""
    st.markdown("### 📰 חדשות ודירוגי אנליסטים")
    st.caption("נשלף מ-Yahoo Finance בזמן אמת (דרך yfinance) — לא מבוצע אוטומטית בסריקה כדי לא להעמיס.")
    if st.button("טען חדשות + המלצות אנליסטים", key=f"news_btn_{ticker}"):
        with st.spinner("שולף חדשות ונתוני אנליסטים..."):
            news_items = fetch_stock_news(ticker)
            analyst = fetch_analyst_data(ticker)

        st.markdown("#### 📰 כותרות אחרונות")
        if not news_items:
            st.info("לא נמצאו כותרות חדשות עדכניות עבור טיקר זה.")
        else:
            for it in news_items:
                ago = _news_time_ago(it.get("pub_raw"))
                st.markdown(f"""
                <div style="background:{PANEL_ALT}; border:1px solid {BORDER}; border-radius:10px; padding:10px 14px; margin-bottom:8px;">
                    <a href="{it['link']}" target="_blank" style="color:#e6e9f0; font-weight:700; font-size:13.5px; text-decoration:none;">{it['title']}</a>
                    <div style="color:{TEXT_MUTED}; font-size:11.5px; margin-top:4px;">{it['publisher']}{' · ' + ago if ago else ''}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("#### 🎯 המלצות אנליסטים")
        if analyst.get("error") and not analyst.get("recs") and not analyst.get("targets"):
            st.info(analyst["error"])
        else:
            recs = analyst.get("recs")
            if recs and sum(recs.values()) > 0:
                total = sum(recs.values())
                bars_html = ""
                for label, val, color in [
                    ("קנייה חזקה", recs["strongBuy"], BUY_COLOR), ("קנייה", recs["buy"], "#6fcf97"),
                    ("החזקה", recs["hold"], ACCENT), ("מכירה", recs["sell"], "#f2994a"),
                    ("מכירה חזקה", recs["strongSell"], SELL_COLOR),
                ]:
                    pct = (val / total) * 100
                    bars_html += f"""
                    <div style="margin-bottom:6px;">
                        <div style="display:flex; justify-content:space-between; font-size:11.5px; color:{TEXT_MUTED};">
                            <span>{label}</span><span>{val}</span>
                        </div>
                        <div style="background:{BORDER}; border-radius:6px; height:8px; overflow:hidden;">
                            <div style="background:{color}; width:{pct:.0f}%; height:100%;"></div>
                        </div>
                    </div>"""
                st.markdown(bars_html, unsafe_allow_html=True)
            else:
                st.caption("אין נתוני המלצות (Buy/Hold/Sell) זמינים למניה זו.")

            targets = analyst.get("targets")
            if targets and not is_bad(targets.get("mean")):
                tc1, tc2, tc3, tc4 = st.columns(4)
                tc1.metric("נוכחי", f"${targets['current']:.2f}" if not is_bad(targets.get('current')) else "—")
                tc2.metric("יעד נמוך", f"${targets['low']:.2f}" if not is_bad(targets.get('low')) else "—")
                tc3.metric("יעד ממוצע", f"${targets['mean']:.2f}" if not is_bad(targets.get('mean')) else "—")
                tc4.metric("יעד גבוה", f"${targets['high']:.2f}" if not is_bad(targets.get('high')) else "—")
            else:
                st.caption("אין יעדי מחיר אנליסטים זמינים למניה זו.")

# ============================
# איתור קניות/מכירות Insider — SEC EDGAR (Form 4)
# ============================
SEC_USER_AGENT = "WyckoffProScanner/1.0 (contact: liorkeisar@gmail.com)"

@st.cache_data(ttl=86400, show_spinner=False)
def load_sec_ticker_cik_map():
    """טוען מיפוי טיקר -> CIK (מזהה חברה ב-SEC). מתעדכן פעם ביום - הקובץ עצמו משתנה לעיתים רחוקות."""
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        mapping = {}
        for row in data.values():
            try:
                mapping[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
            except Exception:
                continue
        return mapping
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insider_transactions(ticker, lookback_days=90, max_filings=15):
    """
    שולף עסקאות Form 4 (קנייה/מכירה בשוק הפתוח ע"י דירקטורים/מנהלים) עבור טיקר,
    ישירות מ-SEC EDGAR.
    """
    result = {"buys": 0, "sells": 0, "buy_value": 0.0, "sell_value": 0.0, "transactions": [], "error": None}
    try:
        cik_map = load_sec_ticker_cik_map()
        if not cik_map:
            result["error"] = "לא ניתן להתחבר ל-SEC EDGAR כרגע (בעיית רשת או חסימה זמנית)"
            return result

        cik = cik_map.get(ticker.upper())
        if not cik:
            result["error"] = "לא נמצא מזהה CIK עבור טיקר זה ב-SEC (ייתכן שזו לא חברה אמריקאית רשומה)"
            return result

        headers = {"User-Agent": SEC_USER_AGENT}
        subs_resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers, timeout=10)
        subs_resp.raise_for_status()
        subs = subs_resp.json()

        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])

        cutoff = datetime.now() - timedelta(days=lookback_days)
        candidates = []
        for i, form in enumerate(forms):
            if form != "4":
                continue
            try:
                fdate = datetime.strptime(dates[i], "%Y-%m-%d")
            except Exception:
                continue
            if fdate < cutoff:
                continue
            candidates.append((fdate, accessions[i], docs[i]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        candidates = candidates[:max_filings]

        cik_int = int(cik)
        for fdate, accession, doc in candidates:
            try:
                acc_nodash = accession.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200 or not r.content:
                    continue
                root = ET.fromstring(r.content)

                owner_name = ""
                owner_el = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
                if owner_el is not None and owner_el.text:
                    owner_name = owner_el.text

                is_director = root.find(".//reportingOwner/reportingOwnerRelationship/isDirector")
                is_officer = root.find(".//reportingOwner/reportingOwnerRelationship/isOfficer")
                role_parts = []
                if is_director is not None and is_director.text == "1":
                    role_parts.append("דירקטור")
                if is_officer is not None and is_officer.text == "1":
                    role_parts.append("מנהל בכיר")
                role_str = "/".join(role_parts) if role_parts else "בעל עניין"

                for tx in root.findall(".//nonDerivativeTransaction"):
                    code_el = tx.find(".//transactionCoding/transactionCode")
                    shares_el = tx.find(".//transactionAmounts/transactionShares/value")
                    price_el = tx.find(".//transactionAmounts/transactionPricePerShare/value")
                    ad_el = tx.find(".//transactionAmounts/transactionAcquiredDisposedCode/value")
                    if code_el is None or code_el.text is None or shares_el is None or shares_el.text is None:
                        continue

                    code = code_el.text
                    try:
                        shares = float(shares_el.text)
                    except Exception:
                        continue
                    try:
                        price = float(price_el.text) if (price_el is not None and price_el.text) else 0.0
                    except Exception:
                        price = 0.0
                    ad = ad_el.text if (ad_el is not None and ad_el.text) else ""
                    value = shares * price

                    if code == "P" and ad == "A":
                        result["buys"] += 1
                        result["buy_value"] += value
                        result["transactions"].append({
                            "date": fdate.strftime("%Y-%m-%d"), "owner": owner_name, "role": role_str,
                            "type": "קנייה", "shares": shares, "value": value
                        })
                    elif code == "S" and ad == "D":
                        result["sells"] += 1
                        result["sell_value"] += value
                        result["transactions"].append({
                            "date": fdate.strftime("%Y-%m-%d"), "owner": owner_name, "role": role_str,
                            "type": "מכירה", "shares": shares, "value": value
                        })
            except Exception:
                continue

        return result
    except Exception as e:
        result["error"] = f"שגיאה בשליפת נתונים מ-SEC: {e}"
        return result

def add_indicators(df, benchmark_df=None):
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

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["SMA200_slope"] = df["SMA200"].diff(20)

    up_day = df["Close"] > df["Close"].shift(1)
    down_day = df["Close"] < df["Close"].shift(1)
    up_vol = df["Volume"].where(up_day, 0).rolling(20).sum()
    down_vol = df["Volume"].where(down_day, 0).rolling(20).sum().replace(0, np.nan)
    df["UpDownVolRatio"] = up_vol / down_vol

    day_range = (df["High"] - df["Low"]).replace(0, np.nan)
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / day_range
    df["CLV"] = clv
    df["CLV_DownDays"] = clv.where(down_day)
    df["AbsorptionScore"] = df["CLV_DownDays"].rolling(30, min_periods=5).mean()

    ema50_change_15d = df["EMA50"] - df["EMA50"].shift(15)
    df["SidewaysSlope"] = safe_div_series(ema50_change_15d, df["ATR"])

    squeeze_active = (df["UpperBB"] < df["UpperKC"]) & (df["LowerBB"] > df["LowerKC"])
    grp = (~squeeze_active).cumsum()
    df["SqueezeActive"] = squeeze_active
    df["SqueezeStreak"] = squeeze_active.groupby(grp).cumsum()

    BASE_WINDOW, RECENT_EXCLUDE = 50, 12
    df["BaseHigh"] = df["High"].rolling(BASE_WINDOW).max().shift(RECENT_EXCLUDE)

    df["ExtensionATR"] = safe_div_series(df["Close"] - df["EMA20"], df["ATR"])

    df["Return20D"] = df["Close"] / df["Close"].shift(20) - 1

    if benchmark_df is not None and not benchmark_df.empty:
        bench = benchmark_df["Close"].reindex(df.index).ffill()
        rs_line = df["Close"] / bench.replace(0, np.nan)
        df["RS_Line"] = rs_line
        df["RS_MA20"] = rs_line.rolling(20).mean()
    else:
        df["RS_Line"] = np.nan
        df["RS_MA20"] = np.nan

    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_wilder = tr.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    dx = 100 * safe_div_series((plus_di - minus_di).abs(), (plus_di + minus_di))
    df["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    df["High52W"] = df["High"].rolling(252, min_periods=20).max()
    df["Low52W"] = df["Low"].rolling(252, min_periods=20).min()
    df["DailyChangePct"] = df["Close"].pct_change() * 100

    return df
# ============================
# מנוע החלטה לפני פריצה
# ============================

def days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130):
    try:
        if len(df) < base_window + 5:
            return None
        closes = df["Close"]
        prior_high = closes.rolling(base_window).max().shift(1)
        breakout_mask = (closes > prior_high * (1 + threshold)) & prior_high.notna()

        recent_mask = breakout_mask.tail(min(search_window, len(breakout_mask)))
        if not recent_mask.any():
            return None
        true_positions = np.where(recent_mask.values)[0]
        last_true_pos = true_positions[-1]
        days_since = (len(recent_mask) - 1) - last_true_pos
        return int(days_since)
    except Exception:
        return None

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

    base_high = safe_last(df["BaseHigh"]) if "BaseHigh" in df.columns else np.nan
    prox = safe_div(safe_last(df["Close"]), base_high, default=0.0)
    if is_bad(prox) or prox <= 0:
        comps["proximity"] = 0
    elif prox <= 1.00:
        comps["proximity"] = score_component(prox, 0.85, 1.00)
    else:
        comps["proximity"] = max(0, int(round(100 - ((prox - 1.00) / 0.15) * 100)))

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    streak = safe_last(df["SqueezeStreak"]) if "SqueezeStreak" in df.columns else 0
    comps["squeeze_duration"] = score_component(streak, 0, 15)

    close_now = safe_last(df["Close"])
    sma150 = safe_last(df["SMA150"]) if "SMA150" in df.columns else np.nan
    sma200 = safe_last(df["SMA200"]) if "SMA200" in df.columns else np.nan
    sma200_slope = safe_last(df["SMA200_slope"]) if "SMA200_slope" in df.columns else np.nan
    stage2_ok = (not is_bad(close_now) and not is_bad(sma150) and not is_bad(sma200)
                 and close_now > sma150 > sma200 and (is_bad(sma200_slope) or sma200_slope > 0))
    comps["stage2"] = 100 if stage2_ok else (40 if (not is_bad(close_now) and not is_bad(sma150) and close_now > sma150) else 0)

    rs_now = safe_last(df["RS_Line"]) if "RS_Line" in df.columns else np.nan
    rs_prev = safe_last(df["RS_Line"].shift(20)) if "RS_Line" in df.columns else np.nan
    rs_change = safe_div(rs_now - rs_prev, abs(rs_prev) if not is_bad(rs_prev) else np.nan, default=np.nan) if not is_bad(rs_now) else np.nan
    comps["relative_strength"] = score_component(rs_change, -0.05, 0.10) if not is_bad(rs_change) else 50

    updown = safe_last(df["UpDownVolRatio"]) if "UpDownVolRatio" in df.columns else np.nan
    comps["volume_quality"] = score_component(updown, 0.6, 2.0) if not is_bad(updown) else 50

    extension = safe_last(df["ExtensionATR"]) if "ExtensionATR" in df.columns else np.nan
    comps["extension"] = score_component(extension, 0.5, 4.0, invert=True) if not is_bad(extension) else 50

    absorption = safe_last(df["AbsorptionScore"]) if "AbsorptionScore" in df.columns else np.nan
    comps["absorption"] = score_component(absorption, -0.3, 0.3) if not is_bad(absorption) else 50

    sideways_slope = safe_last(df["SidewaysSlope"]) if "SidewaysSlope" in df.columns else np.nan
    comps["sideways"] = score_component(abs(sideways_slope) if not is_bad(sideways_slope) else np.nan, 0, 2.5, invert=True) if not is_bad(sideways_slope) else 50

    weights = {
        "compression": 0.08, "rvol": 0.05, "trend": 0.04, "macd": 0.03, "rsi": 0.03,
        "institutional": 0.04, "proximity": 0.06, "squeeze": 0.02, "squeeze_duration": 0.04,
        "risk": 0.03, "stage2": 0.11, "relative_strength": 0.11, "volume_quality": 0.06,
        "extension": 0.08, "absorption": 0.12, "sideways": 0.10
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    hard_downtrend = (not is_bad(close_now) and not is_bad(sma200) and not is_bad(sma200_slope)
                       and close_now < sma200 and sma200_slope < 0)
    if hard_downtrend:
        final_score = min(final_score, 35)

    ret20 = safe_last(df["Return20D"]) if "Return20D" in df.columns else np.nan
    days_since_bo = days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130)
    already_broken_out = (
        (not is_bad(prox) and prox > 1.10) or
        (not is_bad(extension) and extension > 4.0) or
        (not is_bad(ret20) and ret20 > 0.25) or
        (days_since_bo is not None and days_since_bo > 10)
    )
    if already_broken_out:
        final_score = min(final_score, 30)

    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    risk_metric = 100 - comps.get("risk", 0)

    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if comps.get("squeeze_duration", 0) >= 60: notes.append("כיווץ ממושך")
    if comps.get("stage2", 0) == 100: notes.append("מגמת-על בריאה (Stage 2)")
    if comps.get("relative_strength", 0) >= 70: notes.append("חוזק יחסי למדד")
    if comps.get("volume_quality", 0) >= 70: notes.append("נפח קונים דומיננטי")
    if comps.get("absorption", 0) >= 70: notes.append("איסוף שקט בזמן ירידה (ספיגת היצע)")
    if comps.get("sideways", 0) >= 75: notes.append("מגמה הצידה (טווח אמיתי)")
    if hard_downtrend: notes.append("⚠️ מגמת-על יורדת — סיכון גבוה")
    if already_broken_out:
        if days_since_bo is not None and days_since_bo > 10:
            notes.append(f"⚠️ המניה כבר פרצה לפני כ-{days_since_bo} ימי מסחר — לא קדם-פריצה")
        else:
            notes.append("⚠️ נראה שהמניה כבר פרצה/מורחקת מהבסיס — לא אידיאלית לכניסה כ'קדם-פריצה'")
    if not already_broken_out and not is_bad(prox) and prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric, "components": comps, "note": note,
            "rsi_last": safe_last(df["RSI"]) if "RSI" in df.columns else np.nan,
            "rvol_last": rvol, "atr_pct": atr_pct, "stage2_ok": stage2_ok,
            "already_broken_out": already_broken_out, "hard_downtrend": hard_downtrend,
            "days_since_breakout": days_since_bo}
# ============================
# מנוע החלטה לפני פריצה
# ============================

def days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130):
    try:
        if len(df) < base_window + 5:
            return None
        closes = df["Close"]
        prior_high = closes.rolling(base_window).max().shift(1)
        breakout_mask = (closes > prior_high * (1 + threshold)) & prior_high.notna()

        recent_mask = breakout_mask.tail(min(search_window, len(breakout_mask)))
        if not recent_mask.any():
            return None
        true_positions = np.where(recent_mask.values)[0]
        last_true_pos = true_positions[-1]
        days_since = (len(recent_mask) - 1) - last_true_pos
        return int(days_since)
    except Exception:
        return None

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

    base_high = safe_last(df["BaseHigh"]) if "BaseHigh" in df.columns else np.nan
    prox = safe_div(safe_last(df["Close"]), base_high, default=0.0)
    if is_bad(prox) or prox <= 0:
        comps["proximity"] = 0
    elif prox <= 1.00:
        comps["proximity"] = score_component(prox, 0.85, 1.00)
    else:
        comps["proximity"] = max(0, int(round(100 - ((prox - 1.00) / 0.15) * 100)))

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    streak = safe_last(df["SqueezeStreak"]) if "SqueezeStreak" in df.columns else 0
    comps["squeeze_duration"] = score_component(streak, 0, 15)

    close_now = safe_last(df["Close"])
    sma150 = safe_last(df["SMA150"]) if "SMA150" in df.columns else np.nan
    sma200 = safe_last(df["SMA200"]) if "SMA200" in df.columns else np.nan
    sma200_slope = safe_last(df["SMA200_slope"]) if "SMA200_slope" in df.columns else np.nan
    stage2_ok = (not is_bad(close_now) and not is_bad(sma150) and not is_bad(sma200)
                 and close_now > sma150 > sma200 and (is_bad(sma200_slope) or sma200_slope > 0))
    comps["stage2"] = 100 if stage2_ok else (40 if (not is_bad(close_now) and not is_bad(sma150) and close_now > sma150) else 0)

    rs_now = safe_last(df["RS_Line"]) if "RS_Line" in df.columns else np.nan
    rs_prev = safe_last(df["RS_Line"].shift(20)) if "RS_Line" in df.columns else np.nan
    rs_change = safe_div(rs_now - rs_prev, abs(rs_prev) if not is_bad(rs_prev) else np.nan, default=np.nan) if not is_bad(rs_now) else np.nan
    comps["relative_strength"] = score_component(rs_change, -0.05, 0.10) if not is_bad(rs_change) else 50

    updown = safe_last(df["UpDownVolRatio"]) if "UpDownVolRatio" in df.columns else np.nan
    comps["volume_quality"] = score_component(updown, 0.6, 2.0) if not is_bad(updown) else 50

    extension = safe_last(df["ExtensionATR"]) if "ExtensionATR" in df.columns else np.nan
    comps["extension"] = score_component(extension, 0.5, 4.0, invert=True) if not is_bad(extension) else 50

    absorption = safe_last(df["AbsorptionScore"]) if "AbsorptionScore" in df.columns else np.nan
    comps["absorption"] = score_component(absorption, -0.3, 0.3) if not is_bad(absorption) else 50

    sideways_slope = safe_last(df["SidewaysSlope"]) if "SidewaysSlope" in df.columns else np.nan
    comps["sideways"] = score_component(abs(sideways_slope) if not is_bad(sideways_slope) else np.nan, 0, 2.5, invert=True) if not is_bad(sideways_slope) else 50

    weights = {
        "compression": 0.08, "rvol": 0.05, "trend": 0.04, "macd": 0.03, "rsi": 0.03,
        "institutional": 0.04, "proximity": 0.06, "squeeze": 0.02, "squeeze_duration": 0.04,
        "risk": 0.03, "stage2": 0.11, "relative_strength": 0.11, "volume_quality": 0.06,
        "extension": 0.08, "absorption": 0.12, "sideways": 0.10
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    hard_downtrend = (not is_bad(close_now) and not is_bad(sma200) and not is_bad(sma200_slope)
                       and close_now < sma200 and sma200_slope < 0)
    if hard_downtrend:
        final_score = min(final_score, 35)

    ret20 = safe_last(df["Return20D"]) if "Return20D" in df.columns else np.nan
    days_since_bo = days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130)
    already_broken_out = (
        (not is_bad(prox) and prox > 1.10) or
        (not is_bad(extension) and extension > 4.0) or
        (not is_bad(ret20) and ret20 > 0.25) or
        (days_since_bo is not None and days_since_bo > 10)
    )
    if already_broken_out:
        final_score = min(final_score, 30)

    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    risk_metric = 100 - comps.get("risk", 0)

    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if comps.get("squeeze_duration", 0) >= 60: notes.append("כיווץ ממושך")
    if comps.get("stage2", 0) == 100: notes.append("מגמת-על בריאה (Stage 2)")
    if comps.get("relative_strength", 0) >= 70: notes.append("חוזק יחסי למדד")
    if comps.get("volume_quality", 0) >= 70: notes.append("נפח קונים דומיננטי")
    if comps.get("absorption", 0) >= 70: notes.append("איסוף שקט בזמן ירידה (ספיגת היצע)")
    if comps.get("sideways", 0) >= 75: notes.append("מגמה הצידה (טווח אמיתי)")
    if hard_downtrend: notes.append("⚠️ מגמת-על יורדת — סיכון גבוה")
    if already_broken_out:
        if days_since_bo is not None and days_since_bo > 10:
            notes.append(f"⚠️ המניה כבר פרצה לפני כ-{days_since_bo} ימי מסחר — לא קדם-פריצה")
        else:
            notes.append("⚠️ נראה שהמניה כבר פרצה/מורחקת מהבסיס — לא אידיאלית לכניסה כ'קדם-פריצה'")
    if not already_broken_out and not is_bad(prox) and prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric, "components": comps, "note": note,
            "rsi_last": safe_last(df["RSI"]) if "RSI" in df.columns else np.nan,
            "rvol_last": rvol, "atr_pct": atr_pct, "stage2_ok": stage2_ok,
            "already_broken_out": already_broken_out, "hard_downtrend": hard_downtrend,
            "days_since_breakout": days_since_bo}
# ============================
# מנוע החלטה לפני פריצה
# ============================

def days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130):
    try:
        if len(df) < base_window + 5:
            return None
        closes = df["Close"]
        prior_high = closes.rolling(base_window).max().shift(1)
        breakout_mask = (closes > prior_high * (1 + threshold)) & prior_high.notna()

        recent_mask = breakout_mask.tail(min(search_window, len(breakout_mask)))
        if not recent_mask.any():
            return None
        true_positions = np.where(recent_mask.values)[0]
        last_true_pos = true_positions[-1]
        days_since = (len(recent_mask) - 1) - last_true_pos
        return int(days_since)
    except Exception:
        return None

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

    base_high = safe_last(df["BaseHigh"]) if "BaseHigh" in df.columns else np.nan
    prox = safe_div(safe_last(df["Close"]), base_high, default=0.0)
    if is_bad(prox) or prox <= 0:
        comps["proximity"] = 0
    elif prox <= 1.00:
        comps["proximity"] = score_component(prox, 0.85, 1.00)
    else:
        comps["proximity"] = max(0, int(round(100 - ((prox - 1.00) / 0.15) * 100)))

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    streak = safe_last(df["SqueezeStreak"]) if "SqueezeStreak" in df.columns else 0
    comps["squeeze_duration"] = score_component(streak, 0, 15)

    close_now = safe_last(df["Close"])
    sma150 = safe_last(df["SMA150"]) if "SMA150" in df.columns else np.nan
    sma200 = safe_last(df["SMA200"]) if "SMA200" in df.columns else np.nan
    sma200_slope = safe_last(df["SMA200_slope"]) if "SMA200_slope" in df.columns else np.nan
    stage2_ok = (not is_bad(close_now) and not is_bad(sma150) and not is_bad(sma200)
                 and close_now > sma150 > sma200 and (is_bad(sma200_slope) or sma200_slope > 0))
    comps["stage2"] = 100 if stage2_ok else (40 if (not is_bad(close_now) and not is_bad(sma150) and close_now > sma150) else 0)

    rs_now = safe_last(df["RS_Line"]) if "RS_Line" in df.columns else np.nan
    rs_prev = safe_last(df["RS_Line"].shift(20)) if "RS_Line" in df.columns else np.nan
    rs_change = safe_div(rs_now - rs_prev, abs(rs_prev) if not is_bad(rs_prev) else np.nan, default=np.nan) if not is_bad(rs_now) else np.nan
    comps["relative_strength"] = score_component(rs_change, -0.05, 0.10) if not is_bad(rs_change) else 50

    updown = safe_last(df["UpDownVolRatio"]) if "UpDownVolRatio" in df.columns else np.nan
    comps["volume_quality"] = score_component(updown, 0.6, 2.0) if not is_bad(updown) else 50

    extension = safe_last(df["ExtensionATR"]) if "ExtensionATR" in df.columns else np.nan
    comps["extension"] = score_component(extension, 0.5, 4.0, invert=True) if not is_bad(extension) else 50

    absorption = safe_last(df["AbsorptionScore"]) if "AbsorptionScore" in df.columns else np.nan
    comps["absorption"] = score_component(absorption, -0.3, 0.3) if not is_bad(absorption) else 50

    sideways_slope = safe_last(df["SidewaysSlope"]) if "SidewaysSlope" in df.columns else np.nan
    comps["sideways"] = score_component(abs(sideways_slope) if not is_bad(sideways_slope) else np.nan, 0, 2.5, invert=True) if not is_bad(sideways_slope) else 50

    weights = {
        "compression": 0.08, "rvol": 0.05, "trend": 0.04, "macd": 0.03, "rsi": 0.03,
        "institutional": 0.04, "proximity": 0.06, "squeeze": 0.02, "squeeze_duration": 0.04,
        "risk": 0.03, "stage2": 0.11, "relative_strength": 0.11, "volume_quality": 0.06,
        "extension": 0.08, "absorption": 0.12, "sideways": 0.10
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    hard_downtrend = (not is_bad(close_now) and not is_bad(sma200) and not is_bad(sma200_slope)
                       and close_now < sma200 and sma200_slope < 0)
    if hard_downtrend:
        final_score = min(final_score, 35)

    ret20 = safe_last(df["Return20D"]) if "Return20D" in df.columns else np.nan
    days_since_bo = days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130)
    already_broken_out = (
        (not is_bad(prox) and prox > 1.10) or
        (not is_bad(extension) and extension > 4.0) or
        (not is_bad(ret20) and ret20 > 0.25) or
        (days_since_bo is not None and days_since_bo > 10)
    )
    if already_broken_out:
        final_score = min(final_score, 30)

    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    risk_metric = 100 - comps.get("risk", 0)

    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if comps.get("squeeze_duration", 0) >= 60: notes.append("כיווץ ממושך")
    if comps.get("stage2", 0) == 100: notes.append("מגמת-על בריאה (Stage 2)")
    if comps.get("relative_strength", 0) >= 70: notes.append("חוזק יחסי למדד")
    if comps.get("volume_quality", 0) >= 70: notes.append("נפח קונים דומיננטי")
    if comps.get("absorption", 0) >= 70: notes.append("איסוף שקט בזמן ירידה (ספיגת היצע)")
    if comps.get("sideways", 0) >= 75: notes.append("מגמה הצידה (טווח אמיתי)")
    if hard_downtrend: notes.append("⚠️ מגמת-על יורדת — סיכון גבוה")
    if already_broken_out:
        if days_since_bo is not None and days_since_bo > 10:
            notes.append(f"⚠️ המניה כבר פרצה לפני כ-{days_since_bo} ימי מסחר — לא קדם-פריצה")
        else:
            notes.append("⚠️ נראה שהמניה כבר פרצה/מורחקת מהבסיס — לא אידיאלית לכניסה כ'קדם-פריצה'")
    if not already_broken_out and not is_bad(prox) and prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric, "components": comps, "note": note,
            "rsi_last": safe_last(df["RSI"]) if "RSI" in df.columns else np.nan,
            "rvol_last": rvol, "atr_pct": atr_pct, "stage2_ok": stage2_ok,
            "already_broken_out": already_broken_out, "hard_downtrend": hard_downtrend,
            "days_since_breakout": days_since_bo}
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

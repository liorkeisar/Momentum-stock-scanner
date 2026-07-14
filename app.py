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
# בעקבות בקשה לסגנון כמו Investing.com: החלטנו במכוון *לא* לגרד (scrape) את
# investing.com עצמו - זה נגד תנאי השימוש שלהם, שביר (הם משנים HTML לעיתים
# קרובות), ועלול לגרום לחסימת IP. במקום זה, נעזרים ב-yfinance (שכבר מותקן
# ב-requirements.txt שלך) שמביא נתונים דומים מ-Yahoo Finance באופן חוקי ויציב:
# כותרות חדשות אחרונות + התפלגות המלצות אנליסטים (Buy/Hold/Sell) + יעדי מחיר.
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
# זהו המקור הכי "חד משמעי" שאפשר לשלב בחינם: Form 4 הוא גילוי רגולטורי מחייב
# (SEC) על כל עסקת קנייה/מכירה של דירקטורים ומנהלים בכירים, מוגש תוך יומיים
# עסקים. זה לא "מוסדי" במובן של קרנות גדולות (לזה יש 13F/13D, ברבעון/בפיגור),
# אבל זו העסקה הכי קרובה ל"מישהו בפנים קונה במזומן משלו" שיש בציבור.
#
# ⚠️ SEC דורשת User-Agent מזוהה עם פרטי קשר אמיתיים (מדיניות Fair Access).
# בקשות עם UA גנרי/placeholder (כמו example.com) נחסמות/מוזנחות - זה היה
# הבאג שגרם לכל תוצאה להראות "לא נמצא" גם כשהיו עסקאות בפועל.
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
    ישירות מ-SEC EDGAR. מחזיר dict עם סיכום קניות/מכירות ורשימת עסקאות בודדות.
    בכוונה לא נכלל בתוך הסריקה המרוכזת (bulk scan) - מדובר בכמה בקשות רשת
    לכל טיקר, וזה עלול להיות איטי מדי ולחרוג ממדיניות השימוש ההוגן של SEC
    כשסורקים מאות טיקרים. משתמשים בזה רק לפי דרישה (כפתור) בדוח המפורט לטיקר בודד.
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

                    # P = רכישה בשוק הפתוח, S = מכירה בשוק הפתוח (קודי עסקה תקניים של SEC)
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

    # --- מגמת-על (Stage 2 לפי Weinstein/Minervini): SMA150/SMA200 ---
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["SMA200_slope"] = df["SMA200"].diff(20)  # שיפוע ב-20 הימים האחרונים

    # --- איכות נפח: יחס נפח-עולה/נפח-יורד על פני 20 יום ---
    up_day = df["Close"] > df["Close"].shift(1)
    down_day = df["Close"] < df["Close"].shift(1)
    up_vol = df["Volume"].where(up_day, 0).rolling(20).sum()
    down_vol = df["Volume"].where(down_day, 0).rolling(20).sum().replace(0, np.nan)
    df["UpDownVolRatio"] = up_vol / down_vol

    # --- איסוף/ספיגה בזמן ירידה (Wyckoff absorption): איפה הסגירה ביחס לטווח היום,
    # ממוצע רק על ימים אדומים. CLV חיובי בימי ירידה = קונים נכנסים וסופגים היצע
    # למרות שהיום נסגר במינוס - זה בדיוק סימן האיסוף השקט שמבקשים לאתר.
    day_range = (df["High"] - df["Low"]).replace(0, np.nan)
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / day_range  # טווח -1 עד 1
    df["CLV"] = clv
    df["CLV_DownDays"] = clv.where(down_day)
    df["AbsorptionScore"] = df["CLV_DownDays"].rolling(30, min_periods=5).mean()

    # --- תנועה "הצידה" בפועל: שיפוע EMA50 מנורמל ב-ATR. ערך קרוב ל-0 = טווח אמיתי
    # (לא טרנד), בניגוד לכיווץ שקורה בתוך טרנד עולה חד (שגם הוא לגיטימי אבל שונה) ---
    ema50_change_15d = df["EMA50"] - df["EMA50"].shift(15)
    df["SidewaysSlope"] = safe_div_series(ema50_change_15d, df["ATR"])

    # --- משך ה-Squeeze (כמה ימים רצופים הרצועות בתוך הערוץ) ---
    squeeze_active = (df["UpperBB"] < df["UpperKC"]) & (df["LowerBB"] > df["LowerKC"])
    grp = (~squeeze_active).cumsum()
    df["SqueezeActive"] = squeeze_active
    df["SqueezeStreak"] = squeeze_active.groupby(grp).cumsum()

    # --- "התנגדות ישנה" (Base High) — שיא הבסיס *לפני* הריצה האחרונה ---
    # שימוש בשיא 20 יום גולמי ("High20") גורם למניה שכבר פרצה להראות תמיד
    # "קרובה לשיא" כי החלון הנע פשוט רודף אחרי המחיר החדש. כאן משתמשים בשיא
    # של חלון ישן יותר (BASE_WINDOW) שמוזז אחורה (RECENT_EXCLUDE) כדי לשקף
    # את רמת ההתנגדות שנוצרה *לפני* תנועת המחיר האחרונה.
    BASE_WINDOW, RECENT_EXCLUDE = 50, 12
    df["BaseHigh"] = df["High"].rolling(BASE_WINDOW).max().shift(RECENT_EXCLUDE)

    # --- מדד "התרחקות" (Extension) ממוצע נע 20 יום, ביחידות ATR ---
    # מניה שכבר עשתה תנועה חדה ורחוקה מה-EMA20 שלה (במונחי ATR) כבר "רצה" -
    # זה ההפך מתבנית קדם-פריצה שבה המחיר מהודק ליד הממוצעים.
    df["ExtensionATR"] = safe_div_series(df["Close"] - df["EMA20"], df["ATR"])

    # --- תשואת 20 יום — אם המניה כבר עלתה חזק לאחרונה, כנראה שהפריצה כבר קרתה ---
    df["Return20D"] = df["Close"] / df["Close"].shift(20) - 1

    # --- חוזק יחסי מול מדד ייחוס (RS Line) ---
    if benchmark_df is not None and not benchmark_df.empty:
        bench = benchmark_df["Close"].reindex(df.index).ffill()
        rs_line = df["Close"] / bench.replace(0, np.nan)
        df["RS_Line"] = rs_line
        df["RS_MA20"] = rs_line.rolling(20).mean()
    else:
        df["RS_Line"] = np.nan
        df["RS_MA20"] = np.nan

    # --- ADX (Average Directional Index, 14) — עוצמת המגמה (לא כיוונה) ---
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_wilder = tr.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    dx = 100 * safe_div_series((plus_di - minus_di).abs(), (plus_di + minus_di))
    df["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # --- שיא/שפל 52 שבועות (~252 ימי מסחר) ושינוי יומי באחוזים - לשורת הכרטיס ---
    df["High52W"] = df["High"].rolling(252, min_periods=20).max()
    df["Low52W"] = df["Low"].rolling(252, min_periods=20).min()
    df["DailyChangePct"] = df["Close"].pct_change() * 100

    return df



# ============================
# מנוע החלטה לפני פריצה
# ============================

def days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130):
    """
    סורק אחורה עד search_window ימים ומאתר את הפעם האחרונה שבה המחיר חצה
    מעל השיא של base_window הימים שלפניו ביותר מ-threshold. מחזיר כמה ימי מסחר
    עברו מאז (0 = פרצה היום). זהו האיתור הישיר והאמין ביותר ל"כבר פרצה לפני זמן",
    בניגוד למדדים רגעיים (extension/proximity) שיכולים "לפספס" פריצה ישנה אם
    המניה ממשיכה לזחול מעלה בהדרגה בלי לתקן.

    הערה טכנית: החישוב הגלגלי (rolling) מתבצע על כל ההיסטוריה הזמינה ולא רק על
    חלון חתוך, כדי שלכל יום בטווח החיפוש תמיד יהיה מספיק היסטוריה מאחוריו לחישוב
    השיא הקודם - חיתוך מוקדם מדי היה עלול "לפספס" בדיוק פריצות שקרו קרוב לקצה החלון.
    """
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

    # --- קרבה לפריצה מול "התנגדות ישנה" (BaseHigh), לא מול שיא 20 יום שרודף אחרי המחיר ---
    base_high = safe_last(df["BaseHigh"]) if "BaseHigh" in df.columns else np.nan
    prox = safe_div(safe_last(df["Close"]), base_high, default=0.0)
    if is_bad(prox) or prox <= 0:
        comps["proximity"] = 0
    elif prox <= 1.00:
        comps["proximity"] = score_component(prox, 0.85, 1.00)
    else:
        # מעל ההתנגדות הישנה: 100 מיד מעל, יורד לינארית ל-0 ב-15%+ מעליה (כבר פרצה משמעותית)
        comps["proximity"] = max(0, int(round(100 - ((prox - 1.00) / 0.15) * 100)))

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    # --- משך ה-Squeeze: כמה זמן רצוף המניה בכיווץ (ככל שיותר, יותר אנרגיה לפריצה) ---
    streak = safe_last(df["SqueezeStreak"]) if "SqueezeStreak" in df.columns else 0
    comps["squeeze_duration"] = score_component(streak, 0, 15)

    # --- Stage 2 (Weinstein/Minervini): מחיר מעל SMA150/200 עולה = מגמת-על בריאה ---
    close_now = safe_last(df["Close"])
    sma150 = safe_last(df["SMA150"]) if "SMA150" in df.columns else np.nan
    sma200 = safe_last(df["SMA200"]) if "SMA200" in df.columns else np.nan
    sma200_slope = safe_last(df["SMA200_slope"]) if "SMA200_slope" in df.columns else np.nan
    stage2_ok = (not is_bad(close_now) and not is_bad(sma150) and not is_bad(sma200)
                 and close_now > sma150 > sma200 and (is_bad(sma200_slope) or sma200_slope > 0))
    comps["stage2"] = 100 if stage2_ok else (40 if (not is_bad(close_now) and not is_bad(sma150) and close_now > sma150) else 0)

    # --- חוזק יחסי מול מדד ייחוס (RS Line) ---
    rs_now = safe_last(df["RS_Line"]) if "RS_Line" in df.columns else np.nan
    rs_prev = safe_last(df["RS_Line"].shift(20)) if "RS_Line" in df.columns else np.nan
    rs_change = safe_div(rs_now - rs_prev, abs(rs_prev) if not is_bad(rs_prev) else np.nan, default=np.nan) if not is_bad(rs_now) else np.nan
    comps["relative_strength"] = score_component(rs_change, -0.05, 0.10) if not is_bad(rs_change) else 50

    # --- איכות נפח: יחס נפח-עולה/נפח-יורד ---
    updown = safe_last(df["UpDownVolRatio"]) if "UpDownVolRatio" in df.columns else np.nan
    comps["volume_quality"] = score_component(updown, 0.6, 2.0) if not is_bad(updown) else 50

    # --- מדד התרחקות (Extension): כמה ATR המחיר רחוק מ-EMA20 ---
    extension = safe_last(df["ExtensionATR"]) if "ExtensionATR" in df.columns else np.nan
    comps["extension"] = score_component(extension, 0.5, 4.0, invert=True) if not is_bad(extension) else 50

    # --- איסוף/ספיגה בזמן ירידה (Wyckoff absorption) - הרכיב המרכזי המבוקש:
    # CLV ממוצע חיובי בימי ירידה = המחיר נסגר קרוב לשיא הטווח היומי למרות יום אדום,
    # כלומר יש קונים שסופגים היצע בזמן חולשה - זהו איתות איסוף שקט אמיתי. ---
    absorption = safe_last(df["AbsorptionScore"]) if "AbsorptionScore" in df.columns else np.nan
    comps["absorption"] = score_component(absorption, -0.3, 0.3) if not is_bad(absorption) else 50

    # --- תנועה "הצידה" בפועל (לא טרנד) - שיפוע EMA50 מנורמל ב-ATR קרוב ל-0 ---
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

    # וטו קשיח #1: מגמת-על שבורה (מתחת ל-SMA200 יורד)
    hard_downtrend = (not is_bad(close_now) and not is_bad(sma200) and not is_bad(sma200_slope)
                       and close_now < sma200 and sma200_slope < 0)
    if hard_downtrend:
        final_score = min(final_score, 35)

    # וטו קשיח #2: המניה כבר פרצה משמעותית מעל ההתנגדות הישנה ו/או רחוקה מדי מהממוצעים,
    # ו/או שהפריצה בפועל כבר קרתה לפני יותר מ-2 שבועות (גם אם היא ממשיכה לזחול מעלה בהדרגה) -
    # זו כבר לא "קדם-פריצה", היא פריצה שכבר קרתה.
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
            "std20_pct": safe_div(w["Close"].rolling(20).std().iloc[-1] if len(w) >= 20 else np.nan, w["Close"].iloc[-1], default=np.nan),
            "rvol": safe_div(w["Volume"].iloc[-1], vol_ma, default=1.0),
            "ema20_ema50": safe_div(ema20, ema50, default=1.0),
            "macd_diff": w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
            "macd_diff_pct": safe_div(
                w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
                w["Close"].iloc[-1], default=np.nan
            ),
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

def backtest_score_calibration(df_full, lookahead=5, step=3, min_history=250):
    """
    Backtest פשוט לכיול הציון: מריץ את מנוע ההחלטה (compute_breakout_decision)
    על כל נקודה היסטורית (בצעדים של 'step' ימים כדי לחסוך זמן ריצה), ובודק אם
    בפועל התרחשה פריצה מעל שיא 20 הימים הקודמים תוך 'lookahead' ימי מסחר.
    מחזיר טבלת סיכום לפי דלי-ציון (score bucket) עם שיעור ההצלחה בפועל.
    שימו לב: זהו backtest פשוט (ללא עמלות/סליפג'), נועד לכיול הציון בלבד ולא לבדיקת אסטרטגיית מסחר מלאה.
    """
    try:
        n = len(df_full)
        if n < min_history + lookahead + 10:
            return None, None

        scores, outcomes, dates = [], [], []
        for i in range(min_history, n - lookahead, step):
            slice_df = df_full.iloc[:i + 1]
            res = compute_breakout_decision(slice_df)
            score = res["score"]

            window_high = df_full["High"].iloc[max(0, i - 19):i + 1].max()
            future = df_full["Close"].iloc[i + 1:i + 1 + lookahead]
            if future.empty or is_bad(window_high):
                continue
            broke = bool(future.max() > window_high * 1.005)

            scores.append(score)
            outcomes.append(1 if broke else 0)
            dates.append(df_full.index[i])

        if not scores:
            return None, None

        bt_df = pd.DataFrame({"date": dates, "score": scores, "outcome": outcomes})
        bins = [0, 40, 55, 70, 85, 101]
        labels = ["0-39 (חלש)", "40-54 (בינוני)", "55-69 (טוב)", "70-84 (חזק)", "85-100 (מצוין)"]
        bt_df["bucket"] = pd.cut(bt_df["score"], bins=bins, labels=labels, right=False)

        summary = bt_df.groupby("bucket", observed=True).agg(
            מקרים=("outcome", "size"),
            שיעור_הצלחה=("outcome", "mean")
        ).reset_index()
        summary["שיעור_הצלחה"] = (summary["שיעור_הצלחה"] * 100).round(1)
        summary = summary.rename(columns={"bucket": "טווח ציון"})
        return summary, bt_df
    except Exception:
        return None, None

def statistical_similarity_prediction(df, tolerance=0.15, lookahead=5):
    """
    מחפש חלונות היסטוריים 'דומים' להיום ובודק כמה מהם פרצו בעבר.
    שימוש בנרמול z-score (במקום השוואת % גולמי) כדי שהמדדים לא יוטו
    ע"י סקאלת המחיר של המניה (macd_diff, std20 בדולרים משתנים לפי מחיר המניה).
    """
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}
        clean = feats.dropna()
        if clean.empty or len(clean) < 5:
            return {"count": 0, "successes": 0, "rate": 0.0}

        feature_keys = ["std20_pct", "rvol", "ema20_ema50", "macd_diff_pct", "rsi"]
        feature_keys = [k for k in feature_keys if k in clean.columns]

        target = clean.iloc[-1]
        candidates = clean.iloc[:-1]
        if candidates.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}

        means = candidates[feature_keys].mean()
        stds = candidates[feature_keys].std().replace(0, np.nan).fillna(1.0)

        target_z = (target[feature_keys] - means) / stds
        cand_z = (candidates[feature_keys] - means) / stds

        # מרחק אוקלידי מנורמל בין כל חלון היסטורי לבין המצב הנוכחי
        dist = np.sqrt(((cand_z - target_z) ** 2).sum(axis=1))

        # סף מרחק נגזר מסליידר הטולרנס (0.05-0.5) → סקאלת z-score סבירה
        distance_threshold = tolerance * np.sqrt(len(feature_keys)) * 2.5

        sim_mask = dist <= distance_threshold
        sim = candidates[sim_mask]
        count = len(sim)
        successes = int(sim['label'].sum()) if 'label' in sim.columns else 0
        rate = (successes / count) if count > 0 else 0.0
        return {"count": count, "successes": successes, "rate": float(rate)}
    except Exception:
        return {"count": 0, "successes": 0, "rate": 0.0}

def find_swing_points(df, order=3, window=60):
    """
    זיהוי נקודות תפנית אמיתיות (fractals) - נקודה נחשבת שיא/שפל מקומי
    אם היא הגבוהה/הנמוכה ביותר ב-'order' ימים לפני ואחריה משני הצדדים.
    מחזיר רשימות של (אינדקס, מחיר) לשיאים ולשפלים בטווח האחרון.
    """
    w = df.tail(window)
    highs = w["High"].values
    lows = w["Low"].values
    n = len(w)
    swing_highs, swing_lows = [], []
    for i in range(order, n - order):
        h_window = highs[i - order:i + order + 1]
        l_window = lows[i - order:i + order + 1]
        if highs[i] == h_window.max():
            swing_highs.append((i, highs[i]))
        if lows[i] == l_window.min():
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows

def pattern_detection_vcp_like(df):
    """
    זיהוי VCP (Volatility Contraction Pattern) מבוסס נקודות תפנית אמיתיות,
    במקום דגימה גסה כל שליש מהחלון. בודק: שיאים יורדים, שפלים עולים,
    וכיווץ מתקדם (כל תנודה קטנה מקודמתה - התבנית האמיתית של VCP).
    """
    try:
        window = 60
        if len(df) < window:
            return {"match": False, "desc": "לא מספיק נתונים לתבנית", "contractions": 0}

        swing_highs, swing_lows = find_swing_points(df, order=3, window=window)

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"match": False, "desc": "לא נמצאו מספיק נקודות תפנית", "contractions": 0}

        recent_highs = [p for _, p in swing_highs[-4:]]
        recent_lows = [p for _, p in swing_lows[-4:]]

        lower_highs = len(recent_highs) >= 2 and all(
            recent_highs[i] >= recent_highs[i + 1] for i in range(len(recent_highs) - 1)
        )
        higher_lows = len(recent_lows) >= 2 and all(
            recent_lows[i] <= recent_lows[i + 1] for i in range(len(recent_lows) - 1)
        )

        # מדידת כיווץ אמיתי: טווח (high-low) של כל "גל" בין שיא לשפל עוקבים,
        # ובודקים שהטווחים הולכים ומצטמצמים - זהו הליבה של VCP אמיתי.
        swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
        wave_ranges = []
        for i in range(1, len(swings)):
            wave_ranges.append(abs(swings[i][1] - swings[i - 1][1]))
        contractions = 0
        if len(wave_ranges) >= 2:
            for i in range(1, len(wave_ranges)):
                if wave_ranges[i] < wave_ranges[i - 1]:
                    contractions += 1
        contraction_ratio = contractions / max(1, len(wave_ranges) - 1) if wave_ranges else 0
        compression = contraction_ratio >= 0.5

        w = df.tail(window)
        std_vals = w["Close"].rolling(10).std().dropna()
        std_trend = np.polyfit(range(len(std_vals)), std_vals, 1)[0] if len(std_vals) > 2 else 0
        std_declining = std_trend < 0

        match = lower_highs and higher_lows and compression and std_declining
        desc = []
        if lower_highs: desc.append("שיאים יורדים")
        if higher_lows: desc.append("שפלים עולים")
        if compression: desc.append(f"{contractions} כיווצים עוקבים")
        if std_declining: desc.append("סטיית תקן יורדת")
        if not desc:
            desc = ["לא נמצאו סימני VCP ברורים"]
        return {"match": bool(match), "desc": "; ".join(desc), "contractions": contractions}
    except Exception:
        return {"match": False, "desc": "שגיאה בזיהוי תבנית", "contractions": 0}

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
        return BUY_COLOR
    if score >= 55:
        return ACCENT
    return SELL_COLOR

def score_badge_html(score):
    color = score_color(score)
    return f'<span class="score-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{score}</span>'

def ai_gauge_html(score):
    """טבעת ניקוד AI עגולה (conic-gradient) בסגנון SwingAI - ללא תלות בספריית גרפים חיצונית."""
    color = score_color(score)
    return f"""
    <div class="ai-gauge" style="background: conic-gradient({color} {score * 3.6}deg, {BORDER} 0deg);">
        <div class="ai-gauge-inner">
            <span class="score" style="color:{color};">{score}</span>
            <span class="lbl">AI</span>
        </div>
    </div>"""

def score_ring_big_html(score):
    """טבעת ציון גדולה ונקייה (בלי תווית 'AI') - מתאימה לכרטיס המעודכן בהשראת האפליקציה שהוצגה."""
    color = score_color(score)
    return f"""
    <div class="score-ring-big" style="background: conic-gradient({color} {score * 3.6}deg, {BORDER} 0deg);">
        <div class="score-ring-big-inner">
            <span class="score" style="color:{color};">{score}</span>
        </div>
    </div>"""

def sparkline_svg(values, color, width=280, height=44):
    """
    ספארקליין קליל מבוסס SVG טהור (בלי Plotly) - עלות רינדור זניחה גם בפיד עם עשרות כרטיסים.
    מקבל רשימת מספרים (למשל 20 מחירי סגירה אחרונים) ומצייר קו פוליליין מנורמל.
    """
    vals = [v for v in values if not is_bad(v)]
    if len(vals) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pad = 3
    points = []
    for i, v in enumerate(vals):
        x = pad + (i / (n - 1)) * (width - 2 * pad)
        y = pad + (1 - (v - lo) / rng) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(points)
    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
        <polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.2"
                  stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

def fmt_compact_number(v):
    """פורמט קומפקטי למספרים גדולים (וולום וכו') - 4300000 -> '4.3M'."""
    try:
        v = float(v)
    except Exception:
        return "—"
    if is_bad(v):
        return "—"
    if abs(v) >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:.0f}"

def classify_signal(score):
    """מסווג ציון לתגית קנייה/מכירה/המתן + רמת עוצמה, לתצוגת הכרטיס."""
    if score >= 70:
        return "buy", "קנייה", ("גבוהה" if score >= 85 else "בינונית")
    if score <= 35:
        return "sell", "הימנעות", "גבוהה"
    return "neutral", "המתן", "נמוכה"

def compute_trade_levels(df_tail):
    """
    מחשב הערכת כניסה/סטופ/יעד/יחס סיכוי-סיכון להצגה בכרטיס.
    ⚠️ זוהי הערכה טכנית גסה (מבוססת ATR + שפל אחרון), לא המלצת מסחר.
    """
    try:
        entry = float(safe_last(df_tail["Close"]))
        atr = float(safe_last(df_tail["ATR"])) if "ATR" in df_tail.columns else np.nan
        recent_low = float(df_tail["Low"].tail(10).min())
        if is_bad(atr) or atr <= 0:
            stop = recent_low
        else:
            stop = min(recent_low, entry - 1.5 * atr)
        risk = entry - stop
        if is_bad(risk) or risk <= 0:
            return None
        target = entry + risk * 2.0
        rr = round((target - entry) / risk, 1)
        return {"entry": entry, "stop": stop, "target": target, "rr": rr}
    except Exception:
        return None

def render_stock_card(ticker, res, df_tail):
    """
    מציג כרטיס מניה מעודכן: ספארקליין, מחיר + שינוי יומי, טבעת ציון גדולה,
    שורת סטטיסטיקות (וולום/ADX/MFI/RVOL/שיא 52 שבועות), הערות מנוע ההחלטה,
    ורמות כניסה/סטופ/יעד/R:R. בהשראת עיצוב אפליקציית סורק מניות רפרנס.
    """
    score = res.get("score", 0)
    sig_class, sig_label, strength_label = classify_signal(score)
    tag_class = f"tag-{sig_class}"

    notes_list = [n.strip() for n in res.get("note", "").split(",") if n.strip()]
    notes_html = "".join(f"<div>• {n}</div>" for n in notes_list[:4])

    # --- נתוני מחיר/שינוי/ספארקליין מתוך df_tail (אם קיים) ---
    price_html, chg_html, spark_html, stat_row_html = "", "", "", ""
    if df_tail is not None and not df_tail.empty:
        last_price = safe_last(df_tail["Close"])
        chg_pct = safe_last(df_tail["DailyChangePct"]) if "DailyChangePct" in df_tail.columns else np.nan
        spark_vals = df_tail["Close"].tail(20).tolist()
        spark_color = BUY_COLOR if (not is_bad(chg_pct) and chg_pct >= 0) or (
            len(spark_vals) >= 2 and spark_vals[-1] >= spark_vals[0]) else SELL_COLOR
        spark_html = f'<div class="sparkline-wrap">{sparkline_svg(spark_vals, spark_color)}</div>'

        if not is_bad(last_price):
            price_html = f'<span class="stock-card-v2-price">${last_price:,.2f}</span>'
        if not is_bad(chg_pct):
            c_color = BUY_COLOR if chg_pct >= 0 else SELL_COLOR
            arrow = "▲" if chg_pct >= 0 else "▼"
            chg_html = f'<span class="stock-card-v2-chg" style="color:{c_color};">{arrow} {abs(chg_pct):.2f}%</span>'

        vol_last = safe_last(df_tail["Volume"]) if "Volume" in df_tail.columns else np.nan
        adx_last = safe_last(df_tail["ADX"]) if "ADX" in df_tail.columns else np.nan
        mfi_last = safe_last(df_tail["MFI"]) if "MFI" in df_tail.columns else np.nan
        rvol_last = safe_last(df_tail["RVOL"]) if "RVOL" in df_tail.columns else np.nan
        high52_last = safe_last(df_tail["High52W"]) if "High52W" in df_tail.columns else np.nan

        stat_row_html = f"""
        <div class="stat-row-v2">
            <div class="item"><div class="lbl">ווליום</div><div class="val">{fmt_compact_number(vol_last)}</div></div>
            <div class="item"><div class="lbl">ADX</div><div class="val">{f'{adx_last:.0f}' if not is_bad(adx_last) else '—'}</div></div>
            <div class="item"><div class="lbl">MFI</div><div class="val">{f'{mfi_last:.0f}' if not is_bad(mfi_last) else '—'}</div></div>
            <div class="item"><div class="lbl">RVOL</div><div class="val">{f'{rvol_last:.2f}x' if not is_bad(rvol_last) else '—'}</div></div>
            <div class="item"><div class="lbl">שיא 52ש'</div><div class="val">{f'${high52_last:,.1f}' if not is_bad(high52_last) else '—'}</div></div>
        </div>"""

    levels = compute_trade_levels(df_tail) if (df_tail is not None and not df_tail.empty) else None
    trade_html = ""
    if levels:
        trade_html = f"""
        <div class="stat-grid" style="margin-top:8px;">
            <div class="stat-box"><div class="lbl">כניסה</div><div class="val">${levels['entry']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">סטופ</div><div class="val" style="color:{SELL_COLOR};">${levels['stop']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">יעד</div><div class="val" style="color:{BUY_COLOR};">${levels['target']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">R/R</div><div class="val" style="color:{ACCENT};">1:{levels['rr']}</div></div>
        </div>"""

    card_html = f"""
    <div class="stock-card-v2">
        <div class="stock-card-v2-top">
            <div style="flex:1; min-width:0;">
                <span class="stock-card-v2-ticker">{ticker}</span>
                <div style="margin-top:4px;">
                    <span class="tag {tag_class}">{sig_label}</span>
                    <span class="tag tag-strength">עוצמה: {strength_label}</span>
                </div>
                {spark_html}
                <div>{price_html}{chg_html}</div>
            </div>
            {score_ring_big_html(score)}
        </div>
        {stat_row_html}
        <div class="stock-note">{notes_html if notes_html else "אין אותות חזקים"}</div>
        {trade_html}
    </div>"""
    st.markdown(card_html, unsafe_allow_html=True)

def render_top_stat_cards(df_res, details):
    """
    שורת 4 כרטיסי סיכום עליונים (בהשראת עיצוב הרפרנס): עולות/יורדות/פריצה חזקה/ציון ממוצע.
    'עולות'/'יורדות' נספרים לפי השינוי היומי האחרון של כל טיקר (מתוך df_tail בפירוט הסריקה).
    """
    rising = falling = 0
    for t in df_res["Ticker"]:
        info = details.get(t)
        if not info or info["df_tail"].empty or "DailyChangePct" not in info["df_tail"].columns:
            continue
        chg = safe_last(info["df_tail"]["DailyChangePct"])
        if is_bad(chg):
            continue
        if chg >= 0:
            rising += 1
        else:
            falling += 1

    strong_breakout = int((df_res["Score"] >= 85).sum())
    avg_score = round(df_res["Score"].mean(), 0) if not df_res.empty else 0

    st.markdown(f"""
    <div class="top-stat-row">
        <div class="top-stat-card" style="background:rgba(34,197,94,0.10); border-color:rgba(34,197,94,0.30);">
            <div class="icon">📈</div>
            <div class="num" style="color:{BUY_COLOR};">{rising}</div>
            <div class="lbl">עולות</div>
        </div>
        <div class="top-stat-card" style="background:rgba(239,68,68,0.10); border-color:rgba(239,68,68,0.30);">
            <div class="icon">📉</div>
            <div class="num" style="color:{SELL_COLOR};">{falling}</div>
            <div class="lbl">יורדות</div>
        </div>
        <div class="top-stat-card" style="background:rgba(242,169,59,0.10); border-color:rgba(242,169,59,0.30);">
            <div class="icon">🚀</div>
            <div class="num" style="color:{ACCENT};">{strong_breakout}</div>
            <div class="lbl">פריצה חזקה</div>
        </div>
        <div class="top-stat-card" style="background:rgba(108,140,255,0.10); border-color:rgba(108,140,255,0.30);">
            <div class="icon">✨</div>
            <div class="num" style="color:#6c8cff;">{avg_score:.0f}</div>
            <div class="lbl">ציון ממוצע</div>
        </div>
    </div>""", unsafe_allow_html=True)

def generate_rule_based_explanation(ticker, res):
    """
    הסבר מורחב וטבעי בעברית, מבוסס אך ורק על לוגיקת מנוע ההחלטה הקיים
    (compute_breakout_decision) - ללא קריאה לשום API חיצוני בתשלום.
    ממיר את רכיבי הניקוד הגולמיים למשפטים קריאים שמסבירים "למה" המניה קיבלה
    את הציון שקיבלה, כולל הרכיבים החזקים, החלשים, ואזהרות וטו אם הופעלו.
    """
    comps = res.get("components", {})
    score = res.get("score", 0)
    confidence = res.get("confidence", 0)

    comp_meta = {
        "compression": ("דחיסת מחיר (Squeeze)", "המניה נמצאת בתקופת תנודתיות נמוכה יחסית להיסטוריה שלה - "
                        "מצב שלעיתים קרובות מקדים תנועה חדה, כי האנרגיה 'נאגרת' לפני פריצה."),
        "rvol": ("נפח יחסי (RVOL)", "הנפח האחרון ביחס לממוצע 20 היום - נפח גבוה מרמז על עניין מוגבר בשוק."),
        "trend": ("טרנד קצר טווח (EMA20/50)", "היחס בין הממוצע הנע ל-20 יום לממוצע ל-50 יום - EMA20 מעל EMA50 מרמז על מומנטום חיובי קצר-טווח."),
        "macd": ("MACD", "ההפרש בין קו ה-MACD לקו האיתות שלו - ערך חיובי וגדל מרמז על תאוצה חיובית במחיר."),
        "rsi": ("RSI", "מדד המומנטום הקלאסי - נבדק שהוא בטווח בריא (לא overbought/oversold קיצוני)."),
        "institutional": ("כסף מוסדי (OBV/AD)", "האם צבירת הנפח (OBV) וקו ההצטברות/חלוקה (AD) עולים ב-10 הימים האחרונים - סימן לכניסת כסף גדול."),
        "proximity": ("קרבה להתנגדות ישנה", "המרחק בין המחיר הנוכחי לרמת ההתנגדות שנוצרה *לפני* הריצה האחרונה - "
                      "ככל שהמחיר קרוב יותר מלמטה, כך הפוטנציאל ל'קדם-פריצה' אמיתי גבוה יותר."),
        "squeeze": ("Squeeze פעיל", "רצועות בולינגר בתוך ערוצי Keltner כרגע - איתות כיווץ תנודתיות קלאסי."),
        "squeeze_duration": ("משך ה-Squeeze", "כמה ימים רצופים המניה נמצאת במצב כיווץ - כיווץ ממושך יותר נוטה להוליד תנועה חדה יותר כשהוא נשבר."),
        "risk": ("ניקוד סיכון", "התנודתיות (ATR) כאחוז מהמחיר - ציון גבוה כאן = תנודתיות נמוכה יחסית = סיכון מחושב נמוך יותר."),
        "stage2": ("מגמת-על (Stage 2)", "לפי שיטת Weinstein/Minervini: מחיר מעל SMA150 שמעל SMA200 עולה = מגמת-על בריאה תומכת."),
        "relative_strength": ("חוזק יחסי מול SPY", "האם המניה השתפרה ביחס למדד S&P 500 ב-20 הימים האחרונים - חוזק יחסי הוא סימן מוביל חשוב."),
        "volume_quality": ("איכות נפח", "היחס בין נפח בימי עלייה לנפח בימי ירידה - יחס גבוה מרמז שהקונים דומיננטיים יותר מהמוכרים."),
        "extension": ("התרחקות מהממוצע (Extension)", "כמה יחידות ATR המחיר רחוק מ-EMA20 - מחיר קרוב לממוצע (לא 'מורחק') מעדיף כי זה מרמז שהתנועה עוד לא קרתה."),
        "absorption": ("איסוף שקט (Wyckoff Absorption)", "האם בימי ירידה המחיר נסגר קרוב לשיא הטווח היומי - סימן שקונים סופגים היצע בזמן חולשה, איתות איסוף קלאסי לפי וייקוף."),
        "sideways": ("תנועה הצידה (טווח אמיתי)", "שיפוע ה-EMA50 קרוב לאפס - מרמז על טווח מסחר אמיתי (לא טרנד תלול), הקרקע הקלאסית לבניית בסיס."),
    }

    strong = sorted([(k, v) for k, v in comps.items() if v >= 70], key=lambda x: -x[1])
    weak = sorted([(k, v) for k, v in comps.items() if v <= 30], key=lambda x: x[1])

    lines = []
    verdict = "חיובית מאוד" if score >= 80 else "חיובית" if score >= 65 else "מעורבת" if score >= 45 else "חלשה"
    lines.append(f"**סיכום כללי:** {ticker} קיבלה ציון **{score}/100** (רמת ביטחון {confidence}%), תמונה כללית {verdict}.")

    if strong:
        lines.append("\n**מה תומך בציון הגבוה:**")
        for k, v in strong[:6]:
            name, desc = comp_meta.get(k, (k, ""))
            lines.append(f"- **{name}** (ניקוד {v}/100): {desc}")

    if weak:
        lines.append("\n**מה מחליש את התמונה:**")
        for k, v in weak[:5]:
            name, desc = comp_meta.get(k, (k, ""))
            lines.append(f"- **{name}** (ניקוד {v}/100): {desc}")

    if res.get("hard_downtrend"):
        lines.append("\n⚠️ **וטו קשיח הופעל — מגמת-על יורדת:** המחיר מתחת ל-SMA200 שגם הוא יורד. "
                     "זהו סימן למגמת-על שבורה, ולכן הציון הסופי הוגבל (עוטה תקרה נמוכה) גם אם רכיבים אחרים חיוביים.")
    if res.get("already_broken_out"):
        dsb = res.get("days_since_breakout")
        extra = f" (לפני כ-{dsb} ימי מסחר)" if dsb is not None else ""
        lines.append(f"\n⚠️ **וטו קשיח הופעל — נראה שהמניה כבר פרצה{extra}:** זו כבר לא תבנית 'קדם-פריצה' טהורה - "
                     "המחיר כבר רחוק מדי מהבסיס/מהממוצעים, אז הציון הוגבל בהתאם כדי לא להטעות.")

    if not strong and not weak:
        lines.append("\nלא נמצאו רכיבים קיצוניים (לא חזקים ולא חלשים באופן מובהק) - תמונה ניטרלית למדי ברוב הפרמטרים.")

    lines.append("\n_הסבר זה נוצר אוטומטית מתוך ערכי הרכיבים של מנוע ההחלטה בלבד (ללא AI חיצוני/בתשלום), "
                  "ואינו מהווה ייעוץ השקעות._")
    return "\n".join(lines)

def render_stat_pills(df_res):
    """שורת פילים סטטיסטית מעל הפיד (קנייה/מכירה/סה"כ), בסגנון SwingAI."""
    buy_count = int((df_res["Score"] >= 70).sum())
    sell_count = int((df_res["Score"] <= 35).sum())
    total = len(df_res)
    st.markdown(f"""
    <div class="stat-pill-row">
        <div class="stat-pill"><div class="num" style="color:{BUY_COLOR};">{buy_count}</div><div class="lbl">קנייה</div></div>
        <div class="stat-pill"><div class="num" style="color:{SELL_COLOR};">{sell_count}</div><div class="lbl">הימנעות</div></div>
        <div class="stat-pill"><div class="num" style="color:{ACCENT};">{total}</div><div class="lbl">איתותים</div></div>
    </div>""", unsafe_allow_html=True)

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

render_market_ticker()
render_fear_greed_gauge()

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

    with st.sidebar.expander("🎯 סינון ציון בסיסי", expanded=True):
        score_range = st.slider(
            "טווח ציון להצגה:", 0, 100, (60, 100),
            help="רק מניות עם ציון בטווח הזה יוצגו בתוצאות. הגבל את המקסימום כדי לסנן ציונים 'חשודים' גבוהים מדי, "
                 "או צמצם את המינימום כדי לראות גם מועמדים חלשים יותר."
        )
        min_score, max_score = score_range

        min_confidence = st.slider(
            "ביטחון מינימלי (%):", 0, 100, 0,
            help="אחוז הרכיבים בציון שהגיעו לרף 'חזק' (70+). מסנן איתותים עם ציון גבוה אך נתמכים ברכיב יחיד בלבד."
        )

    with st.sidebar.expander("🧪 סינוני איכות מתקדמים", expanded=False):
        exclude_broken_out = st.checkbox(
            "הסתר מניות שכבר פרצו (already broken out)", value=True,
            help="מסנן מניות שקיבלו את דגל הוטו 'כבר פרצה משמעותית' — למניעת False positives כמו CCO."
        )
        exclude_downtrend = st.checkbox(
            "הסתר מגמת-על יורדת (SMA200 יורד)", value=True,
            help="מסנן מניות עם מגמת-על שבורה (מתחת ל-SMA200 יורד) - סיכון גבוה גם אם רכיבים אחרים נראים טוב."
        )
        require_stage2 = st.checkbox(
            "דרוש Stage 2 מלא (Weinstein/Minervini)", value=False,
            help="מציג רק מניות שנמצאות במגמת-על בריאה מלאה: Close > SMA150 > SMA200 עולה."
        )
        rsi_range = st.slider(
            "טווח RSI:", 0, 100, (0, 100),
            help="סנן לפי RSI הנוכחי - לדוגמה 40-70 כדי להימנע ממניות overbought/oversold קיצוניות."
        )
        rvol_min = st.number_input(
            "נפח יחסי מינימלי (RVOL):", min_value=0.0, max_value=10.0, value=0.0, step=0.1,
            help="דורש שהנפח האחרון יהיה לפחות פי X מהממוצע ל-20 יום. 0 = ללא סינון."
        )
        atr_pct_range = st.slider(
            "טווח תנודתיות (ATR% מהמחיר):", 0.0, 15.0, (0.0, 15.0), step=0.5,
            help="מסנן מניות תנודתיות מדי (סיכון גבוה) או שקטות מדי (חסרות פוטנציאל תנועה)."
        )
        price_range = st.slider(
            "טווח מחיר ($):", 0, 1000, (0, 1000), step=5,
            help="הגבל לפי טווח מחיר המניה - לדוגמה כדי להימנע מ-penny stocks או ממניות יקרות מדי."
        )

    with st.sidebar.expander("⚙️ הגדרות סריקה", expanded=False):
        max_tickers = st.number_input("מקסימום טיקרים לסריקה:", min_value=10, max_value=1000, value=200, step=10)
        min_dollar_vol = st.number_input(
            "מינימום מחזור מסחר יומי ($):", min_value=0, max_value=100_000_000,
            value=2_000_000, step=500_000,
            help="מניות עם מחזור מסחר דולרי (מחיר × נפח ממוצע) נמוך מהסף יסוננו — נמנע מנזילות דלה שמעוותת אותות."
        )
        if st.button("🗑️ נקה מטמון (מחירים + SEC + CIK)", use_container_width=True):
            load_history.clear()
            load_benchmark.clear()
            load_market_indices.clear()
            load_sec_ticker_cik_map.clear()
            fetch_insider_transactions.clear()
            fetch_fear_greed_index.clear()
            fetch_stock_news.clear()
            fetch_analyst_data.clear()
            st.success("המטמון נוקה — הריצה הבאה תביא נתונים עדכניים")

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
            skipped_liquidity = []

            benchmark_df = load_benchmark(period="12mo")

            for i, ticker in enumerate(tickers):
                progress.progress((i + 1) / total, text=f"בודק {ticker} ({i+1}/{total})")
                try:
                    df = load_history(ticker, period="12mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                         "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        continue

                    # --- סינון נזילות: מחזור מסחר דולרי ממוצע מתחת לסף לא ייכלל בתוצאות ---
                    avg_vol_20 = df["Volume"].tail(20).mean()
                    last_price_raw = safe_last(df["Close"])
                    dollar_vol = (avg_vol_20 * last_price_raw) if not is_bad(last_price_raw) else 0
                    if min_dollar_vol > 0 and dollar_vol < min_dollar_vol:
                        skipped_liquidity.append(ticker)
                        continue

                    # --- סינון טווח מחיר מוקדם, לפני חישוב אינדיקטורים כבד ---
                    if not is_bad(last_price_raw) and not (price_range[0] <= last_price_raw <= price_range[1]):
                        continue

                    df = add_indicators(df, benchmark_df=benchmark_df)
                    res = compute_breakout_decision(df)

                    # --- סינוני איכות נוספים על תוצאת המנוע ---
                    if exclude_broken_out and res.get("already_broken_out"):
                        continue
                    if exclude_downtrend and res.get("hard_downtrend"):
                        continue
                    if require_stage2 and not res.get("stage2_ok"):
                        continue
                    rsi_last = res.get("rsi_last")
                    if not is_bad(rsi_last) and not (rsi_range[0] <= rsi_last <= rsi_range[1]):
                        continue
                    rvol_last = res.get("rvol_last")
                    if rvol_min > 0 and (is_bad(rvol_last) or rvol_last < rvol_min):
                        continue
                    atr_pct_last = res.get("atr_pct")
                    atr_pct_display = atr_pct_last * 100 if not is_bad(atr_pct_last) else np.nan
                    if not is_bad(atr_pct_display) and not (atr_pct_range[0] <= atr_pct_display <= atr_pct_range[1]):
                        continue
                    if res["confidence"] < min_confidence:
                        continue

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
            if skipped_liquidity:
                st.caption(f"💧 {len(skipped_liquidity)} טיקרים סוננו בשל נזילות נמוכה מהסף שהוגדר: "
                            f"{', '.join(skipped_liquidity[:15])}{' ...' if len(skipped_liquidity) > 15 else ''}")
            if errors:
                with st.expander(f"⚠️ {len(errors)} טיקרים נכשלו בסריקה — לחץ לפרטים"):
                    for e in errors:
                        st.caption(e)

            st.session_state["scan_results"] = results
            st.session_state["scan_details"] = details
            # שומרים את סף הציון האחרון בשימוש כדי שתצוגת session_state הישנה תישאר עקבית אחרי ריענון
            st.session_state["last_min_score"] = min_score
            st.session_state["last_max_score"] = max_score

    # --- הצגת תוצאות אחרונות (נשמר ב-session_state כדי לשרוד ריענונים) ---
    if "scan_results" in st.session_state and st.session_sta

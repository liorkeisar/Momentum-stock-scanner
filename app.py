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

ACCENT = "#00e08f"      # ירוק מנטה — צבע אקסנט ראשי
ACCENT_DARK = "#00c47d"
BG = "#0b0f17"          # רקע ראשי כהה
PANEL = "#12161f"       # רקע כרטיסים/פאנלים
PANEL_ALT = "#171c28"   # רקע שדות קלט
BORDER = "#242a38"      # גבולות עדינים
TEXT_MUTED = "#8891a5"

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
        background: rgba(0,224,143,0.10);
        border: 1px solid rgba(0,224,143,0.35);
        color: {ACCENT};
        padding: 7px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 13px;
        white-space: nowrap;
    }}

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

# ============================
# איתור קניות/מכירות Insider — SEC EDGAR (Form 4)
# ============================
# זהו המקור הכי "חד משמעי" שאפשר לשלב בחינם: Form 4 הוא גילוי רגולטורי מחייב
# (SEC) על כל עסקת קנייה/מכירה של דירקטורים ומנהלים בכירים, מוגש תוך יומיים
# עסקים. זה לא "מוסדי" במובן של קרנות גדולות (לזה יש 13F/13D, ברבעון/בפיגור),
# אבל זו העסקה הכי קרובה ל"מישהו בפנים קונה במזומן משלו" שיש בציבור.
#
# ⚠️ הערה חשובה: SEC דורשת User-Agent מזוהה עם פרטי קשר אמיתיים (מדיניות
# Fair Access). יש לעדכן את הכתובת למטה לכתובת מייל אמיתית שלך לפני שימוש
# מסחרי/תכוף, אחרת הבקשות עלולות להיחסם.
SEC_USER_AGENT = "WyckoffProScanner/1.0 (contact: your-email@example.com)"

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
    # תוקן באג: שימוש בשיא 20 יום גולמי ("High20") גורם למניה שכבר פרצה
    # להראות תמיד "קרובה לשיא" כי החלון הנע פשוט רודף אחרי המחיר החדש.
    # כאן משתמשים בשיא של חלון ישן יותר (BASE_WINDOW) שמוזז אחורה (RECENT_EXCLUDE)
    # כדי לשקף את רמת ההתנגדות שנוצרה *לפני* תנועת המחיר האחרונה.
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
    # תוקן באג: קודם נעשה שימוש בשיא 20 יום גולמי, שגורם למניה שכבר פרצה להראות
    # תמיד "בדיוק בשיא" (כי המחיר עצמו קובע את השיא של החלון הנע). כעת ההשוואה היא
    # מול רמת ההתנגדות שנוצרה *לפני* התנועה האחרונה - ציון שיא רק כשקרובים אליה
    # מלמטה, וקנס הולך וגדל ככל שכבר התרחקנו ממנה כלפי מעלה (כלומר כבר פרצנו).
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
    # זו כבר לא "קדם-פריצה", היא פריצה שכבר קרתה. זה הבאג הספציפי שדווח (למשל CCO).
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
    min_dollar_vol = st.sidebar.number_input(
        "מינימום מחזור מסחר יומי ($):", min_value=0, max_value=100_000_000,
        value=2_000_000, step=500_000,
        help="מניות עם מחזור מסחר דולרי (מחיר × נפח ממוצע) נמוך מהסף יסוננו — נמנע מנזילות דלה שמעוותת אותות."
    )

    if st.sidebar.button("🗑️ נקה מטמון מחירים (רענון נתונים)"):
        load_history.clear()
        load_benchmark.clear()
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

                    df = add_indicators(df, benchmark_df=benchmark_df)
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
            if skipped_liquidity:
                st.caption(f"💧 {len(skipped_liquidity)} טיקרים סוננו בשל נזילות נמוכה מהסף שהוגדר: "
                            f"{', '.join(skipped_liquidity[:15])}{' ...' if len(skipped_liquidity) > 15 else ''}")
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
                    comp_labels = {
                        "compression": "דחיסת מחיר (Squeeze)",
                        "rvol": "נפח יחסי (RVOL)",
                        "trend": "טרנד EMA20/50",
                        "macd": "MACD",
                        "rsi": "RSI",
                        "institutional": "כסף מוסדי (OBV/AD)",
                        "proximity": "קרבה להתנגדות ישנה (לפני הריצה)",
                        "squeeze": "Squeeze פעיל כרגע",
                        "squeeze_duration": "משך ה-Squeeze",
                        "risk": "ניקוד סיכון (נמוך=טוב)",
                        "stage2": "מגמת-על (Stage 2)",
                        "relative_strength": "חוזק יחסי מול SPY",
                        "volume_quality": "איכות נפח (קונים/מוכרים)",
                        "extension": "התרחקות מהממוצע (Extension)",
                        "absorption": "איסוף בזמן ירידה (Wyckoff Absorption)",
                        "sideways": "תנועה הצידה (טווח, לא טרנד)",
                    }
                    comps_named = {comp_labels.get(k, k): v for k, v in res["components"].items()}
                    comp_df = pd.DataFrame.from_dict(comps_named, orient="index", columns=["ערך"]).sort_values("ערך", ascending=False)
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
                                bench_full = load_benchmark(period="24mo")
                                hist_full = add_indicators(hist_full, benchmark_df=bench_full)
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

                # ---------- Backtest לכיול הציון ----------
                st.markdown("---")
                st.markdown("### 🧪 Backtest — האם הציון באמת עובד?")
                st.caption("בודק היסטורית: כשהמניה קיבלה ציון מסוים, כמה פעמים היא באמת פרצה תוך כמה ימים. "
                           "עוזר לכייל את 'ציון מינימלי להצגה' בסיידבר לספי ציון שבאמת מתאמים להצלחה.")
                bt_col1, bt_col2 = st.columns([3, 1])
                with bt_col1:
                    bt_lookahead = st.select_slider("חלון בדיקת פריצה (ימים):", options=[3, 5, 7, 10], value=5, key=f"bt_look_{to_view}")
                with bt_col2:
                    st.write("")
                    run_bt = st.button("הרץ Backtest", key=f"bt_btn_{to_view}", use_container_width=True)

                if run_bt:
                    with st.spinner("מריץ Backtest היסטורי... (עשוי לקחת כמה שניות)"):
                        bt_hist = load_history(to_view, period="5y")
                        if bt_hist.empty or len(bt_hist) < 300:
                            st.warning("אין מספיק היסטוריה (נדרשים לפחות ~300 ימי מסחר) להרצת Backtest אמין.")
                        else:
                            bt_bench = load_benchmark(period="5y")
                            bt_hist_full = add_indicators(bt_hist, benchmark_df=bt_bench)
                            summary, raw_bt = backtest_score_calibration(bt_hist_full, lookahead=bt_lookahead, step=3)
                            if summary is None or summary.empty:
                                st.warning("לא הצלחנו להריץ Backtest עבור טיקר זה (ייתכן חוסר בנתונים).")
                            else:
                                st.dataframe(
                                    summary, use_container_width=True, hide_index=True,
                                    column_config={
                                        "שיעור_הצלחה": st.column_config.ProgressColumn("שיעור הצלחה (%)", min_value=0, max_value=100, format="%.1f%%"),
                                        "מקרים": st.column_config.NumberColumn("מס' מקרים היסטוריים"),
                                    }
                                )
                                overall_rate = round(raw_bt["outcome"].mean() * 100, 1)
                                st.caption(f"שיעור פריצה כללי (בסיס להשוואה, ללא תלות בציון): **{overall_rate}%** "
                                           f"מתוך {len(raw_bt)} נקודות היסטוריות שנבדקו.")
                                st.info("💡 אם שיעור ההצלחה בדליים הגבוהים (70+) גבוה משמעותית מהשיעור הכללי — "
                                        "סימן שהציון אכן מוסיף ערך חיזוי עבור המניה הזו.")

                # ---------- אימות Insider Buying (SEC EDGAR) ----------
                st.markdown("---")
                st.markdown("### 🕵️ אימות קניות/מכירות Insider (SEC EDGAR)")
                st.caption("Form 4 הוא גילוי רגולטורי מחייב על עסקאות דירקטורים/מנהלים בכירים - "
                           "האות הכי 'חד משמעי' שאפשר לקבל בחינם על מישהו שקונה בכסף אמיתי משלו. "
                           "לא מבוצע אוטומטית בסריקה (כדי לא להעמיס על שרתי SEC) - רק לפי דרישה כאן.")
                run_insider = st.button("בדוק עסקאות Insider ב-90 הימים האחרונים", key=f"insider_btn_{to_view}")

                if run_insider:
                    with st.spinner("שולף נתונים מ-SEC EDGAR..."):
                        ins = fetch_insider_transactions(to_view, lookback_days=90, max_filings=15)

                    if ins.get("error"):
                        st.warning(f"⚠️ {ins['error']}")
                    elif ins["buys"] == 0 and ins["sells"] == 0:
                        st.info("לא נמצאו עסקאות Insider בשוק הפתוח ב-90 הימים האחרונים עבור טיקר זה.")
                    else:
                        ic1, ic2, ic3 = st.columns(3)
                        ic1.metric("קניות Insider", ins["buys"], f"${ins['buy_value']:,.0f}")
                        ic2.metric("מכירות Insider", ins["sells"], f"${ins['sell_value']:,.0f}")
                        net = ins["buy_value"] - ins["sell_value"]
                        ic3.metric("נטו (קנייה מינוס מכירה)", f"${net:,.0f}")

                        if ins["buys"] > 0 and ins["buy_value"] > ins["sell_value"]:
                            st.success("✅ קנייה נטו ע\"י אנשי פנים ב-90 הימים האחרונים — אישוש חיובי לתזה.")
                        elif ins["sells"] > ins["buys"] * 2:
                            st.caption("ℹ️ יש יותר מכירות מקניות - שים לב שמכירות insider הן לרוב שגרתיות "
                                       "(תוכניות 10b5-1, מימוש אופציות) ולא בהכרח סימן שלילי, בניגוד לקנייה "
                                       "בשוק הפתוח שהיא כמעט תמיד יזומה ומכוונת.")

                        tx_df = pd.DataFrame(ins["transactions"]).sort_values("date", ascending=False)
                        st.dataframe(
                            tx_df, use_container_width=True, hide_index=True,
                            column_config={
                                "date": "תאריך", "owner": "שם", "role": "תפקיד", "type": "סוג עסקה",
                                "shares": st.column_config.NumberColumn("מניות", format="%d"),
                                "value": st.column_config.NumberColumn("שווי ($)", format="$%.0f"),
                            }
                        )

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

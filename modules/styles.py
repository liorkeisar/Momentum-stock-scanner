"""
modules/styles.py
Wyckoff Pro Swing Scanner

קבועי צבע (ACCENT/PANEL/BORDER וכו') + כל הפונקציות שמרנדרות את ה-CSS הגלובלי,
כותרת העליון (header) ובאנר האזהרה. אלה נשארים כאן בנפרד מ-app.py כדי שכל שינוי
עיצובי (למשל צבע חדש, טעינת theme) יהיה במקום אחד בלי לגעת בלוגיקה של הטאבים.
"""
import streamlit as st

# ---------------------------------------------------------------
# פלטת צבעים
# ---------------------------------------------------------------
ACCENT = "#f2a93b"      # כתום-ענבר — צבע אקסנט ראשי (בהשראת עיצוב SwingAI)
ACCENT_DARK = "#d98f1f"
BG = "#0b0f17"          # רקע ראשי כהה
PANEL = "#12161f"       # רקע כרטיסים/פאנלים
PANEL_ALT = "#171c28"   # רקע שדות קלט
BORDER = "#242a38"      # גבולות עדינים
TEXT_MUTED = "#8891a5"
BUY_COLOR = "#22c55e"   # ירוק - קנייה
SELL_COLOR = "#ef4444"  # אדום - מכירה


def configure_page():
    """קריאה יחידה שחייבת לרוץ ראשונה בסקריפט (st.set_page_config)."""
    st.set_page_config(page_title="Wyckoff Pro — Swing Scanner", layout="wide", page_icon="◈")


def render_css():
    """מזריק את כל ה-CSS הגלובלי של האפליקציה (עיצוב כהה, כרטיסים, טאבים וכו')."""
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


def render_header():
    """מרנדר את כותרת העליון (לוגו + כותרת + סטטוס צ'יפ)."""
    st.markdown(f"""
    <div class="app-header">
        <div>
            <div class="title">◈ Wyckoff Pro <span class="accent">Swing Scanner</span></div>
            <div class="subtitle">סורק פריצה מבוסס וייקוף · אינדיקטורים טכניים · חיזוי סטטיסטי</div>
        </div>
        <div class="status-chip">⚡ כלי תמיכה בהחלטה</div>
    </div>
    """, unsafe_allow_html=True)


def render_banner():
    """מרנדר את באנר האזהרה הגלובלי ('כלי תמיכה בהחלטה בלבד')."""
    st.markdown(
        '<div class="top-banner">⚠️ כלי תמיכה בהחלטה בלבד — אינו מהווה ייעוץ השקעות. '
        'כל החלטת מסחר היא באחריות המשתמש בלבד.</div>',
        unsafe_allow_html=True
    )

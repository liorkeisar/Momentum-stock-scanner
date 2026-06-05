import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

st.set_page_config(layout="wide", page_title="Quantum Terminal TITAN", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.4rem; font-weight: 800; background: linear-gradient(90deg, #FCA311, #00B887); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 25px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: transparent; border-bottom: 1px solid #1E1833; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { background-color: #120E22; border-radius: 8px 8px 0 0; color: #938AA9; padding: 6px 12px; border: 1px solid #1E1833; border-bottom: none; font-size: 0.8rem; }
    .stTabs [aria-selected="true"] { background-color: #1A1530 !important; color: #FCA311 !important; border-color: #FCA311 !important; font-weight: 600; }
    
    .metric-card { background: #111522; border: 1px solid #1F2538; border-radius: 10px; padding: 12px; text-align: center; }
    .metric-label { font-size: 0.75rem; color: #7E7497; font-weight: 500; margin-bottom: 4px; display: block; }
    .metric-value { font-size: 1.25rem; font-weight: 700; color: #FFFFFF; }
    
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 20px; margin-bottom: 25px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 16px; height: 100%; }
    .ticker-symbol { font-size: 2rem; font-weight: 800; color: #FFFFFF; display: block; margin-bottom: 4px; }
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; text-align: center; }
    .badge-accum { background-color: rgba(252, 163, 17, 0.15); color: #FCA311; }
    .badge-search { background-color: rgba(58, 134, 255, 0.15); color: #3A86FF; }
    
    .indicator-box { margin-top: 10px; padding-top: 8px; border-top: 1px solid #1F2538; }
    .indicator-row { display: flex; justify-content: space-between; font-size: 0.8rem; }
    .indicator-name { color: #938AA9; }
    
    .edu-card { background: #131124; border: 1px solid #251F3D; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .edu-title { color: #FCA311; font-size: 1.1rem; font-weight: 700; margin-bottom: 12px; }
    .edu-text { font-size: 0.88rem; color: #B5AEC4; line-height: 1.5; margin-bottom: 10px; }
    
    .stButton>button { background: linear-gradient(180deg, #251F3D, #131124); color: #E6E1F3; border: 1px solid #362E54; border-radius: 12px; padding: 8px 16px; font-weight: 600; width: 100%; }
    .stButton>button:hover { border-color: #FCA311; color: #FCA311; background: #1A1530; }
    
    .whatsapp-btn { background-color: #25D366; color: white !important; font-weight: bold; padding: 10px 20px; text-align: center; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; text-decoration: none; width: 100%; margin-bottom: 20px; border: none; font-size: 0.9rem; }
    .whatsapp-btn:hover { background-color: #128C7E; text-decoration: none; }
    
    .login-box { max-width: 400px; margin: 100px auto; background: #111522; border: 1px solid #1F2538; border-radius: 16px; padding: 30px; text-align: center; }
    
    .portfolio-card { background: #121626; border: 1px solid #232B44; border-radius: 14px; padding: 18px; margin-bottom: 15px; }
    .portfolio-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .portfolio-title { font-size: 1.4rem; font-weight: 800; color: #FFFFFF; }
    .p-positive { color: #00B887; font-weight: 700; }
    .p-negative { color: #FF3A5A; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- מנגנון נעילה קליל (סיסמה לבדיקות) ---
CORRECT_PASSWORD = "titan2026"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#FFFFFF; margin-bottom:20px;">🔒 כניסה למערכת סגורה</h2>', unsafe_allow_html=True)
    password_input = st.text_input("הזן סיסמת גישה:", type="password")
    if st.button("התחבר"):
        if password_input == CORRECT_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("סיסמה שגויה, גישה חסומה.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- הגדרת נתוני התיק האישי שלך ---
# מילון פשוט ומאובטח לעדכון פוזיציות: "סימול": [כמות מניות, מחיר קנייה ממוצע]
MY_PORTFOLIO = {
    "SIRI": [50, 24.50]
}

# --- מאגר נתוני השוק המורחב (500 מניות) ---
MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST", "PEP", "NFLX", "AMD", "ADBE", "AZN", "CSCO", "QCOM", "TMUS", "INTU", "AMAT", "TXN", "AMGN", "ISRG", "HON", "BKNG", "VRTX", "GEHC", "MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "CRWD", "MU", "MELI", "CDNS", "ORLY", "ASML", "CTAS", "AEP", "MAR", "EQIX", "WDAY", "NXPI", "FTNT", "PCAR", "PDD", "MNST", "ADSK"],
    "NASDAQ_B": ["PAYX", "CPRT", "ROST", "KDP", "CHTR", "ANSS", "TEAM", "DDOG", "FAST", "MCHP", "GILD", "EA", "CTSH", "IDXX", "ADI", "BKR", "ON", "EXC", "MRVL", "ABNB", "CEG", "MDB", "VRSK", "CSX", "DXCM", "FFIV", "ILMN", "WBA", "ZBRA", "ALGN", "VRSN", "EBAY", "SIRI", "NTES", "JD", "BIDU", "LCID", "BILI", "OKTA", "SPLK", "FITB", "FANG", "MGM", "SBUX", "WBD", "MKTX", "DLTR", "URI", "EXPE", "KVUE"],
    "SP500_A": ["BRK.B", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY", "WMT", "MCD", "CRM", "BAC", "ACN", "TMO", "LIN", "ORCL", "CMCSA", "ABT", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "LOW", "SCHW", "SPGI", "UNP", "T", "DIS", "INTC", "BMY", "TXN", "RTX", "GE", "AXP", "CAT", "PGR", "C", "GS", "WFC", "BLK", "NOW", "PLTR", "UBER"],
    "SP500_B": ["IBM", "DE", "MMM", "LMT", "SYK", "MDT", "CI", "TJX", "MO", "NOC", "COF", "AMD", "AMAT", "ADI", "LRCX", "KLAC", "MU", "SNPS", "CDNS", "PANW", "FTNT", "EQIX", "PSA", "PLD", "AMT", "CCI", "WY", "SPG", "DLR", "O", "WELL", "AVB", "EQR", "VTR", "BXP", "REG", "MAA", "UDR", "ESS", "PEAK", "DOC", "ARE", "FRT", "ETR", "FE", "AEE", "CMS", "ED", "D", "SO"],
    "SP500_C": ["DUK", "AEP", "EXC", "XEL", "PEG", "WEC", "ES", "DTE", "PPL", "EIX", "ETN", "PH", "EMR", "ROP", "WM", "GEV", "ITW", "NSC", "CSX", "UNP", "FDX", "UPS", "ODFL", "LUV", "DAL", "UAL", "AAL", "MAR", "HLT", "HATT", "EXPE", "BKNG", "NCLH", "RCL", "CCL", "MCD", "YUM", "CMG", "DRI", "DPZ", "SBUX", "TJX", "ROST", "NKE", "TGT", "WMT", "COST", "HD", "LOW", "ORLY"],
    "SP500_D": ["AZO", "GPC", "LKQ", "TSLA", "F", "GM", "HOG", "BWA", "ALV", "MHK", "NVR", "LEN", "DHI", "PHM", "TOL", "MTH", "CCS", "KBH", "GRMN", "HAS", "MAT", "TTWO", "EA", "ATVI", "NFLX", "DIS", "PARA", "WBD", "FOXA", "NWSA", "VZ", "T", "TMUS", "CHTR", "CMCSA", "LUMN", "FYBR", "SBAC", "GOOGL", "META", "PINS", "SNAP", "TTD", "ZG", "MTCH", "IAC", "YELP", "ANGI", "TRIP", "DESP"],
    "MIDCAP_A": ["POOL", "FDS", "PNR", "RS", "TKO", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE", "XPO", "AFRM", "HOOD", "SOFI", "DKNG", "RBLX", "TOST", "UPST", "AI", "PATH", "IOT", "U", "SNOW", "NET", "FSLR", "ENPH", "SEDG", "RUN", "PLUG", "CHPT", "BLINK", "RIVN", "LCID", "QS"],
    "MIDCAP_B": ["RKLB", "SPCE", "BABA", "LI", "NIO", "XPEV", "FUTU", "SE", "SHOP", "SQ", "PYPL", "COIN", "MARA", "RIOT", "CLSK", "WULF", "IREN", "HUT", "CORZ", "MSTR", "GME", "AMC", "DJT", "RDDT", "CELH", "WING", "FRSH", "APP", "PSTG", "NTNX", "NVAX", "MRNA", "BNTX", "CRSP", "EDIT", "BEAM", "NTLA", "PACB", "ILMN", "EXAS", "GH", "GUARD", "FGEN", "BYND", "OTLY", "HIMS", "SOUN", "BBAI", "CXAI", "PLTR"],
    "RUSSELL_2000_A": ["VNDA", "PETQ", "GPRO", "WKHS", "NKLA", "ASTR", "MNMD", "CYBN", "CMPS", "ATAI", "BMEA", "KPTI", "GERN", "BCAB", "XFOR", "CLSD", "EYEN", "OCUP", "OBLG", "SENS", "AMAM", "VERV", "BEAM", "CRBU", "CLLS", "DTIL", "EDIT", "FDMT", "NTLA", "SANA", "SGMO", "VIGL", "ZENTAL", "DRRX", "SCYX", "VYGR", "LRE", "AOUT", "SWBI", "RGR", "POWW", "VSTO", "DKS", "BGFV", "HIBB", "BOOT", "CAL", "DECK", "SKX", "WOLV"],
    "RUSSELL_2000_B": ["IEP", "AMR", "ARCH", "HCC", "CEIX", "BTU", "YAVY", "AAL", "ALGT", "HA", "SAVE", "BLNK", "EVGO", "CHPT", "BE", "FCEL", "PLUG", "AMRC", "CWEN", "AY", "NOVA", "RUN", "SUNW", "MAXN", "SHLS", "ARRY", "FTCI", "NXT", "ENPH", "SEDG", "DDD", "SSYS", "DM", "MKFG", "VLD", "XONE", "PRLB", "NNDM", "SGLY", "MIND", "KTOS", "AVAV", "RADA", "ASTR", "BKSY", "PL", "SATL", "LLAP", "SIDU", "QUBT"]
}

def calculate_indicators(df):
    df['High52'] = df['High'].rolling(252, min_periods=1).max()
    df['Drop_From_Peak'] = ((df['High52'] - df['Close']) / df['High52']) * 100
    df['MA20'] = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / df['MA20']) * 100
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift(1))
    low_cp = np.abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    rmf = tp * df['Volume']
    pos_flow = rmf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_flow = rmf.where(tp < tp.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0, 1e-10))))
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df

def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252: return None
        df = calculate_indicators(df)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        is_dropped = last_row['Drop_From_Peak'] >= 25.0
        is_quiet = last_row['BB_Width'] <= 9.5
        is_accumulating = (last_row['MFI'] > 48) & (last_row['MFI'] > prev_row['MFI'])
        if is_dropped and is_quiet and is_accumulating:
            return ticker, df
    except: return None
    return None

def draw_fixed_pro_chart(df, ticker):
    df_clean = df.copy()
    if df_clean.index.tz is not None: df_clean.index = df_clean.index.tz_localize(None)
    df_slice = df_clean.tail(90)
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, row_heights=[0.44, 0.12, 0.14, 0.15, 0.15], vertical_spacing=0.015)
    fig.add_trace(go.Candlestick(x=df_slice.index, open=df_slice['Open'], high=df_slice['High'], low=df_slice['Low'], close=df_slice['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA20'], line=dict(color='#3A86FF', width=1.2), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Upper'], line=dict(color='rgba(252,163,17,0.3)', width=1, dash='dash'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Lower'], line=dict(color='rgba(252,163,17,0.3)', width=1, dash='dash'), name='BB Lower'), row=1, col=1)
    vol_colors = ['#00B887' if row['Close'] >= row['Open'] else '#FF3A5A' for _, row in df_slice.iterrows()]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MFI'], line=dict(color='#FCA311', width=1.5), name='MFI'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['RSI'], line=dict(color='#FF9F1C', width=1.2), name='RSI'), row=4, col=1)
    macd_colors = ['#00B887' if val >= 0 else '#FF3A5A' for val in df_slice['MACD_Hist']]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['MACD_Hist'], marker_color=macd_colors, name='MACD Hist'), row=5, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MACD'], line=dict(color='#00F5D4', width=1.2), name='MACD'), row=5, col=1)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0B0E14", plot_bgcolor="#0B0E14", height=640, margin=dict(l=5, r=40, t=5, b=5), showlegend=True, xaxis_rangeslider_visible=False, hovermode=False, dragmode=False)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color='#5C5374', size=9), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False, tickfont=dict(color='#5C5374', size=9), side='right', fixedrange=True)
    return fig

def render_info_panel(ticker, df, badge_text, badge_class):
    last_row = df.iloc[-1]
    html_content = f"""<div class="info-panel"><span class="ticker-symbol">{ticker}</span><span class="badge {badge_class}">{badge_text}</span><div style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin-top: 15px; margin-bottom: 20px;">${last_row['Close']:.2f}</div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">מחזור מסחר:</span><span style="color: #E6E1F3; font-weight:600;">{(last_row['Volume']/1e6):.1f}M</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">ממוצע 20 ימים:</span><span style="color: #3A86FF; font-weight:600;">${last_row['MA20']:.2f}</span></div></div></div>"""
    st.markdown(html_content, unsafe_allow_html=True)

def render_kpi_metrics(df):
    last_row = df.iloc[-1]
    close_val = last_row['Close']
    drop_val = last_row['Drop_From_Peak']
    bbw_val = last_row['BB_Width']
    mfi_val = last_row['MFI']
    atr_val = last_row['ATR']
    stop_loss = last_row['BB_Lower'] * 0.985
    take_profit = close_val + (4.0 * atr_val)
    risk_pct = ((close_val - stop_loss) / close_val) * 100
    reward_pct = ((take_profit - close_val) / close_val) * 100
    rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-card"><span class="metric-label">📉 מרחק מהשיא</span><span class="metric-value" style="color:#FF3A5A;">-{drop_val:.1f}%</span></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><span class="metric-label">🤫 מדד דשדוש (BBW)</span><span class="metric-value" style="color:#3A86FF;">{bbw_val:.1f}%</span></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><span class="metric-label">🐳 זרימת כסף (MFI)</span><span class="metric-value" style="color:#00B887;">{mfi_val:.1f}</span></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-card"><span class="metric-label">📊 יחס סיכון (R:R)</span><span class="metric-value" style="color:#FCA311;">1:{rr_ratio:.2f}</span></div>', unsafe_allow_html=True)

def render_educational_card_and_calculator(df, unique_id=""):
    last_row = df.iloc[-1]
    close_val = last_row['Close']
    drop_val = last_row['Drop_From_Peak']
    bbw_val = last_row['BB_Width']
    mfi_val = last_row['MFI']
    atr_val = last_row['ATR']
    macd_hist = last_row['MACD_Hist']
    stop_loss = last_row['BB_Lower'] * 0.985
    take_profit = close_val + (4.0 * atr_val)
    risk_pct = ((close_val - stop_loss) / close_val) * 100
    reward_pct = ((take_profit - close_val) / close_val) * 100
    sub_tab1, sub_tab2 = st.tabs(["🧠 פענוח ומצב AI", "💰 מחשבון פוזיציה"])
    with sub_tab1:
        st.markdown(f'<div class="edu-card"><div class="edu-title">🔍 זיהוי שלב ההצטברות</div><div class="edu-text"><strong>1. מיצוי לחץ המוכרים:</strong> ירידה של <strong>{drop_val:.1f}%</strong> מהשיא השנתי.</div><div class="edu-text"><strong>2. כיווץ אנרגיה:</strong> מדד התנודתיות (BBW) עומד על <strong>{bbw_val:.1f}%</strong>.</div><div class="edu-text"><strong>3. כניסת מוסדיים שקטה:</strong> מדד זרימת הכסף (MFI) מטפס לרמה של <strong>{mfi_val:.1f}</strong>.</div><div class="edu-text"><strong>4. אישור מגמה (MACD):</strong> היסטוגרמה עומדת על <strong>{macd_hist:.2f}</strong>.</div></div>', unsafe_allow_html=True)
    with sub_tab2:
        st.markdown("<h3 style='margin-top:5px; margin-bottom:15px;'>🧮 הגדרת סיכונים אינטראקטיבית</h3>", unsafe_allow_html=True)
        calc_col1, calc_col2 = st.columns(2)
        with calc_col1: account_size = st.slider("גודל התיק שלך ($):", min_value=2000, max_value=100000, value=10000, step=1000, key=f"acc_{unique_id}")
        with calc_col2: risk_per_trade = st.slider("אחוז סיכון מותר (%):", min_value=0.25, max_value=5.0, value=1.0, step=0.25, key=f"risk_{unique_id}")
        allowed_loss = account_size * (risk_per_trade / 100)
        per_share_loss = close_val - stop_loss
        shares_to_buy = int(allowed_loss / per_share_loss) if per_share_loss > 0 else 0
        total_cost = shares_to_buy * close_val
        st.markdown(f'<div style="background: rgba(252, 163, 17, 0.05); border: 1px solid rgba(252, 163, 17, 0.2); border-radius: 8px; padding: 14px;"><span style="font-size:0.85rem; color:#B5AEC4; line-height:1.4;">• מחיר כניסה: <strong>${close_val:.2f}</strong> | 🛑 סטופ לוס: <strong>${stop_loss:.2f}</strong> ({risk_pct:.1f}%)<br>• יעד רווח משוער: <strong>${take_profit:.2f}</strong> ({reward_pct:.1f}%)<br>• פקודת רכש מומלצת: לקנות בדיוק <strong style="color:#FCA311;">{shares_to_buy} מניות</strong>.<br>• שווי הפוזיציה הכולל: <strong>${total_cost:,.2f}</strong>.</span></div>', unsafe_allow_html=True)

# --- ממשק משתמש ראשי ---
col_header, col_share = st.columns([3, 1])
with col_header:
    st.markdown('<h1 class="main-title">Quantum Terminal TITAN</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">מערכת סריקה וניהול תיק מבוזרת ברמת פרודקשן</p>', unsafe_allow_html=True)

with col_share:
    share_text = urllib.parse.quote("כנס לראות את הטרמינל האלגוריתמי שלי: " + "https://momentum-stock.streamlit.app")
    whatsapp_url = f"https://api.whatsapp.com/send?text={share_text}"
    st.markdown(f'<a href="{whatsapp_url}" target="_blank" class="whatsapp-btn">📢 שתף פוזיציה בוואטסאפ</a>', unsafe_allow_html=True)

tabs_names = ["💼 תיק השקעות", "🔍 בדיקה ידנית", "NASDAQ (א')", "NASDAQ (ב')", "S&P 500 (א')", "S&P 500 (ב')", "S&P 500 (ג')", "S&P 500 (ד')", "Mid-Cap (א')", "Mid-Cap (ב')", "Russell 2000 (א')", "Russell 2000 (ב')"]
tabs = st.tabs(tabs_names)

# --- לשונית 1: תיק השקעות דינמי ומאובטח ---
with tabs[0]:
    st.markdown("<h2 style='color:#FFFFFF; font-weight:800; margin-bottom:5px;'>📊 ניטור פוזיציות בזמן אמת</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#7E7497; font-size:0.9rem; margin-bottom:25px;'>מעקב אקטיבי אחר רווחים והגנות אלגוריתמיות למניות התיק</p>", unsafe_allow_html=True)
    
    total_value = 0.0
    total_cost_basis = 0.0
    portfolio_cards_data = []
    
    with st.spinner("טוען נתוני שוק עדכניים לתיק..."):
        for ticker, data in MY_PORTFOLIO.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="50d")
                if not hist.empty:
                    hist = calculate_indicators(hist)
                    last_row = hist.iloc[-1]
                    current_price = last_row['Close']
                    shares = data[0]
                    avg_cost = data[1]
                    
                    position_cost = shares * avg_cost
                    position_value = shares * current_price
                    position_pnl = position_value - position_cost
                    position_pnl_pct = (position_pnl / position_cost) * 100
                    
                    total_value += position_value
                    total_cost_basis += position_cost
                    
                    tech_stop = last_row['BB_Lower'] * 0.985
                    dist_to_stop = ((current_price - tech_stop) / current_price) * 100
                    
                    portfolio_cards_data.append({
                        "ticker": ticker, "shares": shares, "avg_cost": avg_cost,
                        "current_price": current_price, "pnl": position_pnl, "pnl_pct": position_pnl_pct,
                        "tech_stop": tech_stop, "dist_to_stop": dist_to_stop
                    })
            except:
                pass

    if total_cost_basis > 0:
        total_pnl = total_value - total_cost_basis
        total_pnl_pct = (total_pnl / total_cost_basis) * 100
        pnl_class = "p-positive" if total_pnl >= 0 else "p-negative"
        pnl_sign = "+" if total_pnl >= 0 else ""
        
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.markdown(f'<div class="metric-card"><span class="metric-label">💰 שווי תיק כולל</span><span class="metric-value">${total_value:,.2f}</span></div>', unsafe_allow_html=True)
        with kpi2: st.markdown(f'<div class="metric-card"><span class="metric-label">📈 רווח / הפסד כולל</span><span class="metric-value {pnl_class}">{pnl_sign}${total_pnl:,.2f}</span></div>', unsafe_allow_html=True)
        with kpi3: st.markdown(f'<div class="metric-card"><span class="metric-label">📊 תשואה באחוזים</span><span class="metric-value {pnl_class}">{pnl_sign}{total_pnl_pct:.2f}%</span></div>', unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:25px; margin-bottom:15px; font-weight:700; color:#938AA9;'>חלוקת פוזיציות:</div>", unsafe_allow_html=True)
        
        for item in portfolio_cards_data:
            c_class = "p-positive" if item['pnl'] >= 0 else "p-negative"
            c_sign = "+" if item['pnl'] >= 0 else ""
            alert_style = "color:#FF3A5A; font-weight:bold;" if item['dist_to_stop'] <= 3.0 else "color:#E6E1F3;"
            
            st.markdown(f"""
                <div class="portfolio-card">
                    <div class="portfolio-header">
                        <span class="portfolio-title">{item['ticker']} <span style='font-size:0.85rem; color:#7E7497; font-weight:400;'>({item['shares']} יחידות)</span></span>
                        <span class="portfolio-title {c_class}">{c_sign}{item['pnl_pct']:.2f}%</span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:0.85rem; border-top:1px solid #232B44; padding-top:10px;">
                        <div><span style="color:#7E7497;">שער קנייה:</span> <strong style="color:#FFFFFF;">${item['avg_cost']:.2f}</strong></div>
                        <div><span style="color:#7E7497;">שער שוק:</span> <strong style="color:#FFFFFF;">${item['current_price']:.2f}</strong></div>
                        <div><span style="color:#7E7497;">רווח/הפסד דולרי:</span> <strong class="{c_class}">{c_sign}${item['pnl']:,.2f}</strong></div>
                        <div><span style="color:#7E7497;">סטופ טכני (BB):</span> <strong style="{alert_style}">${item['tech_stop']:.2f} (-{item['dist_to_stop']:.1f}%)</strong></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("תיק ההשקעות ריק כעת. כדי להזין מניות, עדכן את המילון MY_PORTFOLIO בשורה 43 של הקוד.")

# --- לשונית 2: בדיקה ידנית ---
with tabs[1]:
    col_search, _ = st.columns([1.5, 2])
    with col_search: search_ticker = st.text_input("הזן סימול לבדיקה ידנית:", value="").strip().upper()
    if search_ticker:
        with st.spinner(f"מנתח..."):
            try:
                stock_data = yf.Ticker(search_ticker).history(period="300d")
                if len(stock_data) >= 252:
                    stock_data = calculate_indicators(stock_data)
                    render_kpi_metrics(stock_data)
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    l_col, r_col = st.columns([1.2, 3.8])
                    with l_col: render_info_panel(search_ticker, stock_data, "PRO Analysis", "badge-search")
                    with r_col:
                        st.plotly_chart(draw_fixed_pro_chart(stock_data, search_ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card_and_calculator(stock_data, unique_id=f"manual_{search_ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else: st.error("אין מספיק מידע היסטורי.")
            except Exception as e: st.error(f"שגיאה: {str(e)}")

# --- לשוניות הסריקה ---
sections_keys = ["NASDAQ_A", "NASDAQ_B", "SP500_A", "SP500_B", "SP500_C", "SP500_D", "MIDCAP_A", "MIDCAP_B", "RUSSELL_2000_A", "RUSSELL_2000_B"]
for i, group_id in enumerate(sections_keys):
    with tabs[i + 2]:
        num_stocks = len(MARKET_DATA[group_id])
        scan_clicked = st.button(f"הפעל סורק לווייתנים ({num_stocks} מניות)", key=f"btn_{i}")
        if scan_clicked or st.session_state.get(f"accum_ready_{group_id}", False):
            if scan_clicked:
                with st.spinner("מריץ סורק אלגוריתמי..."):
                    tickers = MARKET_DATA.get(group_id, [])
                    with ThreadPoolExecutor(max_workers=10) as ex: results = list(ex.map(run_scanner, tickers))
                    st.session_state[f"accum_data_{group_id}"] = {r[0]: r[1] for r in results if r is not None}
                    st.session_state[f"accum_ready_{group_id}"] = True
            found_data = st.session_state.get(f"accum_data_{group_id}", {})
            if found_data:
                for ticker, df_ticker in found_data.items():
                    render_kpi_metrics(df_ticker)
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    l_col, r_col = st.columns([1.2, 3.8])
                    with l_col: render_info_panel(ticker, df_ticker, "Accumulation Trigger", "badge-accum")
                    with r_col:
                        st.plotly_chart(draw_fixed_pro_chart(df_ticker, ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card_and_calculator(df_ticker, unique_id=f"{group_id}_{ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else: st.info("לא אותרו כרגע מניות שעונות על כל תנאי איסוף הסחורה בקבוצה זו.")

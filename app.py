import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal v2", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום מודרני ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #00B887, #E2B4BD); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 35px; }
    
    /* טאבים */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; border-bottom: 1px solid #1E1833; }
    .stTabs [data-baseweb="tab"] { background-color: #151026; border-radius: 20px; color: #938AA9; padding: 8px 20px; border: 1px solid #231B3D; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: #2D2447 !important; color: #00B887 !important; border-color: #00B887 !important; font-weight: 600; }
    
    /* כרטיסיית מניה משולבת */
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 16px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 14px; height: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; display: block; }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-top: 6px; text-align: center; }
    .badge-reversal { background-color: rgba(0, 184, 135, 0.15); color: #00B887; }
    .badge-breakout { background-color: rgba(255, 159, 28, 0.15); color: #FF9F1C; }
    .badge-search { background-color: rgba(58, 134, 255, 0.15); color: #3A86FF; }
    
    /* אלמנטים של אינדיקטורים במקרא */
    .indicator-box { margin-top: 12px; padding-top: 8px; border-top: 1px solid #1F2538; }
    .indicator-row { display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 4px; }
    .indicator-name { color: #938AA9; font-weight: 500; }
    .indicator-desc { color: #5C5374; font-size: 0.7rem; display: block; margin-bottom: 6px; line-height: 1.1; }
    
    /* כרטיס הסבר לימודי */
    .edu-card { background: #12101F; border: 1px solid #251F3D; border-radius: 12px; padding: 16px; margin-top: 15px; }
    .edu-title { color: #E2B4BD; font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
    .edu-metric { font-size: 0.9rem; font-weight: 600; margin-bottom: 8px; }
    .edu-text { font-size: 0.85rem; color: #B5AEC4; line-height: 1.4; margin-bottom: 8px; }
    
    /* כפתור הפעלה ותיבות קלט */
    .stButton>button { background: linear-gradient(180deg, #1A202C, #0B0E14); color: #E6E1F3; border: 1px solid #2D3748; border-radius: 12px; padding: 10px 24px; font-weight: 600; width: 100%; transition: all 0.3s; }
    .stButton>button:hover { border-color: #00B887; color: #00B887; }
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input { background-color: #111522 !important; color: #FFFFFF !important; border: 1px solid #1F2538 !important; border-radius: 10px !important; }
    </style>
""", unsafe_allow_html=True)

# --- מאגר נתוני השוק ---
MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"],
    "NASDAQ_B": ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"],
    "NASDAQ_C": ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"],
    "NASDAQ_D": ["SBAC", "ALGN", "EBAY", "SIRI", "ZBRA", "ILMN", "WBA", "JD", "BIDU", "LCID", "ZM", "MRNA", "PYPL", "INTC", "MU", "DLTR", "EXPE", "LULU"],
    "SP500_A": ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"],
    "SP500_B": ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG", "HON", "LOW", "SPGI", "BLK", "NOW"],
    "DOW_FULL": ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"],
    "MIDCAP": ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE"]
}

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['Vol20'] = df['Volume'].rolling(20).mean()
    
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    
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
    
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    rmf = tp * df['Volume']
    pos_flow = rmf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_flow = rmf.where(tp < tp.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0, 1e-10))))
    
    df['Buy_Signal'] = ((df['Close'] > df['MA20']) & (df['Close'].shift(1) <= df['MA20'].shift(1))) | \
                       ((df['Close'] > df['High20']) & (df['Volume'] > df['Vol20']))
    df['Sell_Signal'] = (df['Close'] < df['MA20']) & (df['Close'].shift(1) >= df['MA20'].shift(1))
    return df

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="120d")
        if len(df) < 50: return None
        df = calculate_indicators(df)
        
        if scan_type == "REVERSAL":
            is_valid = (df['Close'].iloc[-1] > df['MA20'].iloc[-1]) & (df['Close'].iloc[-2] < df['MA20'].iloc[-2])
        elif scan_type == "BREAKOUT":
            is_valid = (df['Close'].iloc[-1] > df['High20'].iloc[-1]) & (df['Volume'].iloc[-1] > df['Vol20'].iloc[-1])
            
        if is_valid: return ticker, df
    except: return None
    return None

def draw_fixed_pro_chart(df, ticker):
    df_clean = df.copy()
    if df_clean.index.tz is not None: df_clean.index = df_clean.index.tz_localize(None)
    df_slice = df_clean.tail(75)
    
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, row_heights=[0.40, 0.12, 0.16, 0.16, 0.16], vertical_spacing=0.015)
    fig.add_trace(go.Candlestick(x=df_slice.index, open=df_slice['Open'], high=df_slice['High'], low=df_slice['Low'], close=df_slice['Close'], increasing_line_color='#00B887', decreasing_line_color='#FF3A5A', name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA20'], line=dict(color='#3A86FF', width=1.2), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Upper'], line=dict(color='rgba(0,184,135,0.25)', width=1, dash='dash'), name='BB Up'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Lower'], line=dict(color='rgba(255,58,90,0.25)', width=1, dash='dash'), name='BB Dn'), row=1, col=1)
    
    vol_colors = ['#00B887' if row['Close'] >= row['Open'] else '#FF3A5A' for _, row in df_slice.iterrows()]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)
    
    macd_colors = ['#00B887' if val >= 0 else '#FF3A5A' for val in df_slice['MACD_Hist']]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['MACD_Hist'], marker_color=macd_colors, name='Hist'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MACD'], line=dict(color='#FCA311', width=1.2), name='MACD'), row=3, col=1)
    
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['RSI'], line=dict(color='#FF9F1C', width=1.2), name='RSI'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MFI'], line=dict(color='#00F5D4', width=1.2), name='MFI'), row=5, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0B0E14", plot_bgcolor="#0B0E14", height=580, margin=dict(l=5, r=40, t=10, b=10), showlegend=False, xaxis_rangeslider_visible=False, hovermode=False, dragmode=False)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color='#5C5374', size=9), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)', zeroline=False, tickfont=dict(color='#5C5374', size=9), side='right', fixedrange=True)
    return fig

def render_info_panel(ticker, df, badge_text, badge_class, price_color):
    last_row = df.iloc[-1]
    rsi_val = last_row['RSI']
    mfi_val = last_row['MFI']
    macd_hist = last_row['MACD_Hist']
    rsi_color = "#FF3A5A" if rsi_val > 70 else ("#00B887" if rsi_val < 30 else "#E6E1F3")
    mfi_color = "#FF3A5A" if mfi_val > 80 else ("#00B887" if mfi_val < 20 else "#E6E1F3")
    macd_color = "#00B887" if macd_hist >= 0 else "#FF3A5A"
    
    html_content = f"""<div class="info-panel"><span class="ticker-symbol">{ticker}</span><span class="badge {badge_class}">{badge_text}</span><div style="font-size: 1.4rem; font-weight: 700; color: {price_color}; margin-top: 10px;">${last_row['Close']:.2f}</div><div style="color: #7E7497; font-size: 0.75rem; margin-bottom: 10px; font-weight: 500;">Vol: {(last_row['Volume']/1e6):.1f}M</div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">BB (בולינג'ר)</span><span style="color: #3A86FF; font-weight:700;">מחיר/רצועה</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">MACD</span><span style="color: {macd_color}; font-weight:700;">{macd_hist:.2f}</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">RSI</span><span style="color: {rsi_color}; font-weight:700;">{rsi_val:.1f}</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">MFI</span><span style="color: {mfi_color}; font-weight:700;">{mfi_val:.1f}</span></div></div></div>"""
    st.markdown(html_content, unsafe_allow_html=True)

# --- מנוע הניתוח הלימודי המשולב עם מחשבון ניהול סיכונים ---
def render_educational_card(df, is_reversal, is_breakout, is_manual_search=False, unique_id=""):
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    rsi = last_row['RSI']
    mfi = last_row['MFI']
    macd_h = last_row['MACD_Hist']
    vol = last_row['Volume']
    vol_avg = last_row['Vol20']
    close_val = last_row['Close']
    ma20_val = last_row['MA20']
    high20_val = last_row['High20']
    bb_upper = last_row['BB_Upper']
    bb_lower = last_row['BB_Lower']
    
    score = 55 
    if vol > vol_avg: score += 10
    if macd_h > 0: score += 5
    if rsi < 40 and is_reversal: score += 10
    if mfi < 35: score += 5
    
    dist_to_upper = ((bb_upper - close_val) / close_val) * 100
    dist_to_lower = ((close_val - bb_lower) / close_val) * 100
    if score > 85: score = 85 
    
    # חישוב יעדים ומניעת הפסד אוטומטיים
    if is_breakout or (is_manual_search and close_val > high20_val):
        stop_loss = high20_val * 0.985 # סטופ מתחת לרמת הפריצה
        take_profit = close_val * 1.10 # יעד שמרני של 10% מעל הפריצה
        trigger_reason = f"המניה זוהתה על ידי ה-AI מכיוון שמחיר הסגירה הנוכחי (${close_val:.2f}) פרץ באופן מובהק את שיא 20 הימים האחרונים שעמד על ${high20_val:.2f}."
        reason_desc = f"נפח המסחר גבוה ב-{((vol/vol_avg)-1)*100:.1f}% מהממוצע, מה שמעיד על כניסת כסף מוסדי מסיבי."
        prevention = "הסכנה המרכזית היא פריצת שווא (Fakeout). אם ה-RSI מתוח, מומלץ להמתין לנסיגה לבדיקת התמיכה מחדש."
    else:
        stop_loss = bb_lower # סטופ מתחת לרצועה התחתונה
        take_profit = bb_upper # יעד ברצועה העליונה
        trigger_reason = f"המניה נכנסה לסורק בעקבות חציית מחיר שורית: מחיר המניה (${close_val:.2f}) חצה כלפי מעלה את קו הממוצע הנע ל-20 ימים (${ma20_val:.2f})."
        reason_desc = f"המחיר ביצע בדיקה ונתמך במרחק של {dist_to_lower:.1f}% בלבד מרצועת בולינג'ר התחתונה, מה שמסמן היפוך ממצב מכירת יתר."
        prevention = "הסיכון הוא שהמגמה הדובית הקודמת טרם הסתיימה. יעד הרצועה העליונה נמצא במרחק של {dist_to_upper:.1f}%."

    risk_pct = ((close_val - stop_loss) / close_val) * 100
    reward_pct = ((take_profit - close_val) / close_val) * 100
    rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

    st.markdown(f"""
        <div class="edu-card">
            <div class="edu-title">🧠 מרכז פענוח וניתוח AI לימודי</div>
            <div class="edu-metric">🎯 סיכויי הצלחה משוערים: <span style="color: {'#00B887' if score >= 70 else '#FF9F1C'}; font-weight: 800;">{score}%</span></div>
            <div class="edu-text"><strong>🔍 למה המניה נכנסה לסורק?</strong> {trigger_reason}</div>
            <div class="edu-text"><strong>📊 הסבר הניתוח הטכני:</strong> {reason_desc}</div>
            <div class="edu-text"><strong>⚠️ גורמי מניעה וסיכוני שוק:</strong> {prevention}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # הוספת רכיב המחשבון הלימודי ישירות מתחת
    st.markdown(f"""
        <div style="margin-top:10px; border-top:1px dashed #251F3D; padding-top:10px;">
            <div style="color:#00B887; font-size:0.95rem; font-weight:700; margin-bottom:8px;">💰 מחשבון ניהול סיכונים ופוזיציות דינמי</div>
            <div style="font-size:0.82rem; color:#B5AEC4; margin-bottom:12px;">
                • מחיר כניסה נוכחי: <strong>${close_val:.2f}</strong><br>
                • 🛑 סטופ לוס מומלץ (מניעת הפסד): <strong>${stop_loss:.2f}</strong> (סיכון של {risk_pct:.1f}%)<br>
                • 🎯 יעד רווח משוער: <strong>${take_profit:.2f}</strong> (פוטנציאל של {reward_pct:.1f}%)<br>
                • 📊 יחס סיכוי לסיכון ($R:R$): <strong style="color:#00B887;">1:{rr_ratio:.2f}</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # שדות קלט דינמיים של המשתמש לצורך חישוב גודל פוזיציה
    calc_col1, calc_col2 = st.columns(2)
    with calc_col1:
        account_size = st.number_input("גודל תיק המסחר שלך ($):", value=10000, step=1000, key=f"acc_{unique_id}")
    with calc_col2:
        risk_per_trade = st.number_input("אחוז סיכון מותר לטרייד (%):", value=1.0, step=0.5, key=f"risk_{unique_id}")
        
    allowed_loss = account_size * (risk_per_trade / 100)
    per_share_loss = close_val - stop_loss
    shares_to_buy = int(allowed_loss / per_share_loss) if per_share_loss > 0 else 0
    total_cost = shares_to_buy * close_val
    
    st.markdown(f"""
        <div style="background: rgba(0, 184, 135, 0.05); border: 1px solid rgba(0, 184, 135, 0.2); border-radius: 8px; padding: 10px; margin-top: 8px;">
            <span style="font-size:0.85rem; color:#E6E1F3; display:block;">🧮 <strong>הנחיית ה-AI לגודל פוזיציה:</strong></span>
            <span style="font-size:0.8rem; color:#B5AEC4;"> כדי לסכן רק <strong>${allowed_loss:.2f}</strong> מהתיק, עליך לקנות בדיוק <strong style="color:#00B887; font-size:0.95rem;">{shares_to_buy} מניות</strong>. שווי פוזיציה כולל: ${total_cost:,.2f}. אם הסטופ-לוס יופעל, הפסדת רק את הסיכון שהגדרת מראש.</span>
        </div>
    """, unsafe_allow_html=True)

# --- ממשק משתמש ראשי ---
st.markdown('<h1 class="main-title">Quantum Terminal</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">מערכת סריקה וניתוח בתצורת Webull Pro Pro</p>', unsafe_allow_html=True)

tabs_names = ["🔍 חיפוש מניה", "NASDAQ א'", "NASDAQ ב'", "NASDAQ ג'", "NASDAQ ד'", "S&P500 א'", "S&P500 ב'", "DOW מלא", "MIDCAP"]
tabs = st.tabs(tabs_names)

with tabs[0]:
    col_search, _ = st.columns([1.5, 2])
    with col_search:
        search_ticker = st.text_input("הזן סימול מניה (לדוגמה: AAPL, TSLA, NVDA):", value="").strip().upper()
    
    if search_ticker:
        with st.spinner(f"מושך נתונים עבור {search_ticker}..."):
            try:
                stock_data = yf.Ticker(search_ticker).history(period="120d")
                if len(stock_data) >= 20:
                    stock_data = calculate_indicators(stock_data)
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    col_left, col_right = st.columns([1.5, 3.5])
                    with col_left:
                        last_close = stock_data['Close'].iloc[-1]
                        prev_close = stock_data['Close'].iloc[-2]
                        render_info_panel(search_ticker, stock_data, "Analysis Mode", "badge-search", "#00B887" if last_close >= prev_close else "#FF3A5A")
                    with col_right:
                        st.plotly_chart(draw_fixed_pro_chart(stock_data, search_ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card(stock_data, is_reversal=False, is_breakout=False, is_manual_search=True, unique_id=f"manual_{search_ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"שגיאה במשיכת הנתונים. ודא שהסימול נכון. ({str(e)})")

sections_keys = ["NASDAQ_A", "NASDAQ_B", "NASDAQ_C", "NASDAQ_D", "SP500_A", "SP500_B", "DOW_FULL", "MIDCAP"]
for i, group_id in enumerate(sections_keys):
    with tabs[i + 1]:
        col_ctrl, _ = st.columns([1, 2])
        with col_ctrl:
            mode = st.radio("אסטרטגיה:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}", horizontal=True)
            scan_clicked = st.button("הפעל סריקה", key=f"btn_{i}")
        
        if scan_clicked or st.session_state.get(f"results_ready_{group_id}", False):
            if scan_clicked:
                with st.spinner("סורק נתוני שוק..."):
                    tickers = MARKET_DATA.get(group_id, [])
                    with ThreadPoolExecutor(max_workers=10) as ex:
                        results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                    st.session_state[f"data_{group_id}"] = {r[0]: r[1] for r in results if r is not None}
                    st.session_state[f"results_ready_{group_id}"] = True
                    st.session_state[f"current_mode_{group_id}"] = mode
            
            found_data = st.session_state.get(f"data_{group_id}", {})
            active_mode = st.session_state.get(f"current_mode_{group_id}", mode)
            
            if found_data:
                for ticker, df_ticker in found_data.items():
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    col_left, col_right = st.columns([1.5, 3.5])
                    with col_left:
                        render_info_panel(ticker, df_ticker, "Reversal" if active_mode == "REVERSAL" else "Breakout", "badge-reversal" if active_mode == "REVERSAL" else "badge-breakout", "#00B887" if active_mode == "REVERSAL" else "#FF9F1C")
                    with col_right:
                        st.plotly_chart(draw_fixed_pro_chart(df_ticker, ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card(df_ticker, is_reversal=(active_mode == "REVERSAL"), is_breakout=(active_mode == "BREAKOUT"), unique_id=f"{group_id}_{ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("לא אותרו איתותים בקבוצה זו תחת התנאים שנבחרו.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Accumulation Scanner", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #FCA311, #00B887); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 35px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; border-bottom: 1px solid #1E1833; }
    .stTabs [data-baseweb="tab"] { background-color: #151026; border-radius: 20px; color: #938AA9; padding: 8px 20px; border: 1px solid #231B3D; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: #2D2447 !important; color: #FCA311 !important; border-color: #FCA311 !important; font-weight: 600; }
    
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 16px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 14px; height: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; display: block; }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-top: 6px; text-align: center; }
    .badge-accum { background-color: rgba(252, 163, 17, 0.15); color: #FCA311; }
    .badge-search { background-color: rgba(58, 134, 255, 0.15); color: #3A86FF; }
    
    .indicator-box { margin-top: 12px; padding-top: 8px; border-top: 1px solid #1F2538; }
    .indicator-row { display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 4px; }
    .indicator-name { color: #938AA9; font-weight: 500; }
    
    .edu-card { background: #12101F; border: 1px solid #251F3D; border-radius: 12px; padding: 16px; margin-top: 15px; }
    .edu-title { color: #E2B4BD; font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; }
    .edu-text { font-size: 0.85rem; color: #B5AEC4; line-height: 1.4; margin-bottom: 8px; }
    
    .stButton>button { background: linear-gradient(180deg, #1A202C, #0B0E14); color: #E6E1F3; border: 1px solid #2D3748; border-radius: 12px; padding: 10px 24px; font-weight: 600; width: 100%; }
    .stButton>button:hover { border-color: #FCA311; color: #FCA311; }
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input { background-color: #111522 !important; color: #FFFFFF !important; border: 1px solid #1F2538 !important; border-radius: 10px !important; }
    </style>
""", unsafe_allow_html=True)

# --- מאגר נתוני השוק (מניות נבחרות לבדיקה) ---
MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"],
    "NASDAQ_B": ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"],
    "NASDAQ_C": ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"],
    "SP500_A": ["BRK.B", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY", "WMT", "MCD", "CRM", "BAC", "ACN", "TMO", "LIN", "ORCL", "CMCSA", "ABT", "NKE", "PM", "UPS", "COP", "MS", "PFE"],
    "MIDCAP_A": ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE"]
}

def calculate_indicators(df):
    # חישוב שיא שנתי (252 ימי מסחר) לבדיקת עוצמת הירידה
    df['High52'] = df['High'].rolling(252, min_periods=1).max()
    df['Drop_From_Peak'] = ((df['High52'] - df['Close']) / df['High52']) * 100
    
    # בולינג'ר וחישוב רוחב רצועה (Bandwidth) למדידת דשדוש ורוגע
    df['MA20'] = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / df['MA20']) * 100
    
    # מדדי נפח זרימת כסף (MFI ו-ATR) לזיהוי איסוף שקט
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
    
    return df

def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252: return None
        df = calculate_indicators(df)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # תנאי מסנן "קפיץ דרוך - איסוף סחורה בשפל":
        # 1. ירדה חזק: המניה רחוקה לפחות 25% מהשיא השנתי שלה
        is_dropped = last_row['Drop_From_Peak'] >= 25.0
        
        # 2. נרגעה ומדשדשת: רוחב רצועות בולינג'ר צר מאוד (מתחת ל-9%), המחיר נעצר
        is_quiet = last_row['BB_Width'] <= 9.0
        
        # 3. איסוף סחורה מסיבי שקט: מדד זרימת הכסף (MFI) מזנק למעלה (מעל 50) למרות שהמחיר לא עלה עדיין
        is_accumulating = (last_row['MFI'] > 50) & (last_row['MFI'] > prev_row['MFI'])
        
        if is_dropped and is_quiet and is_accumulating:
            return ticker, df
    except:
        return None
    return None

def draw_fixed_pro_chart(df, ticker):
    df_clean = df.copy()
    if df_clean.index.tz is not None: df_clean.index = df_clean.index.tz_localize(None)
    df_slice = df_clean.tail(90) # תצוגה מעט רחבה יותר כדי לראות את הדשדוש הצידה
    
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.50, 0.15, 0.17, 0.18], vertical_spacing=0.02)
    fig.add_trace(go.Candlestick(x=df_slice.index, open=df_slice['Open'], high=df_slice['High'], low=df_slice['Low'], close=df_slice['Close'], increasing_line_color='#00B887', decreasing_line_color='#FF3A5A', name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA20'], line=dict(color='#3A86FF', width=1.2), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Upper'], line=dict(color='rgba(252,163,17,0.3)', width=1, dash='dash'), name='BB Up'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Lower'], line=dict(color='rgba(252,163,17,0.3)', width=1, dash='dash'), name='BB Dn'), row=1, col=1)
    
    vol_colors = ['#00B887' if row['Close'] >= row['Open'] else '#FF3A5A' for _, row in df_slice.iterrows()]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MFI'], line=dict(color='#FCA311', width=1.5), name='MFI (זרימת כסף)'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['RSI'], line=dict(color='#FF9F1C', width=1.2), name='RSI'), row=4, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0B0E14", plot_bgcolor="#0B0E14", height=580, margin=dict(l=5, r=40, t=10, b=10), showlegend=False, xaxis_rangeslider_visible=False, hovermode=False, dragmode=False)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color='#5C5374', size=9), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)', zeroline=False, tickfont=dict(color='#5C5374', size=9), side='right', fixedrange=True)
    return fig

def render_info_panel(ticker, df, badge_text, badge_class):
    last_row = df.iloc[-1]
    mfi_val = last_row['MFI']
    rsi_val = last_row['RSI']
    bbw_val = last_row['BB_Width']
    drop_val = last_row['Drop_From_Peak']
    
    html_content = f"""<div class="info-panel"><span class="ticker-symbol">{ticker}</span><span class="badge {badge_class}">{badge_text}</span><div style="font-size: 1.4rem; font-weight: 700; color: #FFFFFF; margin-top: 10px;">${last_row['Close']:.2f}</div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">ירידה מהשיא</span><span style="color: #FF3A5A; font-weight:700;">-{drop_val:.1f}%</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">מדד כיווץ (BBW)</span><span style="color: #3A86FF; font-weight:700;">{bbw_val:.1f}%</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">MFI (כסף נכנס)</span><span style="color: #00B887; font-weight:700;">{mfi_val:.1f}</span></div></div><div class="indicator-box"><div class="indicator-row"><span class="indicator-name">RSI</span><span style="color: #E6E1F3; font-weight:700;">{rsi_val:.1f}</span></div></div></div>"""
    st.markdown(html_content, unsafe_allow_html=True)

def render_educational_card(df, unique_id=""):
    last_row = df.iloc[-1]
    close_val = last_row['Close']
    drop_val = last_row['Drop_From_Peak']
    bbw_val = last_row['BB_Width']
    mfi_val = last_row['MFI']
    atr_val = last_row['ATR']
    
    # מיקום סטופ קרוב מאוד מתחת לרצפת הדשדוש (סיכון אפסי)
    stop_loss = last_row['BB_Lower'] * 0.985
    # יעד פריצה משמעותי למעלה (בום)
    take_profit = close_val + (4.0 * atr_val)
    
    risk_pct = ((close_val - stop_loss) / close_val) * 100
    reward_pct = ((take_profit - close_val) / close_val) * 100
    rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

    st.markdown(f"""
        <div class="edu-card">
            <div class="edu-title">🧠 פענוח AI: זיהוי שלב ההצטברות (Accumulation)</div>
            <div class="edu-text"><strong>📉 היסטוריית הקריסה:</strong> המניה הושמדה ב-<strong>{drop_val:.1f}%</strong> מהשיא השנתי שלה, מה שמבטיח שכל המוכרים החלשים כבר יצאו מהפוזיציה והלחץ הדובי מוצה.</div>
            <div class="edu-text"><strong>🤫 הצימוק והרוגע:</strong> רוחב רצועות בולינג'ר עומד על <strong>{bbw_val:.1f}%</strong> בלבד. המשמעות היא שהמניה נכנסה למצב של כיווץ אנרגיה קיצוני ודשדוש "מת" הצידה.</div>
            <div class="edu-text"><strong>🐳 עקבות לווייתנים (איסוף סחורה):</strong> שים לב! למרות שהמחיר תקוע, מדד ה-MFI זינק ל-<strong>{mfi_val:.1f}</strong>. זהו סימן מובהק שכסף גדול מוסדי קונה מניות בחשאי ללא יצירת רעש במחיר.</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="margin-top:10px; border-top:1px dashed #251F3D; padding-top:10px;">
            <div style="color:#FCA311; font-size:0.95rem; font-weight:700; margin-bottom:8px;">💰 מחשבון פוזיציה מבוסס רצפת דשדוש</div>
            <div style="font-size:0.82rem; color:#B5AEC4; margin-bottom:12px;">
                • מחיר נוכחי: <strong>${close_val:.2f}</strong><br>
                • 🛑 סטופ לוס הדוק (מתחת לרצפת הדשדוש): <strong>${stop_loss:.2f}</strong> (סיכון קטן של {risk_pct:.1f}%)<br>
                • 🎯 יעד רווח (פוטנציאל פיצוץ ראשוני): <strong>${take_profit:.2f}</strong> (רווח של {reward_pct:.1f}%)<br>
                • 📊 יחס סיכון לסיכון פנומנלי ($R:R$): <strong style="color:#00B887; font-size: 0.9rem;">1:{rr_ratio:.2f}</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
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
        <div style="background: rgba(252, 163, 17, 0.05); border: 1px solid rgba(252, 163, 17, 0.2); border-radius: 8px; padding: 10px; margin-top: 8px;">
            <span style="font-size:0.85rem; color:#E6E1F3; display:block;">🧮 <strong>הקצאת הון חכמה:</strong></span>
            <span style="font-size:0.8rem; color:#B5AEC4;"> מכיוון שהסטופ הדוק מאוד, אתה יכול לקנות <strong style="color:#FCA311; font-size:0.95rem;">{shares_to_buy} מניות</strong> בשווי כולל של ${total_cost:,.2f} ועדיין להסתכן בהפסד של <strong>${allowed_loss:.2f}</strong> בלבד אם הרצפה תישבר.</span>
        </div>
    """, unsafe_allow_html=True)

# --- ממשק משתמש ראשי ---
st.markdown('<h1 class="main-title">Quantum Terminal - Accumulation Edition</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">סורק אלגוריתמי לאיתור מניות בשלב איסוף שקט (לפני זינוק)</p>', unsafe_allow_html=True)

tabs_names = ["🔍 בדיקת מניה ידנית", "NASDAQ א'", "NASDAQ ב'", "NASDAQ ג'", "S&P 500", "MIDCAP"]
tabs = st.tabs(tabs_names)

with tabs[0]:
    col_search, _ = st.columns([1.5, 2])
    with col_search:
        search_ticker = st.text_input("הזן סימול לבדיקת איסוף (לדוגמה: AAPL, Intel וכד'):", value="").strip().upper()
    
    if search_ticker:
        with st.spinner(f"מנתח את {search_ticker}..."):
            try:
                stock_data = yf.Ticker(search_ticker).history(period="300d")
                if len(stock_data) >= 252:
                    stock_data = calculate_indicators(stock_data)
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    col_left, col_right = st.columns([1.5, 3.5])
                    with col_left:
                        render_info_panel(search_ticker, stock_data, "Manual Analysis", "badge-search")
                    with col_right:
                        st.plotly_chart(draw_fixed_pro_chart(stock_data, search_ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card(stock_data, unique_id=f"manual_{search_ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error("אין מספיק מידע היסטורי עבור מניה זו.")
            except Exception as e:
                st.error(f"שגיאה במשיכת הנתונים: {str(e)}")

sections_keys = ["NASDAQ_A", "NASDAQ_B", "NASDAQ_C", "SP500_A", "MIDCAP_A"]
for i, group_id in enumerate(sections_keys):
    with tabs[i + 1]:
        scan_clicked = st.button("הפעל סורק לווייתנים (איסוף סחורה)", key=f"btn_{i}")
        
        if scan_clicked or st.session_state.get(f"accum_ready_{group_id}", False):
            if scan_clicked:
                with st.spinner("סורק שוק ומאתר מניות בכיווץ אנרגיה ואיסוף מסיבי..."):
                    tickers = MARKET_DATA.get(group_id, [])
                    with ThreadPoolExecutor(max_workers=10) as ex:
                        results = list(ex.map(run_scanner, tickers))
                    st.session_state[f"accum_data_{group_id}"] = {r[0]: r[1] for r in results if r is not None}
                    st.session_state[f"accum_ready_{group_id}"] = True
            
            found_data = st.session_state.get(f"accum_data_{group_id}", {})
            
            if found_data:
                for ticker, df_ticker in found_data.items():
                    st.markdown('<div class="stock-container">', unsafe_allow_html=True)
                    col_left, col_right = st.columns([1.5, 3.5])
                    with col_left:
                        render_info_panel(ticker, df_ticker, "Accumulation Phase", "badge-accum")
                    with col_right:
                        st.plotly_chart(draw_fixed_pro_chart(df_ticker, ticker), use_container_width=True, config={'displayModeBar': False})
                        render_educational_card(df_ticker, unique_id=f"{group_id}_{ticker}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("לא אותרו כרגע מניות שעונות בצורה מושלמת על כל תנאי איסוף הסחורה והכיווץ הקיצוני בקבוצה זו.")

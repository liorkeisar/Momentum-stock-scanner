import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal v2", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום מודרני ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #F1EFF7, #E2B4BD); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 35px; }
    
    /* טאבים כפתורי קפסולה */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; border-bottom: 1px solid #1E1833; }
    .stTabs [data-baseweb="tab"] { background-color: #151026; border-radius: 20px; color: #938AA9; padding: 8px 20px; border: 1px solid #231B3D; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: #E2B4BD !important; color: #0A0712 !important; border-color: #E2B4BD !important; font-weight: 600; }
    
    /* כרטיסיות מניות */
    .premium-card { background: #120D24; border: 1px solid #1F173A; border-radius: 20px; padding: 24px; margin-bottom: 15px; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    .badge { padding: 6px 14px; border-radius: 30px; font-size: 0.8rem; font-weight: 600; }
    .badge-reversal { background-color: rgba(74, 212, 134, 0.12); color: #4AD486; }
    .badge-breakout { background-color: rgba(244, 162, 97, 0.12); color: #F4A261; }
    
    /* כפתור הפעלה */
    .stButton>button { background: linear-gradient(180deg, #241A42, #191230); color: #E6E1F3; border: 1px solid #33265C; border-radius: 14px; padding: 12px 28px; font-weight: 600; width: 100%; }
    .stButton>button:hover { border-color: #E2B4BD; color: #E2B4BD; }
    
    /* עיצוב רובריקות הבחירה למתנדים */
    div[data-testid="stCheckbox"] {
        background-color: #151026;
        border: 1px solid #231B3D;
        padding: 8px 16px;
        border-radius: 12px;
        transition: all 0.2s ease;
    }
    div[data-testid="stCheckbox"]:hover {
        border-color: #E2B4BD;
    }
    </style>
""", unsafe_allow_html=True)

# --- מאגר המניות המלא מחולק לקבוצות ---
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

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        
        # חישוב מתנדים בסיסיים לסריקה וגרפים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        
        # חישוב אינדיקטורים מורחבים
        std20 = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['MA20'] + (std20 * 2)
        df['BB_Lower'] = df['MA20'] - (std20 * 2)
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # MFI (Money Flow Index)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        rmf = tp * df['Volume']
        pos_flow = rmf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_flow = rmf.where(tp < tp.shift(1), 0).rolling(14).sum()
        df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))
        
        if scan_type == "REVERSAL":
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker, df
        elif scan_type == "BREAKOUT":
            if df['Close'].iloc[-1] > df['High20'].iloc[-1] and df['Volume'].iloc[-1] > df['Vol20'].iloc[-1]:
                return ticker, df
    except: return None
    return None

def draw_premium_chart(df, ticker, mode, show_bb, show_rsi, show_macd, show_mfi):
    df_clean = df.copy()
    if df_clean.index.tz is not None:
        df_clean.index = df_clean.index.tz_localize(None)
        
    df_slice = df_clean.tail(30)
    
    # קביעת כמות פאנלים לפי המתנדים שנבחרו
    rows = 1
    row_heights = [1.0]
    
    if show_rsi: 
        rows += 1
        row_heights.append(0.3)
    if show_macd: 
        rows += 1
        row_heights.append(0.3)
    if show_mfi: 
        rows += 1
        row_heights.append(0.3)
    
    # נרמול גבהים מחדש של הפאנלים
    total_weight = sum(row_heights)
    row_heights = [h/total_weight for h in row_heights]
    
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_heights, vertical_spacing=0.07)
    
    # 1. גרף מחיר ראשי - שטח מוצלל
    fig.add_trace(go.Scatter(
        x=df_slice.index, y=df_slice['Close'], 
        line=dict(color='#E2B4BD', width=2.5), 
        fill='tozeroy', fillcolor='rgba(226, 180, 189, 0.04)',
        name='Price'
    ), row=1, col=1)
    
    # ממוצע נע 20
    fig.add_trace(go.Scatter(
        x=df_slice.index, y=df_slice['MA20'], 
        line=dict(color='#4A3E6D', width=1.5, dash='dot'), 
        name='MA20'
    ), row=1, col=1)
    
    # הוספת רצועות בולינג'ר אם נבחרו
    if show_bb:
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Upper'], line=dict(color='rgba(163, 157, 181, 0.3)', width=1, dash='dash'), name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['BB_Lower'], line=dict(color='rgba(163, 157, 181, 0.3)', width=1, dash='dash'), name='BB Lower'), row=1, col=1)
    
    # קו אנכי בדיוק על יום האיתות הנוכחי (הנר האחרון)
    fig.add_shape(type="line", x0=df_slice.index[-1], y0=df_slice['Close'].min()*0.95, x1=df_slice.index[-1], y1=df_slice['Close'].max()*1.05,
                  line=dict(color="rgba(255,255,255,0.15)", width=1.5, dash="dash"), row=1, col=1)
    
    # נקודת איתות זוהרת בסוף הגרף הראשי
    signal_color = '#4AD486' if mode == "REVERSAL" else '#F4A261'
    fig.add_trace(go.Scatter(
        x=[df_slice.index[-1]], y=[df_slice['Close'].iloc[-1]],
        mode='markers', marker=dict(color=signal_color, size=10, line=dict(color='#0A0712', width=2)),
        name='Signal'
    ), row=1, col=1)
    
    current_row = 2
    
    # 2. פאנל RSI
    if show_rsi:
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['RSI'], line=dict(color='#9B5DE5', width=1.5), name='RSI'), row=current_row, col=1)
        fig.add_shape(type="line", x0=df_slice.index[0], y0=70, x1=df_slice.index[-1], y1=70, line=dict(color="rgba(255,0,0,0.15)", width=1, dash="dash"), row=current_row, col=1)
        fig.add_shape(type="line", x0=df_slice.index[0], y0=30, x1=df_slice.index[-1], y1=30, line=dict(color="rgba(0,255,0,0.15)", width=1, dash="dash"), row=current_row, col=1)
        fig.update_yaxes(range=[10, 90], row=current_row, col=1)
        current_row += 1
        
    # 3. פאנל MACD
    if show_macd:
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MACD'], line=dict(color='#00BBF9', width=1.5), name='MACD'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MACD_Signal'], line=dict(color='#F15BB5', width=1, dash='dot'), name='Signal'), row=current_row, col=1)
        fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['MACD_Hist'], marker_color='rgba(255,255,255,0.1)', name='Hist'), row=current_row, col=1)
        current_row += 1
        
    # 4. פאנל MFI
    if show_mfi:
        fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MFI'], line=dict(color='#00F5D4', width=1.5), name='MFI'), row=current_row, col=1)
        fig.add_shape(type="line", x0=df_slice.index[0], y0=80, x1=df_slice.index[-1], y1=80, line=dict(color="rgba(255,0,0,0.15)", width=1, dash="dash"), row=current_row, col=1)
        fig.add_shape(type="line", x0=df_slice.index[0], y0=20, x1=df_slice.index[-1], y1=20, line=dict(color="rgba(0,255,0,0.15)", width=1, dash="dash"), row=current_row, col=1)
        fig.update_yaxes(range=[5, 95], row=current_row, col=1)
        current_row += 1

    # הגדרות תצוגה כלליות ונעילת מגע מלאה
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=200 + (rows * 70), margin=dict(l=10, r=10, t=10, b=10), showlegend=False, hovermode=False
    )
    
    fig.update_xaxes(showgrid=False, tickfont=dict(color='#5C5374', size=9), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor='#1A1430', tickfont=dict(color='#5C5374', size=9), side='right', fixedrange=True)
    
    return fig

# --- ממשק משתמש ראשי ---
st.markdown('<h1 class="main-title">Quantum Terminal</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">מערכת סריקה מתקדמת מבוססת קבוצות עבודה יציבות</p>', unsafe_allow_html=True)

tabs_names = ["NASDAQ א'", "NASDAQ ב'", "NASDAQ ג'", "NASDAQ ד'", "S&P500 א'", "S&P500 ב'", "DOW מלא", "MIDCAP 400"]
tabs = st.tabs(tabs_names)
sections_keys = ["NASDAQ_A", "NASDAQ_B", "NASDAQ_C", "NASDAQ_D", "SP500_A", "SP500_B", "DOW_FULL", "MIDCAP"]

for i, group_id in enumerate(sections_keys):
    with tabs[i]:
        col_ctrl, _ = st.columns([1, 2])
        with col_ctrl:
            mode = st.radio("אסטרטגיה:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}", horizontal=True)
            scan_clicked = st.button("הפעל סריקה", key=f"btn_{i}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if scan_clicked or st.session_state.get(f"results_ready_{group_id}", False):
            if scan_clicked:
                with st.spinner("מנתח מגמות שוק..."):
                    tickers = MARKET_DATA.get(group_id, [])
                    with ThreadPoolExecutor(max_workers=10) as ex:
                        results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                    st.session_state[f"data_{group_id}"] = {r[0]: r[1] for r in results if r is not None}
                    st.session_state[f"results_ready_{group_id}"] = True
                    st.session_state[f"current_mode_{group_id}"] = mode
            
            found_data = st.session_state.get(f"data_{group_id}", {})
            active_mode = st.session_state.get(f"current_mode_{group_id}", mode)
            
            if found_data:
                grid_cols = st.columns(2)
                for idx, (ticker, df_ticker) in enumerate(found_data.items()):
                    with grid_cols[idx % 2]:
                        badge_class = "badge-reversal" if active_mode == "REVERSAL" else "badge-breakout"
                        badge_text = "Reversal Signal" if active_mode == "REVERSAL" else "Breakout Signal"
                        
                        st.markdown(f"""
                            <div class="premium-card">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                                    <span class="ticker-symbol">{ticker}</span>
                                    <span class="badge {badge_class}">{badge_text}</span>
                                </div>
                                <div style="font-size: 1.1rem; font-weight: 500; color: #E6E1F3; margin-bottom: 5px;">
                                    ${df_ticker['Close'].iloc[-1]:.2f}
                                </div>
                                <div style="color: #7E7497; font-size: 0.85rem; margin-bottom: 0px;">
                                    נפח מסחר: {(df_ticker['Volume'].iloc[-1]/1e6):.2f}M
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # רובריקות בחירת מתנדים
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: bb = st.checkbox("BB", key=f"bb_{ticker}_{i}")
                        with c2: rsi = st.checkbox("RSI", key=f"rsi_{ticker}_{i}")
                        with c3: macd = st.checkbox("MACD", key=f"macd_{ticker}_{i}")
                        with c4: mfi = st.checkbox("MFI", key=f"mfi_{ticker}_{i}")
                        
                        st.plotly_chart(
                            draw_premium_chart(df_ticker, ticker, active_mode, bb, rsi, macd, mfi), 
                            use_container_width=True, 
                            config={'displayModeBar': False}
                        )
            else:
                st.info("לא אותרו הזדמנויות מסחר בקבוצה זו תחת התנאים שנבחרו.")

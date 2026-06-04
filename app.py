import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# הגדרת עמוד רחב ומראה כהה כברירת מחדל
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
    .premium-card { background: #120D24; border: 1px solid #1F173A; border-radius: 20px; padding: 24px; margin-bottom: 20px; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    .badge { padding: 6px 14px; border-radius: 30px; font-size: 0.8rem; font-weight: 600; }
    .badge-reversal { background-color: rgba(74, 212, 134, 0.12); color: #4AD486; }
    .badge-breakout { background-color: rgba(244, 162, 97, 0.12); color: #F4A261; }
    
    /* כפתור הפעלה */
    .stButton>button { background: linear-gradient(180deg, #241A42, #191230); color: #E6E1F3; border: 1px solid #33265C; border-radius: 14px; padding: 12px 28px; font-weight: 600; width: 100%; }
    .stButton>button:hover { border-color: #E2B4BD; color: #E2B4BD; }
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
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        
        if scan_type == "REVERSAL":
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker, df
        elif scan_type == "BREAKOUT":
            if df['Close'].iloc[-1] > df['High20'].iloc[-1] and df['Volume'].iloc[-1] > df['Vol20'].iloc[-1]:
                return ticker, df
    except: return None
    return None

def draw_premium_chart(df, ticker, mode):
    # ניקוי אזור הזמן מהאינדקס למניעת ValueError
    df_clean = df.copy()
    if df_clean.index.tz is not None:
        df_clean.index = df_clean.index.tz_localize(None)
        
    # לוקחים רק את 30 ימי המסחר האחרונים לתצוגה נקייה וממוקדת
    df_slice = df_clean.tail(30)
    
    # חישוב גבולות ציר ה-Y בצורה אוטומטית עם מרווח נשימה של 5%
    y_min = df_slice['Close'].min() * 0.95
    y_max = df_slice['Close'].max() * 1.05
    
    fig = go.Figure()
    
    # קו מחיר אלגנטי
    fig.add_trace(go.Scatter(
        x=df_slice.index, y=df_slice['Close'], 
        line=dict(color='#E2B4BD', width=2.5), 
        name='Price', antialias=True
    ))
    
    # ממוצע נע 20
    fig.add_trace(go.Scatter(
        x=df_slice.index, y=df_slice['MA20'], 
        line=dict(color='#4A3E6D', width=1.5, dash='dot'), 
        name='MA20'
    ))
    
    # הוספת נקודת איתות בולטת על הנר האחרון
    signal_color = '#4AD486' if mode == "REVERSAL" else '#F4A261'
    fig.add_trace(go.Scatter(
        x=[df_slice.index[-1]], y=[df_slice['Close'].iloc[-1]],
        mode='markers',
        marker=dict(color=signal_color, size=10, line=dict(color='#0A0712', width=2)),
        name='Signal'
    ))
    
    # נעילת הגרף מתקלות תנועה ומגע במובייל
    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        height=240, 
        margin=dict(l=10, r=10, t=10, b=10),
        
        # הגדרות ציר X - ביטול אינטראקציה
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(color='#5C5374', size=10),
            fixedrange=True
        ),
        
        # הגדרות ציר Y - קיבוע טווח וביטול אינטראקציה
        yaxis=dict(
            showgrid=True, 
            gridcolor='#1A1430', 
            tickfont=dict(color='#5C5374', size=10), 
            side='right',
            range=[y_min, y_max],
            fixedrange=True
        ),
        showlegend=False,
        hovermode=False # מנטרל את הפופ-אפים המציקים כשנוגעים בגרף
    )
    return fig

# --- ממשק משתמש ---
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
        
        if scan_clicked:
            with st.spinner("מנתח מגמות שוק..."):
                tickers = MARKET_DATA.get(group_id, [])
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                
                found_data = {r[0]: r[1] for r in results if r is not None}
                
                if found_data:
                    grid_cols = st.columns(2)
                    for idx, (ticker, df_ticker) in enumerate(found_data.items()):
                        with grid_cols[idx % 2]:
                            badge_class = "badge-reversal" if mode == "REVERSAL" else "badge-breakout"
                            badge_text = "Reversal Signal" if mode == "REVERSAL" else "Breakout Signal"
                            
                            st.markdown(f"""
                                <div class="premium-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                                        <span class="ticker-symbol">{ticker}</span>
                                        <span class="badge {badge_class}">{badge_text}</span>
                                    </div>
                                    <div style="font-size: 1.1rem; font-weight: 500; color: #E6E1F3; margin-bottom: 5px;">
                                        ${df_ticker['Close'].iloc[-1]:.2f}
                                    </div>
                                    <div style="color: #7E7497; font-size: 0.85rem; margin-bottom: 15px;">
                                        נפח מסחר: {(df_ticker['Volume'].iloc[-1]/1e6):.2f}M
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # שליחת ה-mode לפונקציית הציור החדשה
                            st.plotly_chart(draw_premium_chart(df_ticker, ticker, mode), use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("לא אותרו הזדמנויות מסחר בקבוצה זו תחת התנאים שנבחרו.")

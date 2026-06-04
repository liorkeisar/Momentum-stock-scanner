import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# הגדרת עמוד רחב
st.set_page_config(layout="wide", page_title="Quantum Terminal")

# --- CSS עיצוב פינטק מודרני ומזמין (בהשראת האפליקציה) ---
st.markdown("""
    <style>
    /* רקע כללי של האפליקציה */
    .stApp {
        background-color: #0E0B16;
        color: #F1EFF7;
        font-family: 'Inter', system-ui, sans-serif;
    }
    
    /* עיצוב הטאבים למעלה */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161224;
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #A39DB5;
        padding: 8px 16px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #261E3D !important;
        color: #E2B4BD !important;
        font-weight: bold;
    }
    
    /* כרטיסיות תוצאה צפות (Cards) */
    .signal-container {
        background: linear-gradient(145deg, #1C172E, #161224);
        border: 1px solid #2C2447;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    
    /* תגיות סטטוס מעוגלות */
    .badge-buy {
        background-color: rgba(74, 212, 134, 0.15);
        color: #4AD486;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-break {
        background-color: rgba(226, 180, 189, 0.15);
        color: #E2B4BD;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* כפתורים מעוצבים */
    .stButton>button {
        background: #261E3D;
        color: #F1EFF7;
        border: 1px solid #3D3061;
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: #E2B4BD;
        color: #0E0B16;
        border-color: #E2B4BD;
    }
    </style>
""", unsafe_allow_html=True)

# --- מאגר המניות המחולק לקבוצות ---
def get_sectional_tickers(section_name):
    if section_name == "NASDAQ_A":
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"]
    elif section_name == "NASDAQ_B":
        return ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"]
    elif section_name == "NASDAQ_C":
        return ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"]
    elif section_name == "NASDAQ_D":
        return ["SBAC", "ALGN", "EBAY", "SIRI", "ZBRA", "ILMN", "WBA", "JD", "BIDU", "LCID", "ZM", "MRNA", "PYPL", "INTC", "MU", "DLTR", "EXPE", "LULU"]
    elif section_name == "SP500_A":
        return ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"]
    elif section_name == "SP500_B":
        return ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG", "HON", "LOW", "SPGI", "BLK", "NOW"]
    elif section_name == "DOW_FULL":
        return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    elif section_name == "MIDCAP":
        return ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE"]
    return ["AAPL", "MSFT"]

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

def draw_clean_chart(df, ticker):
    fig = go.Figure()
    # קו מחיר חלק בגוון פסטל בהשראת האפליקציה החדשה
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#E2B4BD', width=2.5), name='Price'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#A39DB5', width=1, dash='dash'), name='MA20'))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2C2447')
    )
    return fig

# --- כותרת המערכת ---
st.write("## 🔮 Quantum Terminal")
st.write("<p style='color:#A39DB5;'>מערכת סריקה מתקדמת מבוססת קבוצות עבודה יציבות</p>", unsafe_allow_html=True)

# יצירת הטאבים
tabs = st.tabs([
    "NASDAQ א'", "NASDAQ ב'", "NASDAQ ג'", "NASDAQ ד'", 
    "S&P500 א'", "S&P500 ב'", 
    "DOW מלא", "MIDCAP 400"
])

sections = [
    ("NASDAQ_A", "נאסדק קבוצה א'"), ("NASDAQ_B", "נאסדק קבוצה ב'"), 
    ("NASDAQ_C", "נאסדק קבוצה ג'"), ("NASDAQ_D", "נאסדק קבוצה ד'"),
    ("SP500_A", "S&P קבוצה א'"), ("SP500_B", "S&P קבוצה ב'"),
    ("DOW_FULL", "דאו ג'ונס מלא"), ("MIDCAP", "מיד-קאפ 400")
]

for i, (group_id, label) in enumerate(sections):
    with tabs[i]:
        col_controls, col_space = st.columns([1, 2])
        with col_controls:
            mode = st.radio("אסטרטגיית ניתוח:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}", horizontal=True)
            scan_clicked = st.button(f"הפעל סריקה חכמה", key=f"btn_{i}")
        
        if scan_clicked:
            with st.spinner("מנתח את מגמות השוק..."):
                tickers = get_sectional_tickers(group_id)
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                
                # סינון תוצאות ריקות
                found_data = {r[0]: r[1] for r in results if r is not None}
                
                if found_data:
                    st.write("### 🎯 הזדמנויות מסחר שזוהו:")
                    
                    # הצגת התוצאות בכרטיסיות פינטק רכות
                    for ticker, df_ticker in found_data.items():
                        badge_html = f"<span class='badge-buy'>BUY / {mode}</span>" if mode == "REVERSAL" else f"<span class='badge-break'>BREAKOUT</span>"
                        
                        st.markdown(f"""
                            <div class="signal-container">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                    <span style="font-size: 1.6rem; font-weight: 700; color: #F1EFF7;">{ticker}</span>
                                    {badge_html}
                                </div>
                                <p style="color: #A39DB5; font-size: 0.9rem; margin-top: -10px;">מחיר אחרון: ${df_ticker['Close'].iloc[-1]:.2f}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # הצגת גרף נקי ומעוצב מתחת לכרטיסייה
                        st.plotly_chart(draw_clean_chart(df_ticker, ticker), use_container_width=True)
                else:
                    st.info("לא אותרו הזדמנויות מסחר העונות על הגדרות אלו כרגע בקבוצה זו.")

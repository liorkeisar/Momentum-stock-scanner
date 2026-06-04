import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# הגדרת עמוד רחב ומראה כהה כברירת מחדל
st.set_page_config(layout="wide", page_title="Terminal v2", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום מודרני (סגנון אפליקציית נייטיב) ---
st.markdown("""
    <style>
    /* הגדרות בסיס וצבעי רקע עמוקים */
    .stApp {
        background-color: #0A0712;
        color: #E6E1F3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* כותרות פרימיום */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.05rem;
        background: linear-gradient(90deg, #F1EFF7, #E2B4BD);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .sub-title {
        color: #7E7497;
        font-size: 0.95rem;
        margin-bottom: 35px;
    }
    
    /* עיצוב רשת הטאבים - הפיכה לכפתורי קפסולה מודרניים */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        padding: 0px;
        margin-bottom: 25px;
        border-bottom: 1px solid #1E1833;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #151026;
        border-radius: 20px;
        color: #938AA9;
        padding: 8px 20px;
        border: 1px solid #231B3D;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #E2B4BD !important;
        color: #0A0712 !important;
        border-color: #E2B4BD !important;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(226, 180, 189, 0.25);
    }
    
    /* כרטיסיות תוצאה (Cards) במראה צף ונקי */
    .premium-card {
        background: #120D24;
        border: 1px solid #1F173A;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 12px 32px rgba(0,0,0,0.4);
    }
    
    .ticker-symbol {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.03rem;
    }
    
    /* תגיות מעוגלות עדינות */
    .badge {
        padding: 6px 14px;
        border-radius: 30px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03rem;
    }
    .badge-reversal { background-color: rgba(74, 212, 134, 0.12); color: #4AD486; }
    .badge-breakout { background-color: rgba(244, 162, 97, 0.12); color: #F4A261; }
    
    /* עיצוב כפתור ההפעלה שייראה כמו כפתור מערכת */
    .stButton>button {
        background: linear-gradient(180deg, #241A42, #191230);
        color: #E6E1F3;
        border: 1px solid #33265C;
        border-radius: 14px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 0.9rem;
        width: 100%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        border-color: #E2B4BD;
        color: #E2B4BD;
        box-shadow: 0 4px 16px rgba(226, 180, 189, 0.1);
    }
    
    /* ביטול גבולות מיותרים של Streamlit */
    hr { border-color: #1E1833; }
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

def draw_premium_chart(df, ticker):
    fig = go.Figure()
    # קו מחיר דק ואלגנטי בצבע ורוד-פסטל נקי
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#E2B4BD', width=2), name='Price', antialias=True))
    # ממוצע נע בגוון סגול עמוק משולב ברקע
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#4A3E6D', width=1, dash='dot'), name='MA20'))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, tickfont=dict(color='#5C5374', size=10)),
        yaxis=dict(showgrid=True, gridcolor='#1A1430', tickfont=dict(color='#5C5374', size=10), side='right'),
        showlegend=False
    )
    return fig

# --- כותרת המערכת במראה נקי ---
st.markdown('<h1 class="main-title">Quantum Terminal</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">מערכת סריקה מתקדמת מבוססת קבוצות עבודה יציבות</p>', unsafe_allow_html=True)

# יצירת הטאבים (כעת מעוצבים כפתורי קפסולה)
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
        # ארגון פקדים נקי במבנה טורי קומפקטי
        col_ctrl, col_space = st.columns([1, 2])
        with col_ctrl:
            mode = st.radio("אסטרטגיה:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}", horizontal=True)
            scan_clicked = st.button(f"הפעל סריקה", key=f"btn_{i}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if scan_clicked:
            with st.spinner("מנתח מגמות שוק..."):
                tickers = get_sectional_tickers(group_id)
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                
                found_data = {r[0]: r[1] for r in results if r is not None}
                
                if found_data:
                    # יצירת רשת נקייה של 2 עמודות עבור כרטיסיות התוצאה
                    grid_cols = st.columns(2)
                    
                    for idx, (ticker, df_ticker) in enumerate(found_data.items()):
                        with grid_cols[idx % 2]:
                            badge_class = "badge-reversal" if mode == "REVERSAL" else "badge-breakout"
                            badge_text = "Reversal Signal" if mode == "REVERSAL" else "Breakout Signal"
                            
                            # הדפסת מבנה ה-Card המעוגל
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
                            
                            # הזרקת הגרף בצורה חלקה ישירות מתחת לנתוני הכרטיסייה
                            st.plotly_chart(draw_premium_chart(df_ticker, ticker), use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("לא אותרו הזדמנויות מסחר בקבוצה זו תחת התנאים שנבחרו.")

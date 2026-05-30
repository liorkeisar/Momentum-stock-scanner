import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

# הגדרות עמוד
st.set_page_config(page_title="Quantum Scanner", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# --- CSS מודרני לחלוטין ---
st.markdown("""
    <style>
    /* העלמת אלמנטים מיותרים של Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* צבע רקע ראשי של האפליקציה (כמו TradingView) */
    .stApp {
        background-color: #0B0E14;
        color: #D1D4DC;
    }
    
    /* עיצוב כותרת ראשית בסטייל ניאון */
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #00FF87 0%, #60EFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    .sub-title {
        color: #787B86;
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: -10px;
        margin-bottom: 40px;
    }
    
    /* עיצוב כרטיסיות (Tabs) מודרני */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #131722;
        border-radius: 12px;
        padding: 12px 24px;
        border: 1px solid #2A2E39;
        color: #787B86;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        border-color: #60EFFF;
        color: #D1D4DC;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2A2E39 0%, #131722 100%);
        border: 1px solid #00FF87 !important;
        color: #00FF87 !important;
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.1);
    }
    
    /* עיצוב כפתורי סריקה */
    .stButton>button {
        background: linear-gradient(135deg, #00FF87 0%, #00C853 100%);
        color: #0B0E14;
        border: none;
        border-radius: 8px;
        padding: 12px 0px;
        font-size: 1.1rem;
        font-weight: 700;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 255, 135, 0.4);
        color: #0B0E14;
    }
    
    /* עיצוב אקורדיון (Expander) */
    .streamlit-expanderHeader {
        background-color: #131722;
        border-radius: 8px;
        color: #D1D4DC;
        font-weight: 600;
        border: 1px solid #2A2E39;
    }
    div[data-testid="stExpanderDetails"] {
        background-color: #0B0E14;
        border: 1px solid #2A2E39;
        border-top: none;
        border-radius: 0 0 8px 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות עזר למשיכת מניות ---
@st.cache_data
def get_tickers(index):
    try:
        if index == "DJIA":
            return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", 
                    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", 
                    "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
        elif index == "SP500":
            return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        elif index == "NASDAQ100":
            tables = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
            for t in tables:
                if 'Ticker' in t.columns: return t['Ticker'].tolist()
                if 'Symbol' in t.columns: return t['Symbol'].tolist()
        elif index == "MIDCAP400":
            return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies')[0]['Symbol'].tolist()
    except: pass
    return ["AAPL", "MSFT", "NVDA", "TSLA"]

# --- מנוע סריקה מחמיר ---
def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 50: return None
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['Vol20'] = df['Volume'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        if scan_type == "REVERSAL":
            df['BUY'] = (df['MACD'] > df['Signal_Line']) & (df['MACD'].shift(1) <= df['Signal_Line'].shift(1)) & (df['Close'] > df['MA20'])
            df['SELL'] = (df['MACD'] < df['Signal_Line']) & (df['MACD'].shift(1) >= df['Signal_Line'].shift(1))
        elif scan_type == "BREAKOUT":
            df['BUY'] = (df['Close'] > df['High20']) & (df['Volume'] > df['Vol20'] * 2)
            df['SELL'] = (df['Close'] < df['MA20']) & (df['Close'].shift(1) >= df['MA20'].shift(1))

        if df['BUY'].iloc[-1]:
            return ticker, df
    except: return None
    return None

# --- ציור גרף מקצועי המותאם לעיצוב המודרני ---
def draw_chart(df, ticker, scan_type):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.7])

    # נרות יפניים בעיצוב נקי
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
        name='Price',
        increasing_line_color='#00FF87', increasing_fillcolor='#00FF87',
        decreasing_line_color='#FF3366', decreasing_fillcolor='#FF3366'
    ), row=1, col=1)
    
    buy_signals = df[df['BUY']]
    sell_signals = df[df['SELL']]

    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98, mode='markers+text',
                             text=['BUY'] * len(buy_signals), textposition='bottom center',
                             marker=dict(color='#00FF87', size=12, symbol='triangle-up'), name='Buy'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02, mode='markers+text',
                             text=['SELL'] * len(sell_signals), textposition='top center',
                             marker=dict(color='#FF3366', size=12, symbol='triangle-down'), name='Sell'), row=1, col=1)

    colors = ['#00FF87' if row['Close'] >= row['Open'] else '#FF3366' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    # התאמת רקע הגרף במדויק לרקע האפליקציה החדש
    fig.update_layout(
        template="plotly_dark", height=650, xaxis_rangeslider_visible=False, showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
        title=dict(text=f"{ticker} | {scan_type}", font=dict(size=22, color="#D1D4DC")),
        paper_bgcolor="#0B0E14", plot_bgcolor="#0B0E14"
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#131722', zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#131722', zeroline=False)
    return fig

# --- ממשק ראשי ---
st.markdown('<p class="main-title">Quantum Scanner</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Institutional Grade Algorithmic Detection</p>', unsafe_allow_html=True)

# דאשבורד נתונים סטטי (לעיצוב ומראה)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Status", "OPEN", "Live")
col2.metric("Scan Engines", "8 Active", "Optimized")
col3.metric("Algorithm", "Confluence V2", "Strict")
col4.metric("Latency", "1.2s", "-0.3ms")

st.write("") # מרווח

# ארגון לשוניות
tabs = st.tabs([
    "SP500 Reversal", "Dow Reversal", "Nasdaq Reversal", "MidCap Reversal", 
    "SP500 Breakout", "Dow Breakout", "Nasdaq Breakout", "MidCap Breakout"
])

def execute(index, scan_type):
    tickers = get_tickers(index)
    with st.status(f"🚀 סורק {len(tickers)} מניות בזמן אמת...", expanded=True) as status:
        st.write(f"מפעיל אלגוריתם {scan_type} על מדד {index}")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda t: run_scanner(t, scan_type), tickers))
        status.update(label="הסריקה הושלמה בהצלחה!", state="complete", expanded=False)
        
    found = False
    for res in results:
        if res:
            ticker, df = res
            with st.expander(f"🟢 זיהוי טריגר מדויק במניה: {ticker}"):
                st.plotly_chart(draw_chart(df, ticker, scan_type), use_container_width=True)
            found = True
            
    if not found: 
        st.error("לא נמצאו איתותים בשוק העונים על תנאי האלגוריתם כרגע.")

# פריסת כפתורים
with tabs[0]:
    if st.button("RUN SCANNER", key="b1"): execute("SP500", "REVERSAL")
with tabs[1]:
    if st.button("RUN SCANNER", key="b2"): execute("DJIA", "REVERSAL")
with tabs[2]:
    if st.button("RUN SCANNER", key="b3"): execute("NASDAQ100", "REVERSAL")
with tabs[3]:
    if st.button("RUN SCANNER", key="b4"): execute("MIDCAP400", "REVERSAL")

with tabs[4]:
    if st.button("RUN SCANNER", key="b5"): execute("SP500", "BREAKOUT")
with tabs[5]:
    if st.button("RUN SCANNER", key="b6"): execute("DJIA", "BREAKOUT")
with tabs[6]:
    if st.button("RUN SCANNER", key="b7"): execute("NASDAQ100", "BREAKOUT")
with tabs[7]:
    if st.button("RUN SCANNER", key="b8"): execute("MIDCAP400", "BREAKOUT")

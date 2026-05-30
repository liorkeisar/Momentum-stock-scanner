import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Quantum Scanner", layout="wide")

# --- CSS עיצוב עתידני ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Courier New', monospace; }
    .neon-title { color: #00FF9D; text-shadow: 0 0 10px #00FF9D; font-size: 3rem; text-transform: uppercase; text-align: center; }
    .stButton>button { background-color: #111; border: 1px solid #00FF9D; color: #00FF9D; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #00FF9D; color: #000; box-shadow: 0 0 20px #00FF9D; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות לוגיקה ---
@st.cache_data
def get_tickers(index):
    try:
        if index == "DJIA": return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
        elif index == "SP500": return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        elif index == "NASDAQ100": return pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[0]['Ticker'].tolist()
        elif index == "MIDCAP400": return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies')[0]['Symbol'].tolist()
    except: return ["AAPL", "MSFT", "NVDA"]

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
        if df['BUY'].iloc[-1]: return ticker, df
    except: return None
    return None

def draw_chart(df, ticker, scan_type):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])
    # נרות ו-MA20
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='yellow', width=1.5), name='MA20'), row=1, col=1)
    
    # איתותים עם מחירי כניסה/יציאה
    buy = df[df['BUY']]
    sell = df[df['SELL']]
    fig.add_trace(go.Scatter(x=buy.index, y=buy['Low'], mode='markers+text', text=buy['Close'].round(2), textposition='bottom center', marker=dict(color='lime', size=12, symbol='triangle-up'), name='BUY'), row=1, col=1)
    fig.add_trace(go.Scatter(x=sell.index, y=sell['High'], mode='markers+text', text=sell['Close'].round(2), textposition='top center', marker=dict(color='red', size=12, symbol='triangle-down'), name='SELL'), row=1, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='cyan', width=1), name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], line=dict(color='magenta', width=1), name='Signal'), row=2, col=1)
    
    # Volume
    colors = ['lime' if r['Close'] >= r['Open'] else 'red' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=800, paper_bgcolor="#050505", plot_bgcolor="#050505", margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- ממשק ---
st.markdown('<h1 class="neon-title">QUANTUM SCANNER</h1>', unsafe_allow_html=True)
tabs = st.tabs(["SP500 REV", "DOW REV", "NASD REV", "MIDC REV", "SP500 BRK", "DOW BRK", "NASD BRK", "MIDC BRK"])

def execute(idx, scn):
    tickers = get_tickers(idx)
    with st.spinner("סורק..."):
        with ThreadPoolExecutor(max_workers=5) as ex: results = list(ex.map(lambda t: run_scanner(t, scn), tickers))
        for res in results:
            if res:
                with st.expander(f"✅ SIGNAL: {res[0]}"): st.plotly_chart(draw_chart(res[1], res[0], scn), use_container_width=True)

# כפתורים ללשוניות
for i, (idx, scn) in enumerate([("SP500", "REVERSAL"), ("DJIA", "REVERSAL"), ("NASDAQ100", "REVERSAL"), ("MIDCAP400", "REVERSAL"), ("SP500", "BREAKOUT"), ("DJIA", "BREAKOUT"), ("NASDAQ100", "BREAKOUT"), ("MIDCAP400", "BREAKOUT")]):
    with tabs[i]:
        if st.button(f"EXECUTE SCAN", key=f"b{i}"): execute(idx, scn)

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- CSS עיצוב תיבות בסגנון נטפליקס ---
st.markdown("""
    <style>
    .card { background-color: #161A23; border-radius: 12px; padding: 15px; border: 1px solid #2A2E39; margin: 5px; }
    .ticker-name { font-size: 1.2rem; font-weight: bold; color: #00FF9D; }
    .status-tag { background: #00C853; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות (לוגיקה נשארת זהה למה שעבד) ---
@st.cache_data
def get_tickers(index):
    # (החזרתי את הפונקציה המלאה שלך)
    if index == "DJIA": return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    if index == "SP500": return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    if index == "NASDAQ100": return pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[0]['Ticker'].tolist()
    if index == "MIDCAP400": return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies')[0]['Symbol'].tolist()
    return ["AAPL", "MSFT"]

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 50: return None
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        if scan_type == "REVERSAL":
            df['BUY'] = (df['MACD'] > df['Signal_Line']) & (df['MACD'].shift(1) <= df['Signal_Line'].shift(1)) & (df['Close'] > df['MA20'])
        else:
            df['BUY'] = (df['Close'] > df['High20']) & (df['Volume'] > df['Vol20'] * 2)
            
        if df['BUY'].iloc[-1]: return ticker, df
    except: return None
    return None

# --- ממשק עם טאבים וסורקים ---
st.title("⚡ Quantum Terminal")
tabs = st.tabs(["SP500 REV", "DOW REV", "NASD REV", "MIDC REV", "SP500 BRK", "DOW BRK", "NASD BRK", "MIDC BRK"])

def execute(index, scan_type):
    tickers = get_tickers(index)
    with st.spinner(f"סורק {index}..."):
        with ThreadPoolExecutor(max_workers=10) as ex: results = list(ex.map(lambda t: run_scanner(t, scan_type), tickers))
        
        # סינון תוצאות
        found = [r for r in results if r]
        
        if not found:
            st.warning("לא נמצאו איתותים.")
            return

        # הצגה בתיבות נטפליקס
        cols = st.columns(4)
        for i, res in enumerate(found):
            with cols[i % 4]:
                st.markdown(f"""<div class="card"><div class="ticker-name">{res[0]} <span class="status-tag">BUY</span></div></div>""", unsafe_allow_html=True)
                if st.button(f"גרף {res[0]}", key=f"{res[0]}_{i}"):
                    st.line_chart(res[1]['Close'])

# קישור הטאבים לסורקים
params = [("SP500", "REVERSAL"), ("DJIA", "REVERSAL"), ("NASDAQ100", "REVERSAL"), ("MIDCAP400", "REVERSAL"), 
          ("SP500", "BREAKOUT"), ("DJIA", "BREAKOUT"), ("NASDAQ100", "BREAKOUT"), ("MIDCAP400", "BREAKOUT")]

for i, (idx, scn) in enumerate(params):
    with tabs[i]:
        if st.button(f"הפעל סריקת {idx}", key=f"btn_{i}"): execute(idx, scn)

import streamlit as st
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Multi-Strategy Scanner")

# --- טעינת רשימת מניות ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].dropna().unique().tolist()
        return [str(t) for t in tickers if len(str(t)) < 6 and str(t).isalpha()]
    except:
        return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- לוגיקת הסריקה ---
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        # שליפת סקטור
        info = stock.info
        sector = info.get('sector', 'Unknown')
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # אסטרטגיה 1: מניות במחיר מציאה
        if mode == "מציאה":
            if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
                return ticker, df, 100, sector
        
        # אסטרטגיה 2: פריצות
        elif mode == "פריצה":
            if df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
                score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
                return ticker, df, score, sector
    except: return None
    return None

# --- ממשק משתמש ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")
tab1, tab2 = st.tabs(["📉 מניות במחיר מציאה", "🚀 מניות לפני פריצה"])

def process_scan(mode):
    tickers = get_universe()
    progress_bar = st.progress(0)
    results = {}
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = (res[1], res[2], res[3])
            progress_bar.progress((i + 1) / len(tickers))
    return dict(sorted(results.items(), key=lambda item: item[1][1], reverse=True))

# תצוגת לשוניות
with tab1:
    if st.button("סרוק מציאות"):
        st.session_state['res_val'] = process_scan("מציאה")
    if 'res_val' in st.session_state:
        for t, (df, s, sec) in st.session_state['res_val'].items():
            st.write(f"---")
            st.write(f"**מניה:** {t} | **סקטור:** {sec}")

with tab2:
    if st.button("סרוק פריצות"):
        st.session_state['res_brk'] = process_scan("פריצה")
    if 'res_brk' in st.session_state:
        for t, (df, s, sec) in st.session_state['res_brk'].items():
            st.write(f"---")
            st.write(f"**מניה:** {t} | **סקטור:** {sec} | **ציון פריצה:** {s}/100")

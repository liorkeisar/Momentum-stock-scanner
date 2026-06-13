import streamlit as st
import yfinance as yf
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

# הגדרת מטמון למניעת חסימות מ-Yahoo
class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

st.set_page_config(layout="wide", page_title="TITAN: Multi-Strategy Scanner")

# --- טעינת רשימת מניות ---
@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].dropna().unique().tolist()
        return [str(t) for t in tickers if len(str(t)) < 6 and str(t).isalpha()]
    except:
        return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- לוגיקת הסריקה ---
def run_scanner(ticker, mode):
    try:
        # השהייה מזערית למניעת חסימת IP
        time.sleep(0.1)
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="300d")
        
        # סינון בסיסי: מניה וותיקה עם נזילות
        if len(df) < 200 or df['Volume'].rolling(20).mean().iloc[-1] < 200000: return None
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        
        # אסטרטגיה 1: מציאה (ירידה מתונה יותר ו-BB רחב יותר)
        if mode == "מציאה":
            is_dropped = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.15
            if is_dropped.iloc[-1] and df['BB_Width'].iloc[-1] < 25:
                return ticker, 100
        
        # אסטרטגיה 2: פריצות
        elif mode == "פריצה":
            if df['BB_Width'].iloc[-1] < 25 and df['RVOL'].iloc[-1] > 1.2:
                score = min(100, int((25 - df['BB_Width'].iloc[-1]) * 2 + (df['RVOL'].iloc[-1] * 10)))
                return ticker, score
    except: return None
    return None

# --- ממשק משתמש ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")
tab1, tab2 = st.tabs(["📉 מניות במחיר מציאה", "🚀 מניות לפני פריצה"])

def process_scan(mode):
    tickers = get_universe()[:500] # מתחילים ב-500 כדי לשמור על מהירות
    progress_bar = st.progress(0)
    results = {}
    
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = res[1]
            progress_bar.progress((i + 1) / len(tickers))
            
    return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))

with tab1:
    if st.button("סרוק מציאות"):
        st.session_state['res_val'] = process_scan("מציאה")
    if 'res_val' in st.session_state:
        for t, s in st.session_state['res_val'].items():
            st.write(f"---")
            st.write(f"**מניה:** {t} | **ציון:** {s}")

with tab2:
    if st.button("סרוק פריצות"):
        st.session_state['res_brk'] = process_scan("פריצה")
    if 'res_brk' in st.session_state:
        for t, s in st.session_state['res_brk'].items():
            st.write(f"---")
            st.write(f"**מניה:** {t} | **ציון פריצה:** {s}/100")

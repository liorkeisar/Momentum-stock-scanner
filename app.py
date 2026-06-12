import streamlit as st
import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# --- טעינה ---
@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- לוגיקה חסינה מתקלות ---
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        # חישובים - בדיוק כמו בגרסה שעבדה לך
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # ניסיון בטוח לשלוף סקטור (אם נכשל, נחזיר 'Unknown')
        try:
            sector = stock.info.get('sector', 'Unknown')
        except:
            sector = 'Unknown'
        
        # לוגיקה שהוכחה כעובדת
        if mode == "מציאה":
            if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
                return {'Ticker': ticker, 'Score': 100, 'Sector': sector}
        
        elif mode == "פריצה":
            if df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
                score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
                return {'Ticker': ticker, 'Score': score, 'Sector': sector}
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: Persistent Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def process_and_save(mode, filename):
    tickers = get_universe()
    results = []
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = [ex.submit(run_scanner, t, mode) for t in tickers]
        for f in futures:
            res = f.result()
            if res: results.append(res)
    
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)
    st.session_state[mode] = df
    return df

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        st.session_state[mode] = process_and_save(mode, filename)
    
    # טעינה בטוחה מהקובץ
    if mode not in st.session_state and os.path.exists(filename):
        st.session_state[mode] = pd.read_csv(filename)
    
    if mode in st.session_state:
        df = st.session_state[mode]
        if not df.empty:
            st.metric("סה\"כ נמצאו", len(df))
            st.dataframe(df, use_container_width=True)
        else:
            st.write("לא נמצאו תוצאות.")
            
        if st.button(f"נקה נתוני {mode}"):
            if os.path.exists(filename): os.remove(filename)
            if mode in st.session_state: del st.session_state[mode]
            st.rerun()

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")

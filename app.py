import streamlit as st
import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor

# הגדרת דף רחב
st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# --- פונקציית טעינת מניות ---
@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except:
        return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- מנוע הסריקה ---
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000:
            return None
        
        # חישובים טכניים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        sector = stock.info.get('sector', 'Unknown')
        
        # לוגיקה - מציאות
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 12:
            return {'Ticker': ticker, 'Score': 100, 'Sector': sector}
        
        # לוגיקה - פריצות
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
            return {'Ticker': ticker, 'Score': score, 'Sector': sector}
    except:
        return None
    return None

# --- ממשק משתמש ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def handle_tab(mode, file_name):
    # כפתור סריקה
    if st.button(f"סרוק מניות - {mode}"):
        with st.spinner("סורק את כל השוק, נא להמתין..."):
            results = []
            with ThreadPoolExecutor(max_workers=50) as ex:
                futures = [ex.submit(run_scanner, t, mode) for t in get_universe()]
                for f in futures:
                    res = f.result()
                    if res: results.append(res)
            
            if results:
                df_res = pd.DataFrame(results)
                df_res.to_csv(file_name, index=False)
                st.session_state[mode] = df_res
            else:
                st.warning("לא נמצאו מניות בתנאים אלו כרגע.")

    # טעינה אוטומטית אם קיים קובץ
    if mode not in st.session_state and os.path.exists(file_name):
        st.session_state[mode] = pd.read_csv(file_name)
    
    # הצגת הטבלה
    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)
        if st.button(f"🗑️ נקה תוצאות {mode}", key=f"clear_{mode}"):
            if os.path.exists(file_name): os.remove(file_name)
            if mode in st.session_state: del st.session_state[mode]
            st.rerun()

with tab1: handle_tab("מציאה", "res_val.csv")
with tab2: handle_tab("פריצה", "res_brk.csv")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: ATR Professional & Value")

# --- פונקציות עזר ---
@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            if 'Symbol' in df.columns:
                return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
        except Exception as e:
            st.sidebar.error(f"שגיאה בקריאת הקובץ: {e}")
    return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252: return None
        
        info = stock.info
        curr_price = df['Close'].iloc[-1]
        
        # לוגיקת "ערך עמוק" (Graham Number)
        if mode == "ערך עמוק":
            eps = info.get('trailingEps', 0)
            bvps = info.get('bookValue', 0)
            graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
            if graham_num > curr_price * 1.2: # מחיר נמוך ב-20% מהערך ההוגן
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'FairValue': round(graham_num, 2), 'Upside%': round(((graham_num/curr_price)-1)*100, 2)}
            return None

        # לוגיקת ניתוח טכני (מציאה/פריצה)
        if df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        atr = calculate_atr(df)
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))}
    except: return None
    return None

# --- ממשק משתמש ---
st.title("🛡️ TITAN: Pro Scanner & Value Finder")
tab1, tab2, tab3 = st.tabs(["📉 מציאות", "🚀 פריצות", "💎 ערך עמוק"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק מניות..."):
            universe = get_universe()
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(filter(None, ex.map(lambda t: run_scanner(t, mode), universe)))
            
            if results:
                df = pd.DataFrame(results)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות.")

    if mode not in st.session_state and os.path.exists(filename):
        st.session_state[mode] = pd.read_csv(filename)
    
    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)
        st.download_button(f"📥 הורד אקסל {mode}", data=st.session_state[mode].to_csv(index=False), file_name=f"{mode}.csv")

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
with tab3: render_tab("ערך עמוק", "res_val_deep.csv")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# פונקציית טעינת מניות מהקובץ המקומי
@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            if 'Symbol' in df.columns:
                return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
        except: pass
    return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if len(df) < 200: return None
        
        curr_price = df['Close'].iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        rvol = (df['Volume'] / df['Volume'].rolling(20).mean()).iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - curr_price) / df['High'].rolling(252).max()) > 0.25
        
        info = stock.info
        eps = info.get('trailingEps', 0)
        bvps = info.get('bookValue', 0)
        graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0

        if mode == "מציאה" and is_dropped and bb_width < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        elif mode == "פריצה" and bb_width < 15 and rvol > 1.2:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': min(100, int((15-bb_width)*3 + (rvol*20)))}
        elif mode == "ערך עמוק" and graham_num > curr_price * 1.2:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'FairValue': round(graham_num, 2), 'Upside%': round(((graham_num/curr_price)-1)*100, 2)}
    except: return None
    return None

st.title("🛡️ TITAN: Advanced Scanner with Auto-Save")
tab1, tab2, tab3 = st.tabs(["📉 מציאות", "🚀 פריצות", "💎 ערך עמוק"])

def render_tab(mode):
    filename = f"{mode}_saved.csv"
    
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(filter(None, ex.map(lambda t: run_scanner(t, mode), get_universe())))
            
            if results:
                df = pd.DataFrame(results)
                df.to_csv(filename, index=False) # שמירה אוטומטית לקובץ
                st.dataframe(df, use_container_width=True)
            else: st.warning("לא נמצאו מניות.")
    
    # טעינה אוטומטית אם יש קובץ שמור
    elif os.path.exists(filename):
        st.write(f"📂 נתונים אחרונים עבור {mode}:")
        st.dataframe(pd.read_csv(filename), use_container_width=True)

with tab1: render_tab("מציאה")
with tab2: render_tab("פריצה")
with tab3: render_tab("ערך עמוק")

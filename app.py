import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# 1. פונקציית טעינת מניות
@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            return df['Symbol'].dropna().unique().tolist()
        except: pass
    return ["AAPL", "NVDA", "MSFT"]

# 2. מנוע סריקה משולב (טכני + שווי הוגן)
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if len(df) < 200: return None
        curr_price = df['Close'].iloc[-1]
        
        # חישוב שווי הוגן (גרהאם) מבוסס על נתוני דוחות (EPS ו-BVPS)
        # שימוש ב-info בצורה בטוחה רק בתוך try/except קטן
        try:
            info = stock.info
            eps = info.get('trailingEps', 0)
            bvps = info.get('bookValue', 0)
            graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
        except: graham_num = 0

        # לוגיקת "ערך עמוק"
        if mode == "ערך עמוק":
            if graham_num > curr_price * 1.2: 
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'FairValue': round(graham_num, 2), 'Upside%': round(((graham_num/curr_price)-1)*100, 2)}
            return None

        # לוגיקה טכנית (מציאה/פריצה)
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - curr_price) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and is_dropped and bb_width < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        elif mode == "פריצה" and bb_width < 15:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 80}
    except: return None
    return None

# 3. ממשק
st.title("🛡️ TITAN: Pro Scanner & Value Finder")
tab1, tab2, tab3 = st.tabs(["📉 מציאות", "🚀 פריצות", "💎 ערך עמוק"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק נתונים..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(filter(None, ex.map(lambda t: run_scanner(t, mode), get_universe())))
            if results:
                df = pd.DataFrame(results).sort_values(by=list(results[0].keys())[-1], ascending=False)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות.")

    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
with tab3: render_tab("ערך עמוק", "res_deep.csv")

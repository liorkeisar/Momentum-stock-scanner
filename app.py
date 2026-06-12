import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Scanner with Save")

@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    return []

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        if mode == "ערך עמוק":
            info = stock.info
            curr_price = info.get('currentPrice', 0)
            eps = info.get('trailingEps', 0)
            bvps = info.get('bookValue', 0)
            graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
            if graham_num > curr_price * 1.2:
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'FairValue': round(graham_num, 2), 'Upside%': round(((graham_num/curr_price)-1)*100, 2)}
            return None

        df = stock.history(period="300d")
        if len(df) < 200 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        curr_price = df['Close'].iloc[-1]
        
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean()
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and is_dropped.iloc[-1] and bb_width.iloc[-1] < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        elif mode == "פריצה" and bb_width.iloc[-1] < 15:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 80}
    except: return None
    return None

st.title("🛡️ TITAN: Nasdaq Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "פריצה", "ערך עמוק"], horizontal=True)
filename = f"results_{mode}.csv"

if st.button("התחל סריקה"):
    universe = get_universe()
    progress_bar = st.progress(0)
    results = []
    
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in universe}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results.append(res)
            progress_bar.progress((i + 1) / len(universe))
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False) # שמירה לקובץ
        st.session_state[mode] = df
        st.success(f"הסריקה נשמרה לקובץ: {filename}")
    else:
        st.warning("לא נמצאו מניות.")

# טעינה מהזיכרון או מהקובץ אם קיים
if mode not in st.session_state and os.path.exists(filename):
    st.session_state[mode] = pd.read_csv(filename)

if mode in st.session_state:
    st.dataframe(st.session_state[mode], use_container_width=True)
    st.download_button(f"📥 הורד את תוצאות {mode}", data=st.session_state[mode].to_csv(index=False), file_name=filename)

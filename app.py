import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Full Scanner with Value")

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
        
        # לוגיקת שווי הוגן (גרהאם)
        if mode == "ערך עמוק":
            # שליפת נתונים פונדמנטליים בצורה בטוחה
            info = stock.info
            eps = info.get('trailingEps', 0)
            bvps = info.get('bookValue', 0)
            # נוסחת גרהאם: sqrt(22.5 * EPS * BVPS)
            graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
            
            # בדיקה אם המחיר הנוכחי נמוך מהערך ההוגן
            curr_price = info.get('currentPrice', 0)
            if graham_num > curr_price * 1.2: # מרווח ביטחון של 20%
                return {
                    'Ticker': ticker, 
                    'Price': round(curr_price, 2), 
                    'FairValue': round(graham_num, 2), 
                    'Upside%': round(((graham_num/curr_price)-1)*100, 2)
                }
            return None

        # לוגיקה טכנית (עבור מציאה ופריצה)
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

# ממשק משתמש
st.title("🛡️ TITAN: Nasdaq Pro Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "פריצה", "ערך עמוק"], horizontal=True)

if st.button("התחל סריקה מלאה"):
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
        st.success(f"נמצאו {len(results)} מניות.")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.warning("לא נמצאו מניות בתנאים אלו. נסה מצב אחר.")

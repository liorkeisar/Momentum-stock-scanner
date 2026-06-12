import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

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
        # משיכה אחת של היסטוריה כדי לחסוך קריאות
        df = stock.history(period="1y")
        if len(df) < 250: return None
        
        curr_price = df['Close'].iloc[-1]
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        
        # סינון איכות מקצועי (רק מניות מעל ממוצע 200 יום)
        if curr_price < ma200: return None
        
        # 1. אסטרטגיית שווי הוגן (יציבה יותר)
        if mode == "ערך עמוק":
            info = stock.info
            # מחפשים מניות עם PE נמוך וערך ספרתי גבוה (Value)
            pe = info.get('trailingPE', 999)
            if 0 < pe < 15: # מכפיל רווח בין 0 ל-15 נחשב זול
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'PE_Ratio': round(pe, 2)}
            return None

        # 2. אסטרטגיה טכנית (סינון מחמיר ל-700 המניות)
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        rvol = df['Volume'].iloc[-1] / vol_avg
        bb_width = (df['Close'].rolling(20).std() * 4 / df['Close'].rolling(20).mean()) * 100
        
        # מציאה: ירידה חדה וסחיטה של הרצועות (פחות מ-5% רוחב)
        if mode == "מציאה" and bb_width < 5:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        
        # פריצה: נפח מסחר פי 2.5 מהממוצע + תנודתיות נמוכה
        if mode == "פריצה" and rvol > 2.5 and bb_width < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 80}
            
    except: return None
    return None

# ממשק
st.title("🛡️ TITAN: Elite Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "פריצה", "ערך עמוק"], horizontal=True)

if st.button("סרוק"):
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
        st.dataframe(pd.DataFrame(results).head(50), use_container_width=True) # מציג רק 50 הכי חזקות
    else:
        st.warning("לא נמצאו מניות איכותיות בתנאים אלו.")

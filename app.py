import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# הגדרות עמוד
st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner & Value Finder")

# רשימת מניות לדוגמה - ניתן להרחיב לפי הצורך
@st.cache_data(ttl=3600)
def get_universe():
    return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "AMZN", "META", "GOOGL", "NFLX", "AVGO", "INTC", "CSCO", "PEP", "KO", "JPM"]

# פונקציית סריקה מרכזית
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        info = stock.info
        if len(df) < 200: return None
        
        curr_price = df['Close'].iloc[-1]
        
        # חישוב ערך גרהאם (Graham Number) ללשונית ערך
        eps = info.get('trailingEps', 0)
        bvps = info.get('bookValue', 0)
        graham_num = np.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
        
        # לוגיקה ללשונית "ערך עמוק"
        if mode == "ערך עמוק":
            if graham_num > curr_price * 1.2: # מחיר נמוך ב-20% לפחות מהערך ההוגן
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'FairValue': round(graham_num, 2), 'Upside%': round(((graham_num/curr_price)-1)*100, 2)}
            return None

        # לוגיקה ללשוניות טכניות (מציאה/פריצה)
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        rvol = (df['Volume'] / df['Volume'].rolling(20).mean()).iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - curr_price) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and is_dropped and bb_width < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        elif mode == "פריצה" and bb_width < 15 and rvol > 1.2:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': min(100, int((15-bb_width)*3 + (rvol*20)))}
            
    except: return None
    return None

# ממשק משתמש
st.title("🛡️ TITAN: Advanced Professional Scanner")
tab1, tab2, tab3 = st.tabs(["📉 מציאות", "🚀 פריצות", "💎 ערך עמוק"])

def render_tab(mode):
    if st.button(f"סרוק מניות - {mode}"):
        with st.spinner("מנתח נתונים (טכני + פונדמנטלי)..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(filter(None, ex.map(lambda t: run_scanner(t, mode), get_universe())))
            
            if results:
                df = pd.DataFrame(results).sort_values(by=list(results[0].keys())[-1], ascending=False)
                st.dataframe(df, use_container_width=True) # הצגה יציבה ללא סטייל שגורם לקריסה
            else: 
                st.warning("לא נמצאו מניות העונות על הקריטריונים.")

with tab1: render_tab("מציאה")
with tab2: render_tab("פריצה")
with tab3: render_tab("ערך עמוק")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Debug Scanner")

def get_universe():
    filename = "nasdaq_screener.csv"
    # בדיקת קיום קובץ
    if not os.path.exists(filename):
        st.error(f"⚠️ הקובץ {filename} לא נמצא בתיקייה!")
        return ["AAPL", "NVDA", "MSFT"] # רשימת חירום

    try:
        df = pd.read_csv(filename)
        st.write(f"✅ הקובץ נטען. עמודות שנמצאו: {list(df.columns)}")
        
        # חיפוש העמודה הנכונה (לפעמים השם שונה)
        target_col = 'Symbol' if 'Symbol' in df.columns else df.columns[0]
        st.write(f"🔍 משתמש בעמודה: {target_col}")
        
        symbols = df[target_col].dropna().unique().tolist()
        return [str(t) for t in symbols if len(str(t)) < 6 and str(t).isalpha()]
    except Exception as e:
        st.error(f"❌ שגיאה בקריאת הקובץ: {e}")
        return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="100d") # צמצום ל-100 ימים לזיהוי מהיר
        if len(df) < 50: return None
        
        curr_price = df['Close'].iloc[-1]
        
        # לוגיקה פשוטה לבדיקת תקינות
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        
        if mode == "מציאה":
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 50}
    except: return None

# --- ממשק ---
st.title("🛡️ TITAN: Scanner Debugger")
if st.button("בצע סריקה מהירה"):
    universe = get_universe()
    st.write(f"🚀 מתחיל לסרוק {len(universe)} מניות...")
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(filter(None, ex.map(lambda t: run_scanner(t, "מציאה"), universe[:20]))) # רק 20 ראשונות לניסיון
    
    if results:
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("עדיין לא נמצאו מניות.")

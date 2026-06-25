import streamlit as st
import yfinance as yf
import pandas as pd
import os

# הגדרות עמוד
st.set_page_config(page_title="KEISAR Scanner", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'

# עיצוב כותרת קטנה יותר
st.markdown("### ◈ KEISAR Scanner")

# פונקציית סינון (ללא שינוי בלוגיקה)
def get_indicators(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info.get('marketCap', 0) < 300_000_000: return None
        if info.get('averageVolume', 0) < 200_000: return None
        
        target_price = info.get('targetMeanPrice')
        current_price = info.get('currentPrice')
        if target_price and current_price and current_price > (target_price * 0.70): return None
        
        df = stock.history(period="1y")
        if df is None or len(df) < 252: return None
        
        yearly_low = df['Close'].min()
        if current_price > (yearly_low * 1.30): return None
        return True
    except: return None

# תפריט צד להגדרות
with st.sidebar:
    st.header("הגדרות סריקה")
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.multiselect("בחר רשימות:", all_files)
    run_btn = st.button("🚀 הפעל סריקה")

# לוגיקת סריקה
if run_btn:
    if not selected_files:
        st.error("בחר רשימה מהתפריט.")
    else:
        all_tickers = list(set([t for f in selected_files for t in pd.read_csv(f, header=None).iloc[:, 0].dropna()]))
        my_bar = st.progress(0, text="מתחיל סריקה...")
        master_list = []
        
        for i, ticker in enumerate(all_tickers):
            if get_indicators(ticker):
                master_list.append({"Ticker": ticker})
            my_bar.progress((i + 1) / len(all_tickers), text=f"סורק: {ticker}")
            
        if master_list:
            pd.DataFrame(master_list).to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()
        else:
            st.warning("לא נמצאו מניות.")

# הצגת תוצאות
if os.path.exists(SCAN_RESULTS_FILE):
    st.dataframe(pd.read_csv(SCAN_RESULTS_FILE), use_container_width=True)

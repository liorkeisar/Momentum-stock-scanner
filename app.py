import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# הגדרות
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# פונקציות ליבה
@st.cache_data(ttl=3600)
def get_data(ticker):
    try: return yf.Ticker(ticker).history(period="6mo")
    except: return pd.DataFrame()

def get_indicators(df):
    if df.empty or len(df) < 30: return None
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    return df.fillna(0)

def add_to_portfolio(ticker, price):
    hist = yf.Ticker(ticker).history(period="1mo")
    atr = float(hist['High'].iloc[-1] - hist['Low'].iloc[-1])
    sl = round(price - (2 * atr), 2)
    tp = round(price + (4 * atr), 2)
    rr = round((tp - price) / (price - sl), 2)
    
    new_row = pd.DataFrame({'Ticker': [ticker], 'Entry': [price], 'SL': [sl], 'TP': [tp], 'R:R': [rr]})
    
    if os.path.exists(PORTFOLIO_FILE):
        port = pd.read_csv(PORTFOLIO_FILE)
        if ticker in port['Ticker'].values: return False, "כבר קיים"
        new_row.to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
    else:
        new_row.to_csv(PORTFOLIO_FILE, index=False)
    return True, "נוספה בהצלחה"

# ממשק
st.title("◈ KEISAR Pro Hunter")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק"])

with tab1:
    all_csv = [f for f in os.listdir('.') if f.endswith('.csv') and f not in [PORTFOLIO_FILE, SCAN_RESULTS_FILE]]
    selected = st.multiselect("בחר רשימות:", all_csv, default=all_csv)
    
    if st.button("🚀 סרוק"):
        master = []
        with st.spinner("סורק..."):
            for file in selected:
                for t in pd.read_csv(file, header=None).iloc[:, 0].dropna().unique():
                    df = get_indicators(get_data(t))
                    if df is not None:
                        # כאן נוצרת המניה. וודא שחישוב ה-Score קיים
                        master.append({"Ticker": t, "Score": 1, "Price": round(float(df['Close'].iloc[-1]), 2)})
        
        # פתרון ה-KeyError: בדיקה אם הרשימה לא ריקה
        if master:
            df_final = pd.DataFrame(master)
            df_final.sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()
        else:
            st.warning("לא נמצאו מניות העומדות בתנאים.")

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res)
        ticker = st.selectbox("בחר מניה:", df_res['Ticker'])
        if st.button("➕ הוסף"):
            price = df_res[df_res['Ticker']==ticker]['Price'].iloc[0]
            succ, msg = add_to_portfolio(ticker, price)
            if succ: st.success(msg)

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_p = pd.read_csv(PORTFOLIO_FILE)
        st.dataframe(df_p)
        to_del = st.selectbox("בחר מניה למחיקה:", df_p['Ticker'].unique())
        if st.button("❌ מחק"):
            df_p[df_p['Ticker'] != to_del].to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
    else:
        st.info("התיק ריק")

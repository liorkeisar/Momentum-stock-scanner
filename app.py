import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np
from datetime import datetime

# הגדרות כלליות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- פונקציות חישוב ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    return yf.Ticker(ticker).history(period="6mo")

def get_market_status():
    spy = yf.Ticker("SPY").history(period="1y")
    spy['MA200'] = spy['Close'].rolling(window=200).mean()
    return spy['Close'].iloc[-1] > spy['MA200'].iloc[-1]

def get_indicators(df):
    df = df.copy()
    df['Daily_Change'] = df['Close'].pct_change()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['AvgVol'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['AvgVol']
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    if df['Daily_Change'].iloc[-1] < -0.05: return -1
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    elif df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק מוסדי מקצועי")
if not get_market_status():
    st.warning("⚠️ אזהרת מערכת: השוק (SPY) מתחת ל-MA200.")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    st.sidebar.header("⚙️ הגדרות סריקה")
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files, default=all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        alerts = [] # רשימת התראות פנימית
        
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                if len(df) > 50:
                    score = calculate_score(df)
                    if score >= 0:
                        master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
                        # לוגיקת התראה פנימית
                        if score == 5 and df['RVOL'].iloc[-1] > 1.5:
                            alerts.append(f"🔥 איתות חם: {ticker} בציון 5 ו-RVOL גבוה!")
            except: continue
            progress_bar.progress((i + 1) / len(all_tickers))
        
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.session_state['alerts'] = alerts # שמירת התראות בזיכרון הממשק
        st.rerun()

    # הצגת התראות אם קיימות
    if 'alerts' in st.session_state and st.session_state['alerts']:
        st.error("🚨 מרכז התראות בזמן אמת:")
        for alert in st.session_state['alerts']:
            st.write(alert)

    if os.path.exists(SCAN_RESULTS_FILE):
        st.dataframe(pd.read_csv(SCAN_RESULTS_FILE), use_container_width=True)
        # ... (שאר הקוד לניתוח והוספה לתיק נשאר זהה) ...

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
    try:
        spy = yf.Ticker("SPY").history(period="1y")
        spy['MA200'] = spy['Close'].rolling(window=200).mean()
        return spy['Close'].iloc[-1] > spy['MA200'].iloc[-1]
    except: return True

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
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
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
    # מיון קבצים בסדר עולה
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f])
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        alerts = []
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                if len(df) > 20:
                    score = calculate_score(df)
                    if score >= 0:
                        master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
            except: continue
            progress_bar.progress((i + 1) / len(all_tickers))
        
        if master_list:
            pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        
        if st.button("הצג ניתוח"):
            st.session_state['selected_ticker'] = selected
            st.rerun()
            
        if 'selected_ticker' in st.session_state:
            ticker = st.session_state['selected_ticker']
            data = get_indicators(get_data(ticker))
            last_price = float(data['Close'].iloc[-1])
            atr = float(data['ATR'].iloc[-1])
            sl, tp = round(last_price - (1.5 * atr), 2), round(last_price + (3.0 * atr), 2)
            
            st.subheader(f"📊 ניתוח טכני: {ticker}")
            st.write(f"מחיר: ${last_price:.2f} | SL: ${sl:.2f} | TP: ${tp:.2f}")
            
            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [ticker], 'Entry': [last_price], 'SL': [sl], 'TP': [tp]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוסף לתיק!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE) and os.path.getsize(PORTFOLIO_FILE) > 0:
        try:
            df_port = pd.read_csv(PORTFOLIO_FILE)
            for i, row in df_port.iterrows():
                col1, col2 = st.columns([0.8, 0.2])
                curr_p = float(get_data(row['Ticker'])['Close'].iloc[-1])
                col1.write(f"**{row['Ticker']}** | כניסה: ${row['Entry']} | נוכחי: ${curr_p:.2f}")
                if col2.button("🗑️ הסר", key=f"del_{i}"):
                    df_port.drop(i).to_csv(PORTFOLIO_FILE, index=False)
                    st.rerun()
        except: os.remove(PORTFOLIO_FILE); st.rerun()

with tab3:
    st.header("🎓 מדריך אסטרטגי")
    st.write("השתמש בסורק כדי למצוא מניות עם ציון גבוה (Squeeze נמוך ו-RVOL גבוה).")

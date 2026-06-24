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
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    # חישוב RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    return df.dropna()

def calculate_score(df):
    # סינונים מחמירים
    dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
    
    # 1. סינון מתיחות, עלייה מהירה ו-RSI
    if df['Daily_Change'].tail(3).sum() > 0.08 or abs(dist_from_ma) > 0.04 or df['RSI'].iloc[-1] > 70:
        return -1
    
    # 2. סינון דחיסה (5 ימים רצופים וקירבה למינימום תנודתיות)
    min_squeeze = df['Squeeze'].rolling(20).min().iloc[-1]
    if df['Squeeze'].iloc[-1] > min_squeeze * 1.05:
        return -1
    
    is_squeezing = df['Squeeze'] < df['Squeeze'].rolling(20).mean()
    if is_squeezing.rolling(5).sum().iloc[-1] < 5:
        return -1
    
    # 3. ניקוד
    score = 4 
    if df['OBV'].diff(5).mean() > 0: score += 2
    if 1.0 < df['RVOL'].iloc[-1] < 1.4: score += 1
        
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק התפרצויות מקצועי")
if not get_market_status(): st.warning("⚠️ אזהרת מערכת: השוק (SPY) מתחת ל-MA200.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי", "🔍 זן מניה"])

with tab1:
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files, default=all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        progress = st.progress(0)
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                score = calculate_score(df)
                if score >= 0:
                    master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2)})
            except: continue
            progress.progress((i + 1) / len(all_tickers))
        
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, column_config={"Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=7)}, use_container_width=True)

with tab4:
    ticker_input = st.text_input("הזן סימול מניה (למשל: AAPL):").upper()
    if st.button("בדוק מניה"):
        df = get_indicators(get_data(ticker_input))
        score = calculate_score(df)
        status_color = "green" if score >= 4 else "orange" if score >= 0 else "red"
        st.markdown(f"### ציון: <span style='color:{status_color}'>{score}/7</span>", unsafe_allow_html=True)
        if score >= 0: st.success("המניה עומדת בקריטריונים!")
        else: st.error("המניה נפסלה (מתוחה מדי או ללא דחיסה מספקת).")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        st.subheader("💼 התיק הפעיל שלך")
        for i, row in df_port.iterrows():
            col1, col2 = st.columns([0.8, 0.2])
            curr_p = float(get_data(row['Ticker'])['Close'].iloc[-1])
            ret = ((curr_p - row['Entry']) / row['Entry']) * 100
            col1.write(f"**{row['Ticker']}** | תשואה: {ret:.2f}%")
            if col2.button("🗑️ הסר", key=f"del_{i}"):
                df_port.drop(i, inplace=True)
                df_port.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()

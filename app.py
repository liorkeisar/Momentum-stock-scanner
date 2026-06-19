import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# הגדרות כלליות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# פונקציות חישוב טכני
def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['MACD'].iloc[-1] > 0: score += 1
    return score

# ממשק
st.sidebar.header("⚙️ הגדרות סריקה")
all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
selected_files = st.sidebar.multiselect("בחר תיקיות לסריקה:", all_files, default=all_files)

if st.sidebar.button("🗑️ מחק סריקה קודמת"):
    if os.path.exists(SCAN_RESULTS_FILE):
        os.remove(SCAN_RESULTS_FILE)
        st.rerun()

st.title("◈ KEISAR: סורק מוסדי מקצועי")
tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    if st.button("🚀 הפעל סריקה"):
        master_list = []
        progress_bar = st.progress(0)
        for i, file in enumerate(selected_files):
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for ticker in tickers:
                try:
                    df = get_indicators(yf.Ticker(ticker).history(period="6mo"))
                    if len(df) > 50:
                        score = calculate_score(df)
                        master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "Squeeze": round(df['Squeeze'].iloc[-1], 3)})
                except: continue
            progress_bar.progress((i + 1) / len(selected_files))
        
        if master_list:
            pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        else:
            if os.path.exists(SCAN_RESULTS_FILE): os.remove(SCAN_RESULTS_FILE)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE) and os.path.getsize(SCAN_RESULTS_FILE) > 10:
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג גרפים"):
            data = get_indicators(yf.Ticker(selected).history(period="6mo"))
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='gray', width=1), name='Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='gray', width=1), name='Lower'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV', line=dict(color='blue')), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)
            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [selected]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
                st.success(f"{selected} נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE, names=['Ticker']))

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות (ASST Style)")
    st.markdown("עקרון העבודה: זיהוי דחיסה טכנית המלווה בצבירת ווליום (OBV).")
    c1, c2 = st.columns(2)
    with c1:
        st.checkbox("Squeeze נמוך מ-0.15 (התכנסות)")
        st.checkbox("OBV עולה/יציב בגרף שבועי")
    with c2:
        st.checkbox("מחיר מעל ממוצע נע 20")
        st.checkbox("היסטוגרמת MACD חיובית")
    
    st.write("---")
    st.markdown("**1. התכנסות (Bollinger Squeeze):** מייצגת אנרגיה שנאגרת לפני פריצה. [attachment_0](attachment)")
    st.markdown("**2. צבירת סחורה (OBV):** עדות לפעילות מוסדית תומכת. ")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# הגדרות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

# ממשק
st.sidebar.header("⚙️ הגדרות סריקה")
all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f]
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
        for file in selected_files:
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for ticker in tickers:
                try:
                    df = yf.Ticker(ticker).history(period="6mo")
                    if len(df) > 50:
                        df = get_indicators(df)
                        squeeze = (df['Upper'].iloc[-1] - df['Lower'].iloc[-1]) / df['Close'].iloc[-1]
                        if squeeze < 0.15:
                            master_list.append({"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2), "Squeeze": round(squeeze, 3)})
                except: continue
        
        if master_list:
            pd.DataFrame(master_list).to_csv(SCAN_RESULTS_FILE, index=False)
        else:
            if os.path.exists(SCAN_RESULTS_FILE): os.remove(SCAN_RESULTS_FILE)
        st.rerun()

    # בדיקה בטוחה לפני קריאת הקובץ
    if os.path.exists(SCAN_RESULTS_FILE) and os.path.getsize(SCAN_RESULTS_FILE) > 0:
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        if 'Ticker' in df_res.columns:
            selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
            if st.button("הצג גרפים"):
                data = get_indicators(yf.Ticker(selected).history(period="6mo"))
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV'), row=2, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("לחץ על הפעל סריקה כדי להתחיל.")

with tab3:
    st.header("🎓 מדריך אסטרטגי")
    st.markdown("עקרון העבודה: זיהוי דחיסה טכנית (Bollinger Squeeze).")
    st.write("1. התכנסות רצועות מייצגת אגירת אנרגיה לפני פריצה.")
    st.write("2. עליית OBV מעידה על פעילות מוסדית תומכת.")

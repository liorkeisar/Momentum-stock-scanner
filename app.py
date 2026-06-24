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

# --- פונקציות ליבה ---
def get_indicators(ticker):
    df = yf.Ticker(ticker).history(period="6mo")
    if len(df) < 20: return None
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    return df.dropna()

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק ---
st.title("◈ KEISAR: סורק מוסדי")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק"])

with tab1:
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.sidebar.multiselect("בחר רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        for file in selected_files:
            for ticker in pd.read_csv(file, header=None).iloc[:, 0].dropna().unique():
                try:
                    df = get_indicators(ticker)
                    if df is not None:
                        master_list.append({"Ticker": ticker, "Score": calculate_score(df), "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
                except: continue
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        df_res['Signal'] = df_res['Score'].apply(lambda x: '✅ HIGH MOMENTUM' if x >= 3 else '')
        st.dataframe(df_res, use_container_width=True)
        
        ticker = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג גרף וניתוח"):
            df = get_indicators(ticker)
            last_p, atr = float(df['Close'].iloc[-1]), float(df['ATR'].iloc[-1])
            sl, tp = round(last_p - 1.5*atr, 2), round(last_p + 2.5*atr, 2)
            rr = round((tp - last_p) / (last_p - sl), 2)
            sl_pct, tp_pct = round(((last_p - sl)/last_p)*100, 2), round(((tp - last_p)/last_p)*100, 2)
            
            # תצוגת נתוני סיכון-סיכוי
            st.metric("יחס R/R", f"1:{rr}")
            col1, col2 = st.columns(2)
            col1.metric("Stop Loss", f"${sl} ({sl_pct}%)")
            col2.metric("Take Profit", f"${tp} ({tp_pct}%)")
            
            # גרף
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['RVOL'], name='RVOL'), row=2, col=1)
            fig.update_layout(height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [ticker], 'Entry': [last_p], 'SL': [sl], 'TP': [tp]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוסף!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.table(pd.read_csv(PORTFOLIO_FILE))
        if st.button("🗑️ נקה תיק"): os.remove(PORTFOLIO_FILE); st.rerun()

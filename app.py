import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# הגדרות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
PORTFOLIO_FILE = 'portfolio.csv'

def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=10).mean()
    return df.dropna()

def calculate_score(df):
    # ציון משוקלל: תנאים בסיסיים + בונוס על RVOL ודחיסה (Squeeze)
    score = 0.0
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['MACD'].iloc[-1] > 0: score += 1
    if df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['RVOL'].iloc[-1] >= 1.5: score += 1
    return round(score, 2)

st.title("◈ KEISAR: סורק מוסדי מדורג")

if st.button("🚀 הפעל סריקה מדורגת"):
    master_list = []
    # מציאת כל קבצי ה-CSV שאינם תוצאות סריקה או תיק
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'scan' not in f and 'portfolio' not in f]
    
    for file in all_files:
        tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
        for ticker in tickers:
            try:
                df = get_indicators(yf.Ticker(ticker).history(period="6mo"))
                if len(df) > 50:
                    master_list.append({
                        "Ticker": ticker, 
                        "Score": calculate_score(df),
                        "RVOL": round(df['RVOL'].iloc[-1], 2),
                        "Price": round(float(df['Close'].iloc[-1]), 2),
                        "Squeeze": round(df['Squeeze'].iloc[-1], 3)
                    })
            except: continue
    
    if master_list:
        # מיון חכם: קודם לפי ציון, ואז לפי RVOL כשובר שוויון
        df_res = pd.DataFrame(master_list).sort_values(by=['Score', 'RVOL'], ascending=[False, False])
        df_res.to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

# הצגה
if os.path.exists(SCAN_RESULTS_FILE):
    df_res = pd.read_csv(SCAN_RESULTS_FILE)
    st.dataframe(df_res, use_container_width=True)
    
    selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
    if st.button("הצג גרפים"):
        data = get_indicators(yf.Ticker(selected).history(period="6mo"))
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close']), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV'), row=2, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)

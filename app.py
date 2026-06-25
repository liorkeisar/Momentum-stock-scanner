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

def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=10).mean()
    return df.dropna()

def calculate_quality_score(df):
    # ציון מורכב: נותן משקל גבוה ל-RVOL ו-Squeeze
    score = 0.0
    # תנאים בסיסיים
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['MACD'].iloc[-1] > 0: score += 1
    
    # בונוס על Squeeze הדוק (ככל שהוא קטן מ-0.15, הציון עולה)
    sq = df['Squeeze'].iloc[-1]
    if sq < 0.15: score += (1.0 + (0.15 - sq) * 5)
    
    # בונוס על RVOL גבוה (ככל שהוא גבוה מ-1.5, הציון עולה משמעותית)
    rvol = df['RVOL'].iloc[-1]
    if rvol > 1.0: score += min(rvol, 2.0)
        
    return round(score, 2)

st.title("◈ KEISAR: סורק מוסדי מדורג")

if st.button("🚀 הפעל סריקה מדורגת"):
    master_list = []
    # כאן יבוא הלוגיקה שלך לטעינת קבצי הטיקרים
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'scan' not in f and 'port' not in f]
    for file in all_files:
        tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
        for ticker in tickers:
            try:
                df = get_indicators(yf.Ticker(ticker).history(period="6mo"))
                if len(df) > 50:
                    master_list.append({
                        "Ticker": ticker, 
                        "Score": calculate_quality_score(df),
                        "RVOL": round(df['RVOL'].iloc[-1], 2),
                        "Price": round(float(df['Close'].iloc[-1]), 2),
                        "Squeeze": round(df['Squeeze'].iloc[-1], 3)
                    })
            except: continue
    
    if master_list:
        # המיון כאן מבטיח שהטובה ביותר (הציון הכי גבוה) תהיה ראשונה
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

# הצגה
if os.path.exists(SCAN_RESULTS_FILE):
    df_res = pd.read_csv(SCAN_RESULTS_FILE)
    st.dataframe(df_res, use_container_width=True)

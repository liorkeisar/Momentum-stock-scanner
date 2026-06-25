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
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    return df.dropna()

def calculate_score(df):
    score = 0
    # חישוב RVOL: ווליום נוכחי חלקי ממוצע ווליום של 10 ימים אחרונים
    avg_vol = df['Volume'].rolling(window=10).mean().iloc[-1]
    rvol = df['Volume'].iloc[-1] / avg_vol if avg_vol > 0 else 0
    
    if df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if rvol >= 1.5: score += 1 
    
    return score

# --- ממשק ---
st.title("◈ KEISAR: סורק מוסדי מדורג")

if st.button("🚀 הפעל סריקה מדורגת (4 עד 1)"):
    master_list = []
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f]
    
    for file in all_files:
        tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
        for ticker in tickers:
            try:
                df = get_indicators(yf.Ticker(ticker).history(period="6mo"))
                if len(df) > 50:
                    score = calculate_score(df)
                    master_list.append({
                        "Ticker": ticker, 
                        "Score (0-4)": score, 
                        "Price": round(float(df['Close'].iloc[-1]), 2),
                        "Squeeze": round(df['Squeeze'].iloc[-1], 3)
                    })
            except: continue
    
    if master_list:
        # כאן קורה הקסם: המיון מתבצע לפי הציון מהגבוה לנמוך
        df_res = pd.DataFrame(master_list).sort_values(by="Score (0-4)", ascending=False)
        df_res.to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

# הצגה
if os.path.exists(SCAN_RESULTS_FILE) and os.path.getsize(SCAN_RESULTS_FILE) > 10:
    st.write("מניות מדורגות לפי חוזק (ציון 4 בראש):")
    df_res = pd.read_csv(SCAN_RESULTS_FILE)
    st.dataframe(df_res, use_container_width=True)

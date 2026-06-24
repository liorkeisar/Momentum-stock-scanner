import streamlit as st
import yfinance as yf
import pandas as pd
import os
import numpy as np

# הגדרות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- פונקציות חישוב ---
def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    return df.dropna()

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק מוסדי")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק השקעות"])

with tab1:
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.sidebar.multiselect("בחר רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        for file in selected_files:
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for ticker in tickers:
                try:
                    df = get_indicators(yf.Ticker(ticker).history(period="6mo"))
                    score = calculate_score(df)
                    master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
                except: continue
        # מיון לפי ציון (גבוה ביותר למעלה)
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        # תצוגה עם הדגשה למניות מנצחות
        st.dataframe(df_res.style.background_gradient(subset=['Score'], cmap='Greens'), use_container_width=True)
        
        selected = st.selectbox("בחר לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח"):
            data = get_indicators(yf.Ticker(selected).history(period="6mo"))
            last_p = float(data['Close'].iloc[-1])
            atr = float(data['ATR'].iloc[-1])
            sl, tp = round(last_p - (1.5*atr), 2), round(last_p + (2.5*atr), 2)
            st.write(f"### {selected} | מחיר: ${last_p} | SL: ${sl} | TP: ${tp}")
            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [selected], 'Entry': [last_p], 'SL': [sl], 'TP': [tp]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוסף!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE) and os.path.getsize(PORTFOLIO_FILE) > 0:
        df_port = pd.read_csv(PORTFOLIO_FILE)
        for i, row in df_port.iterrows():
            col1, col2 = st.columns([0.8, 0.2])
            curr = float(yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1])
            col1.write(f"**{row['Ticker']}** | כניסה: ${row['Entry']} | נוכחי: ${curr:.2f}")
            if col2.button("🗑️", key=f"del_{i}"):
                df_port.drop(i).to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="TITAN Wyckoff Pro", layout="wide")
st.title("◈ TITAN: מערכת וייקוף מוסדית אינטראקטיבית")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות תשתית ---
def init_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice']).to_csv(PORTFOLIO_FILE, index=False)

def get_portfolio_df():
    init_portfolio()
    return pd.read_csv(PORTFOLIO_FILE)

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER', 'Symbol (NASDAQ)']
    target = next((c for c in cols if c in df.columns), df.columns[0])
    # ניקוי כפילויות וטיפול בשמות מניות
    tickers = df[target].dropna().astype(str).unique().tolist()
    return [t.strip() for t in tickers]

# --- מנועי ניתוח ---
def check_divergence(df):
    if len(df) < 30: return False
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    return (df['Close'].tail(10).iloc[-1] < df['Close'].tail(10).iloc[0]) and (macd.tail(10).iloc[-1] > macd.tail(10).iloc[0])

def get_pivot_points(df):
    recent = df.tail(20)
    return recent['High'].max(), recent['Low'].min()

def calculate_wyckoff_and_risk(df):
    if len(df) < 30: return None
    atr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
    
    recent = df.tail(20)
    up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    if pd.isna(up_vol) or pd.isna(down_vol) or down_vol == 0: return None
    
    vr, rw = up_vol / down_vol, (recent['High'].max() - recent['Low'].min()) / recent['Close'].iloc[-1] * 100
    score = (40 if vr > 1.5 else 0) + (40 if rw < 5 else 0) + (20 if check_divergence(df) else 0)
    return min(score, 100), round(vr, 2), round(rw, 2), round(atr, 2), check_divergence(df)

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    files = [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]
    selected_file = st.sidebar.selectbox("בחר רשימה:", files) if files else None
    
    if selected_file and st.sidebar.button("הרץ סריקת עומק"):
        tickers = load_selected_list(selected_file)
        results = []
        bar = st.progress(0)
        for i, ticker in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            try:
                time.sleep(0.05)
                df = yf.Ticker(ticker).history(period="6mo", interval="1d")
                if not df.empty and df['Volume'].iloc[-1] > 200000 and df['Close'].iloc[-1] >= 10:
                    res = calculate_wyckoff_and_risk(df)
                    if res:
                        score, vr, rw, atr, div = res
                        results.append({"Ticker": ticker, "Score": score, "Price": round(df['Close'].iloc[-1], 2), "VR": vr, "RW%": rw, "Div": "✅" if div else "❌"})
            except: continue
        st.session_state['results_df'] = pd.DataFrame(results) if results else pd.DataFrame()
        st.rerun()

    if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
        st.dataframe(st.session_state['results_df'].sort_values("Score", ascending=False), use_container_width=True)
        
        target = st.selectbox("בחר מניה לניתוח מעמיק:", st.session_state['results_df']['Ticker'].tolist())
        if st.button("בצע Deep Dive למניה"):
            df_deep = yf.Ticker(target).history(period="1y")
            res, sup = get_pivot_points(df_deep)
            st.subheader(f"ניתוח עומק: {target}")
            col1, col2 = st.columns(2)
            col1.metric("התנגדות קרובה", round(res, 2))
            col2.metric("תמיכה קרובה", round(sup, 2))
            st.line_chart(df_deep['Close'])
            st.success("הניתוח הושלם!")

with tab2:
    init_portfolio()
    portfolio = pd.read_csv(PORTFOLIO_FILE)
    if not portfolio.empty:
        st.dataframe(portfolio, use_container_width=True)
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].unique().tolist())
        if st.button("מחק מניה 🗑️"):
            portfolio[portfolio['Ticker'] != to_manage].to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")
PORTFOLIO_FILE = 'portfolio.csv'

# פונקציות עזר לתיקון בסיס הנתונים
def init_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice']).to_csv(PORTFOLIO_FILE, index=False)

def get_portfolio_df():
    init_portfolio()
    return pd.read_csv(PORTFOLIO_FILE)

# --- פונקציות עזר ---
def get_available_lists(): return [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER', 'Symbol (NASDAQ)']
    target = next((c for c in cols if c in df.columns), df.columns[0])
    return df[target].dropna().astype(str).unique().tolist()

def calculate_wyckoff_and_risk(df):
    """חישוב מדדי וייקוף ורמות סיכון (ATR)"""
    if df is None or len(df) < 20: return 0, 0, 0, 0, 0
    
    # 1. ATR (ניהול סיכון)
    hl = df['High'] - df['Low']
    h_pc = (df['High'] - df['Close'].shift()).abs()
    l_pc = (df['Low'] - df['Close'].shift()).abs()
    atr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
    
    # 2. Wyckoff Metrics
    recent = df.tail(20)
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    vr = (up['Volume'].mean() / down['Volume'].mean()) if down['Volume'].mean() > 0 and not pd.isna(down['Volume'].mean()) else 1.0
    rw = (recent['High'].max() - recent['Low'].min()) / ((recent['High'].max() + recent['Low'].min()) / 2) * 100
    
    # 3. מערכת ניקוד מוסדית
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    return score, vr, rw, atr

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    available_lists = get_available_lists()
    if not available_lists: st.error("לא נמצאו קבצי CSV")
    else:
        selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
        min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

        if st.sidebar.button("הרץ סריקה"):
            tickers = load_selected_list(selected_file)
            results = []
            bar = st.progress(0)
            for i, ticker in enumerate(tickers):
                bar.progress((i + 1) / len(tickers))
                try:
                    time.sleep(0.05) # מניעת חסימה
                    df = yf.Ticker(ticker).history(period="3mo", interval="1d")
                    if not df.empty:
                        score, vr, rw, atr = calculate_wyckoff_and_risk(df)
                        if score >= min_score:
                            price = float(df['Close'].iloc[-1])
                            results.append({
                                "Ticker": ticker, "Score": score, "Price": round(price, 2),
                                "VR": round(vr, 2), "RW%": round(rw, 2),
                                "StopLoss": round(price - (2 * atr), 2),
                                "Target": round(price + (6 * atr), 2)
                            })
                except: continue
            st.session_state['results_df'] = pd.DataFrame(results)
            st.rerun()

        if st.session_state.get('results_df') is not None:
            df = st.session_state['results_df']
            st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
            
            to_add = st.selectbox("בחר מניה לעבודה:", df['Ticker'].tolist())
            if st.button("הוסף לתיק ההשקעות 💼"):
                price = df[df['Ticker'] == to_add]['Price'].values[0]
                df_port = get_portfolio_df()
                new_row = pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                pd.concat([df_port, new_row]).to_csv(PORTFOLIO_FILE, index=False)
                st.success("נוסף!")

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        view_df = portfolio.copy()
        for i, row in view_df.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                view_df.at[i, 'CurrentPrice'] = round(curr, 2)
                view_df.at[i, 'Perf%'] = round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)
            except: continue
        st.dataframe(view_df, use_container_width=True)
        
        to_manage = st.selectbox("בחר מניה לניהול:", view_df['Ticker'].unique().tolist())
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

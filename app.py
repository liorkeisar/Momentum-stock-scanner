import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="TITAN Wyckoff Pro", layout="wide")
st.title("◈ TITAN: מערכת וייקוף מוסדית")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות תשתית ---
def init_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice']).to_csv(PORTFOLIO_FILE, index=False)

def get_portfolio_df():
    init_portfolio()
    return pd.read_csv(PORTFOLIO_FILE)

def get_available_lists(): 
    return [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER', 'Symbol (NASDAQ)']
    target = next((c for c in cols if c in df.columns), df.columns[0])
    return df[target].dropna().astype(str).unique().tolist()

# --- מנוע הניתוח המקצועי (מתוקן) ---
def calculate_wyckoff_and_risk(df):
    """חישוב מדדי וייקוף וניהול סיכונים עם הגנה מ-NaN"""
    if df is None or len(df) < 30: return None
    
    # 1. ATR - ניהול סיכון
    hl = df['High'] - df['Low']
    h_pc = (df['High'] - df['Close'].shift()).abs()
    l_pc = (df['Low'] - df['Close'].shift()).abs()
    atr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
    
    # 2. Wyckoff Metrics
    recent = df.tail(20)
    up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    if pd.isna(up_vol) or pd.isna(down_vol) or down_vol == 0: return None
    
    vr = up_vol / down_vol
    rw = (recent['High'].max() - recent['Low'].min()) / recent['Close'].iloc[-1] * 100
    
    # 3. ניקוד
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    
    if np.isnan(atr) or np.isnan(score): return None
    
    return score, round(vr, 2), round(rw, 2), round(atr, 2)

# --- ממשק משתמש ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    available_lists = get_available_lists()
    if not available_lists: st.error("לא נמצאו קבצי CSV")
    else:
        selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
        min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

        if st.sidebar.button("הרץ סריקת עומק"):
            tickers = load_selected_list(selected_file)
            results = []
            bar = st.progress(0)
            
            for i, ticker in enumerate(tickers):
                bar.progress((i + 1) / len(tickers))
                try:
                    time.sleep(0.05)
                    df = yf.Ticker(ticker).history(period="6mo", interval="1d")
                    # הגנה: חייב להיות ווליום תקין ונתונים
                    if not df.empty and df['Volume'].iloc[-1] > 200000:
                        res = calculate_wyckoff_and_risk(df)
                        if res:
                            score, vr, rw, atr = res
                            if score >= min_score:
                                price = float(df['Close'].iloc[-1])
                                results.append({
                                    "Ticker": ticker, "Score": score, "Price": round(price, 2),
                                    "VR": vr, "RW%": rw,
                                    "StopLoss": round(price - (2 * atr), 2),
                                    "Target": round(price + (6 * atr), 2)
                                })
                except: continue
            
            st.session_state['results_df'] = pd.DataFrame(results) if results else pd.DataFrame()
            st.rerun()

        if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
            df = st.session_state['results_df'].sort_values("Score", ascending=False)
            st.dataframe(df, use_container_width=True)
            
            to_add = st.selectbox("בחר מניה להוספה:", df['Ticker'].tolist())
            if st.button("הוסף לתיק ההשקעות 💼"):
                price = df[df['Ticker'] == to_add]['Price'].values[0]
                df_port = get_portfolio_df()
                pd.concat([df_port, pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})]).to_csv(PORTFOLIO_FILE, index=False)
                st.success("נוסף!")

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        # הצגה נקייה ללא None
        st.dataframe(portfolio, use_container_width=True)
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].unique().tolist())
        if st.button("מחק מניה 🗑️"):
            portfolio[portfolio['Ticker'] != to_manage].to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="TITAN Wyckoff Pro", layout="wide")
st.title("◈ TITAN: מערכת וייקוף מוסדית עם זיהוי סטייה")
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

# --- מנוע סטייה וניתוח ---
def check_divergence(df):
    """זיהוי סטייה שורית: מחיר יורד + MACD עולה"""
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    
    recent_price = df['Close'].tail(10)
    recent_macd = macd.tail(10)
    
    price_down = recent_price.iloc[-1] < recent_price.iloc[0]
    macd_up = recent_macd.iloc[-1] > recent_macd.iloc[0]
    
    return price_down and macd_up

def calculate_wyckoff_and_risk(df):
    if df is None or len(df) < 30: return None
    
    # ATR
    hl = df['High'] - df['Low']
    h_pc = (df['High'] - df['Close'].shift()).abs()
    l_pc = (df['Low'] - df['Close'].shift()).abs()
    atr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
    
    # Wyckoff
    recent = df.tail(20)
    up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    if pd.isna(up_vol) or pd.isna(down_vol) or down_vol == 0: return None
    
    vr = up_vol / down_vol
    rw = (recent['High'].max() - recent['Low'].min()) / recent['Close'].iloc[-1] * 100
    
    # ניקוד משוקלל + בונוס סטייה
    score = 0
    if vr > 1.5: score += 40
    if rw < 5: score += 40
    
    is_divergent = check_divergence(df)
    if is_divergent: score += 20
    
    return min(score, 100), round(vr, 2), round(rw, 2), round(atr, 2), is_divergent

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    files = get_available_lists()
    selected_file = st.sidebar.selectbox("בחר רשימה:", files) if files else None
    min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

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
                        if score >= min_score:
                            price = float(df['Close'].iloc[-1])
                            results.append({
                                "Ticker": ticker, "Score": score, "Price": price,
                                "VR": vr, "RW%": rw, "Divergence": "✅" if div else "❌",
                                "Stop": round(price - (2 * atr), 2), "Target": round(price + (6 * atr), 2)
                            })
            except: continue
        st.session_state['results_df'] = pd.DataFrame(results) if results else pd.DataFrame()
        st.rerun()

    if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
        st.dataframe(st.session_state['results_df'].sort_values("Score", ascending=False), use_container_width=True)

# ... (שאר קוד התיק כפי שהיה)

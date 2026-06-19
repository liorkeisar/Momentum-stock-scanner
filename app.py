import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")

PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות עזר ---
def get_available_lists(): 
    return [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]

@st.cache_data
def load_selected_list(filename):
    # קריאה ללא כותרות, לוקחים את העמודה הראשונה
    df = pd.read_csv(filename, header=None)
    return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()

def calculate_wyckoff_score(df):
    if df is None or len(df) < 30: return 0, 0, 0
    recent = df.tail(20)
    
    # חישוב ווליום
    up = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    # חישוב יחס ווליום (VR)
    vr = (up / down) if (pd.notna(down) and down > 0) else 1
    
    # חישוב טווח מסחר (RW)
    high_max = recent['High'].max()
    low_min = recent['Low'].min()
    rw = (high_max - low_min) / ((high_max + low_min) / 2) * 100 if (high_max + low_min) != 0 else 0
    
    # חישוב ציון
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    return round(score, 2), round(vr, 2), round(rw, 2)

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice']).to_csv(PORTFOLIO_FILE, index=False)
    return pd.read_csv(PORTFOLIO_FILE)

# --- ממשק טאבים ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    available_lists = get_available_lists()
    selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
    min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

    if st.sidebar.button("הרץ סריקה"):
        tickers = load_selected_list(selected_file)
        results = []
        bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period="6mo")
                
                if not df.empty and 'Close' in df.columns:
                    score, vr, rw = calculate_wyckoff_score(df)
                    results.append({
                        "Ticker": ticker, 
                        "Score": score, 
                        "Price": round(float(df['Close'].iloc[-1]), 2), 
                        "VR": vr,
                        "RW%": rw
                    })
            except Exception:
                continue
        
        st.session_state['results_df'] = pd.DataFrame(results)
        st.rerun()

    if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
        df = st.session_state['results_df']
        df = df[df['Score'] >= min_score]
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
        
        to_add = st.selectbox("בחר מניה להוספה:", df['Ticker'].tolist())
        if st.button("הוסף לתיק ההשקעות 💼"):
            price = df[df['Ticker'] == to_add]['Price'].values[0]
            new_entry = pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
            new_entry.to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success(f"{to_add} נוספה בהצלחה!")

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        st.dataframe(portfolio, use_container_width=True)
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
    else: 
        st.info("התיק ריק.")

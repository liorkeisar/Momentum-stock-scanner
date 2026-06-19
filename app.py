import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="KEISAR Auto-Scanner", layout="wide")
st.title("◈ KEISAR: סורק מוסדי (גרסת איתור בסיס)")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות ---
def calculate_wyckoff(df):
    if df is None or len(df) < 30: return 0, 0, 0
    recent = df.tail(20)
    
    # חישוב ווליום
    up = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    vr = (up / down) if (pd.notna(down) and down > 0) else 1
    
    # חישוב טווח ותנודתיות
    high_max = recent['High'].max()
    low_min = recent['Low'].min()
    mid = (high_max + low_min) / 2
    rw = ((high_max - low_min) / mid * 100) if mid != 0 else 0
    
    # סינון מניות בשיא: בדיקה כמה המניה רחוקה מהשיא של 6 חודשים
    all_time_high = df['High'].max()
    current_price = df['Close'].iloc[-1]
    # אם המניה קרובה לשיא (פחות מ-10% מהשיא), היא מקבלת "קנס" בציון
    proximity_to_high = current_price / all_time_high
    penalty = 0.5 if proximity_to_high > 0.9 else 1.0 
    
    # חישוב ציון משוקלל
    raw_score = (40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0)
    score = min(raw_score * penalty, 100)
    
    return round(score, 2), round(vr, 2), round(rw, 2)

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק אוטומטי", "💼 תיק השקעות"])

with tab1:
    min_score = st.sidebar.slider("סנן לפי ציון מינימלי:", 0, 100, 40)
    
    if st.button("🚀 סריקת מניות בבניית בסיס"):
        all_files = [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]
        master_results = []
        bar = st.progress(0)
        
        for idx, file in enumerate(all_files):
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().astype(str).str.strip().unique()
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="5d")
                    if not hist.empty and hist['Volume'].mean() > 50000:
                        df = stock.history(period="6mo")
                        score, vr, rw = calculate_wyckoff(df)
                        # מציגים רק מניות עם ציון מינימלי אחרי הקנס
                        if score >= min_score:
                            master_results.append({
                                "Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), 
                                "VR": vr, "RW%": rw
                            })
                except: continue
            bar.progress((idx + 1) / len(all_files))
        
        st.session_state['master_df'] = pd.DataFrame(master_results)
        st.rerun()

    if 'master_df' in st.session_state:
        st.dataframe(st.session_state['master_df'].sort_values("Score", ascending=False), use_container_width=True)
        
        to_add = st.selectbox("בחר מניה להוספה לתיק:", st.session_state['master_df']['Ticker'].unique())
        if st.button("הוסף לתיק ההשקעות 💼"):
            row = st.session_state['master_df'][st.session_state['master_df']['Ticker'] == to_add].iloc[0]
            pd.DataFrame({'Ticker': [row['Ticker']], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [row['Price']]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success(f"{to_add} נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE), use_container_width=True)
        if st.button("נקה תיק 🗑️"):
            os.remove(PORTFOLIO_FILE)
            st.rerun()

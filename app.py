import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
st.title("◈ KEISAR: סורק מוסדי (צייד שפלים ופערים)")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות ---
def check_gap_closure(df):
    """בודק אם היה פער (Gap) שנסגר ביום האחרון"""
    if len(df) < 5: return False
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    # בדיקה האם מחיר הסגירה של אתמול נמצא בטווח המסחר של היום (סימן לסגירת פער)
    if today['Low'] <= yesterday['Close'] <= today['High']:
        return True
    return False

def calculate_wyckoff(ticker_obj, df):
    if df is None or len(df) < 30: return 0, 0, 0
    
    # 1. פילטר שווי שוק (מינימום 300 מיליון דולר)
    market_cap = ticker_obj.info.get('marketCap', 0)
    if market_cap < 300_000_000: return 0, 0, 0
    
    recent = df.tail(20)
    up = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    vr = (up / down) if (pd.notna(down) and down > 0) else 1
    
    low_min = recent['Low'].min()
    high_max = recent['High'].max()
    rw = ((high_max - low_min) / ((high_max + low_min) / 2) * 100)
    
    # 2. בונוס שפלים שנתיים
    year_low = df['Low'].min()
    current_price = df['Close'].iloc[-1]
    dist_from_low = (current_price - year_low) / (year_low + 0.001)
    bottom_bonus = 1.8 if dist_from_low < 0.20 else 1.0
    
    # 3. בונוס סגירת פער
    gap_bonus = 1.3 if check_gap_closure(df) else 1.0
    
    # חישוב ציון
    raw_score = (40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0)
    score = min(raw_score * bottom_bonus * gap_bonus, 100)
    
    return round(score, 2), round(vr, 2), round(rw, 2)

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק KEISAR", "💼 תיק השקעות"])

with tab1:
    min_score = st.sidebar.slider("סנן לפי ציון מינימלי:", 0, 100, 50)
    
    if st.button("🚀 הפעל סריקת KEISAR"):
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
                        score, vr, rw = calculate_wyckoff(stock, df)
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
        df_display = st.session_state['master_df'].sort_values("Score", ascending=False)
        st.dataframe(df_display, use_container_width=True)
        
        to_add = st.selectbox("בחר מניה להוספה לתיק:", df_display['Ticker'].unique())
        if st.button("הוסף לתיק ההשקעות 💼"):
            row = df_display[df_display['Ticker'] == to_add].iloc[0]
            pd.DataFrame({'Ticker': [row['Ticker']], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [row['Price']]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success(f"{to_add} נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE), use_container_width=True)
        if st.button("נקה תיק 🗑️"):
            os.remove(PORTFOLIO_FILE)
            st.rerun()

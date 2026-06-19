import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות ---
def get_available_lists(): 
    return [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename, header=None)
    # לוקחים את העמודה הראשונה, מנקים רווחים ומסירים כפילויות
    return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()

def calculate_wyckoff(df):
    if df is None or len(df) < 30: return 0, 0, 0, 0
    recent = df.tail(20)
    
    # חישוב ווליום
    up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    # חישוב VR ו-RW
    vr = (up_vol / down_vol) if (pd.notna(down_vol) and down_vol > 0) else 1
    high_max = recent['High'].max()
    low_min = recent['Low'].min()
    mid = (high_max + low_min) / 2
    rw = ((high_max - low_min) / mid * 100) if mid != 0 else 0
    
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    return round(score, 2), round(vr, 2), round(rw, 2), round(float(df['Close'].iloc[-1]), 2)

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    lists = get_available_lists()
    selected_file = st.sidebar.selectbox("בחר רשימה:", lists)
    
    if st.sidebar.button("הרץ סריקת עומק"):
        tickers = load_selected_list(selected_file) # כאן מוגדר המשתנה שגרם לשגיאה
        results = []
        bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            try:
                stock = yf.Ticker(ticker)
                # בדיקת סחירות בסיסית (5 ימים אחרונים)
                check = stock.history(period="5d")
                if not check.empty and check['Volume'].mean() > 50000:
                    df = stock.history(period="6mo")
                    score, vr, rw, price = calculate_wyckoff(df)
                    results.append({"Ticker": ticker, "Score": score, "Price": price, "VR": vr, "RW%": rw})
            except: continue
        
        st.session_state['res'] = pd.DataFrame(results)
        st.rerun()

    if 'res' in st.session_state and not st.session_state['res'].empty:
        st.dataframe(st.session_state['res'].sort_values("Score", ascending=False), use_container_width=True)
        # הוספה לתיק
        to_add = st.selectbox("בחר מניה להוספה:", st.session_state['res']['Ticker'].tolist())
        if st.button("הוסף לתיק 💼"):
            price = st.session_state['res'][st.session_state['res']['Ticker'] == to_add]['Price'].iloc[0]
            pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success("נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_p = pd.read_csv(PORTFOLIO_FILE)
        st.dataframe(df_p, use_container_width=True)

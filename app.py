import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="KEISAR Bottom Hunter & Value", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
PORTFOLIO_FILE = 'portfolio.csv'

def get_indicators(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # סינון איכות
        if info.get('marketCap', 0) < 300_000_000: return None
        if info.get('averageVolume', 0) < 200_000: return None
        
        # --- סינון שווי הוגן ---
        # אם מחיר היעד של האנליסטים גבוה ב-30% מהמחיר הנוכחי
        target_price = info.get('targetMeanPrice')
        current_price = info.get('currentPrice')
        if target_price and current_price:
            if current_price > (target_price * 0.70): return None # סינון: רק מניות עם פוטנציאל עלייה של 30%+
        
        df = stock.history(period="1y")
        if df is None or len(df) < 252: return None
        
        # סינון שפל שנתי (30% מהשפל)
        yearly_low = df['Close'].min()
        if current_price > (yearly_low * 1.30): return None

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
        return df.dropna()
    except Exception: return None

# --- ממשק ---
st.title("◈ KEISAR: סורק שפל וערך (Value & Bottom Hunter)")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק"])

with tab1:
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.sidebar.multiselect("בחר רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        with st.spinner('מחפש מניות בשפל שנסחרות בדיסקאונט...'):
            for file in selected_files:
                tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
                for ticker in tickers:
                    df = get_indicators(ticker)
                    if df is not None:
                        master_list.append({"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2)})
        
        if master_list:
            pd.DataFrame(master_list).to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()
        else:
            st.error("לא נמצאו מניות שעומדות בכל הקריטריונים (שפל + שווי הוגן + שווי שוק).")

    if os.path.exists(SCAN_RESULTS_FILE):
        st.dataframe(pd.read_csv(SCAN_RESULTS_FILE), use_container_width=True)

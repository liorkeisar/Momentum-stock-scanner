import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# הגדרות
st.set_page_config(page_title="KEISAR Bottom Hunter", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
PORTFOLIO_FILE = 'portfolio.csv'

def get_indicators(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # סינון איכות: שווי שוק 300M+ ונפח 200K+
        if info.get('marketCap', 0) < 300_000_000: return None
        if info.get('averageVolume', 0) < 200_000: return None
        
        df = stock.history(period="1y")
        if df is None or len(df) < 252: return None
        
        # סינון שפל שנתי
        yearly_low = df['Close'].min()
        current_price = df['Close'].iloc[-1]
        if current_price > (yearly_low * 1.15): return None

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
        return df.dropna()
    except: return None

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק ---
st.title("◈ KEISAR: סורק שפל (Bottom Hunter)")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק"])

with tab1:
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.sidebar.multiselect("בחר רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        with st.spinner('סורק ומדרג...'):
            for file in selected_files:
                for ticker in pd.read_csv(file, header=None).iloc[:, 0].dropna().unique():
                    df = get_indicators(ticker)
                    if df is not None:
                        master_list.append({"Ticker": ticker, "Score": calculate_score(df), "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
        
        if master_list:
            df_final = pd.DataFrame(master_list).sort_values(by="Score", ascending=False)
            df_final.to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        df_res['Signal'] = df_res.apply(lambda row: '✅ HIGH MOMENTUM' if row['Score'] >= 3 and row['RVOL'] > 1.5 else '', axis=1)
        st.dataframe(df_res, use_container_width=True)
        
        ticker = st.selectbox("בחר לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח"):
            df = get_indicators(ticker)
            if df is not None and not df.empty:
                last_p, atr = float(df['Close'].iloc[-1]), float(df['ATR'].iloc[-1])
                sl, tp = round(last_p - 1.5*atr, 2), round(last_p + 2.5*atr, 2)
                rr = round((tp - last_p) / (last_p - sl), 2)
                
                st.metric("יחס R/R", f"1:{rr}")
                col1, col2 = st.columns(2)
                col1.metric("Stop Loss", f"${sl}")
                col2.metric("Take Profit", f"${tp}")
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['RVOL'], name='RVOL'), row=2, col=1)
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                if st.button("הוסף לתיק"):
                    pd.DataFrame({'Ticker': [ticker], 'Entry': [last_p], 'SL': [sl], 'TP': [tp]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                    st.success("נוסף!")
            else:
                st.error("לא ניתן להציג ניתוח למניה זו (ייתכן שאינה עומדת בתנאי הסינון כרגע).")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        for i, row in df_port.iterrows():
            df_data = get_indicators(row['Ticker'])
            if df_data is not None:
                curr_p, ma20 = float(df_data['Close'].iloc[-1]), float(df_data['MA20'].iloc[-1])
                if curr_p < ma20: st.error(f"⚠️ אזהרת יציאה: {row['Ticker']} מתחת ל-MA20!")
                else: st.success(f"✅ {row['Ticker']} במומנטום חיובי.")
        st.table(df_port)
        if st.button("🗑️ נקה תיק"): os.remove(PORTFOLIO_FILE); st.rerun()

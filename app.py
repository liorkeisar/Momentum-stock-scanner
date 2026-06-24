import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np
from datetime import datetime

# הגדרות כלליות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- פונקציות חישוב ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    return yf.Ticker(ticker).history(period="6mo")

def get_market_status():
    spy = yf.Ticker("SPY").history(period="1y")
    spy['MA200'] = spy['Close'].rolling(window=200).mean()
    return spy['Close'].iloc[-1] > spy['MA200'].iloc[-1]

def get_indicators(df):
    df = df.copy()
    df['Daily_Change'] = df['Close'].pct_change()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['AvgVol'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['AvgVol']
    high_low = df['High'] - df['Low']
    df['ATR'] = high_low.rolling(window=14).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    if df['Daily_Change'].iloc[-1] < -0.05: return -1
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    elif df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק מוסדי מקצועי")
if not get_market_status():
    st.warning("⚠️ אזהרת מערכת: השוק (SPY) מתחת ל-MA200.")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    st.sidebar.header("⚙️ הגדרות סריקה")
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files, default=all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        alerts = []
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                if len(df) > 50:
                    score = calculate_score(df)
                    if score >= 0:
                        master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
                        if score >= 4 and df['RVOL'].iloc[-1] > 1.5:
                            alerts.append(f"🔥 איתות חם: {ticker} בציון {score} ו-RVOL {round(float(df['RVOL'].iloc[-1]), 2)}!")
            except: continue
            progress_bar.progress((i + 1) / len(all_tickers))
        
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.session_state['alerts'] = alerts
        st.rerun()

    if 'alerts' in st.session_state and st.session_state['alerts']:
        st.error("🚨 מרכז התראות בזמן אמת:")
        for alert in st.session_state['alerts']:
            st.write(alert)

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        def style_rvol(row):
            color = 'background-color: #d4edda' if row['RVOL'] > 1.5 else ''
            return [color] * len(row)
        st.dataframe(df_res.style.apply(style_rvol, axis=1), use_container_width=True)
        
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח"):
            data = get_indicators(get_data(selected))
            last_price = float(data['Close'].iloc[-1])
            atr = float(data['ATR'].iloc[-1])
            
            sl = round(last_price - (1.5 * atr), 2)
            tp = round(last_price + (3.0 * atr), 2)
            
            # חישוב יחס סיכוי סיכון
            risk = last_price - sl
            reward = tp - last_price
            rr_ratio = round(reward / risk, 2)
            
            st.metric(label="מחיר נוכחי", value=f"${last_price:.2f}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Stop Loss", f"${sl}", delta=f"{round(((sl-last_price)/last_price)*100, 2)}%")
            col2.metric("Take Profit", f"${tp}", delta=f"{round(((tp-last_price)/last_price)*100, 2)}%")
            col3.metric("R/R Ratio", f"1 : {rr_ratio}")
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['RVOL'], name='RVOL', line=dict(color='orange')), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("הוסף לתיק"):
                new_entry = pd.DataFrame({'Ticker': [selected], 'Entry_Price': [last_price], 'Date': [datetime.now().strftime("%Y-%m-%d")]})
                mode = 'a' if os.path.exists(PORTFOLIO_FILE) else 'w'
                new_entry.to_csv(PORTFOLIO_FILE, mode=mode, header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success(f"{selected} נוספה לתיק!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        portfolio_data = []
        for _, row in df_port.iterrows():
            try:
                curr_p = float(get_data(row['Ticker'])['Close'].iloc[-1])
                ret = ((curr_p - row['Entry_Price']) / row['Entry_Price']) * 100
                portfolio_data.append({**row.to_dict(), 'Current': round(curr_p, 2), 'Return_%': round(ret, 2)})
            except: continue
        st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)
    else:
        st.info("התיק ריק.")

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות (ASST)")
    st.markdown("""
    ### ניהול סיכונים חכם
    * **R/R Ratio:** יחס הסיכוי מול הסיכון. אנחנו שואפים תמיד ליחס הגבוה מ-1.5 כדי שהעסקה תהיה כדאית סטטיסטית.
    * **Delta %:** מראה כמה אחוזים המניה צריכה לעלות/לרדת כדי לפגוע ביעדים שלך.
    """)

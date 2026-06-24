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
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    # סינון: מניות מתוחות (יותר מ-6% מהממוצע) או זינוק חד מדי (8% ב-3 ימים)
    dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
    if df['Daily_Change'].tail(3).sum() > 0.08 or abs(dist_from_ma) > 0.06:
        return -1
    
    # בדיקת "משך דחיסה" (חייבת להיות בדחיסה לפחות 4 ימים מתוך ה-5 האחרונים)
    is_squeezing = df['Squeeze'] < df['Squeeze'].rolling(20).mean()
    if is_squeezing.rolling(5).sum().iloc[-1] < 4:
        return -1
    
    score = 0
    # בונוס על דחיסה (Squeeze)
    min_squeeze = df['Squeeze'].rolling(20).min().iloc[-1]
    if df['Squeeze'].iloc[-1] <= min_squeeze * 1.1: score += 4
    
    # בונוס על איסוף מוסדי (OBV Slope)
    if df['OBV'].diff(5).mean() > 0: score += 2
    
    # בונוס על RVOL שמעיד על עניין מבוקר
    if 1.0 < df['RVOL'].iloc[-1] < 1.4: score += 1
        
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק התפרצויות מקצועי")
if not get_market_status(): st.warning("⚠️ אזהרת מערכת: השוק (SPY) מתחת ל-MA200.")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    st.sidebar.header("⚙️ הגדרות סריקה")
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files, default=all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        progress = st.progress(0)
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                if len(df) > 50:
                    score = calculate_score(df)
                    if score >= 0:
                        master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2)})
            except: continue
            progress.progress((i + 1) / len(all_tickers))
        
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.subheader("דירוג מניות לסריקה")
        st.dataframe(
            df_res,
            column_config={"Score": st.column_config.ProgressColumn("Score", help="ניקוד המניה (0-7)", format="%d", min_value=0, max_value=7)},
            use_container_width=True
        )
        
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח"):
            st.session_state['selected_ticker'] = selected
            st.rerun()
            
        if 'selected_ticker' in st.session_state:
            ticker = st.session_state['selected_ticker']
            data = get_indicators(get_data(ticker))
            last_price, atr = float(data['Close'].iloc[-1]), float(data['ATR'].iloc[-1])
            sl, tp = round(last_price - (1.5 * atr), 2), round(last_price + (3.0 * atr), 2)
            rr_ratio = round((tp - last_price) / (last_price - sl), 2)
            
            st.subheader(f"📊 ניתוח טכני: {ticker}")
            st.markdown(f"**מחיר:** ${last_price:.2f} | **SL:** ${sl:.2f} | **TP:** ${tp:.2f} | **R/R:** 1:{rr_ratio:.2f}")
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['RVOL'], name='RVOL', line=dict(color='orange')), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [ticker], 'Entry': [last_price], 'SL': [sl], 'TP': [tp], 'Date': [datetime.now().strftime("%Y-%m-%d")]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success(f"{ticker} נוספה לתיק!")
                st.rerun()

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        st.subheader("💼 התיק הפעיל שלך")
        for i, row in df_port.iterrows():
            col1, col2 = st.columns([0.8, 0.2])
            curr_p = float(get_data(row['Ticker'])['Close'].iloc[-1])
            ret = ((curr_p - row['Entry']) / row['Entry']) * 100
            col1.write(f"**{row['Ticker']}** | תשואה: {ret:.2f}% | נוכחי: ${curr_p:.2f}")
            if col2.button("🗑️ הסר", key=f"del_{i}"):
                df_port.drop(i, inplace=True)
                df_port.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()
    else: st.info("התיק ריק.")

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות (ASST)")
    st.markdown("""
    המערכת מחפשת כעת **דחיסה ארוכה (לפחות 4 מתוך 5 ימים)** ללא מתיחות יתר.
    * 
    * 
    """)

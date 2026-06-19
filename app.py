import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="KEISAR Professional", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות עזר ---
def get_indicators(df):
    # Bollinger Bands
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    # OBV
    df['OBV'] = (pd.Series(np.where(df['Close'] > df['Close'].shift(1), df['Volume'], 
                 np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))).cumsum())
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- ממשק ---
st.title("◈ KEISAR: סורק מוסדי מקצועי")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק השקעות"])

with tab1:
    if st.button("🚀 הפעל סריקה מלאה"):
        all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f]
        master_list = []
        progress_bar = st.progress(0)
        
        files_count = len(all_files)
        for i, file in enumerate(all_files):
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    df = stock.history(period="6mo")
                    if len(df) > 50:
                        df = get_indicators(df)
                        # לוגיקת ה-Squeeze: טווח צר (Lower ו-Upper קרובים)
                        squeeze = (df['Upper'].iloc[-1] - df['Lower'].iloc[-1]) / df['Close'].iloc[-1]
                        if squeeze < 0.15: # התכנסות
                            master_list.append({"Ticker": ticker, "Price": df['Close'].iloc[-1], "Squeeze": round(squeeze, 3)})
                except: continue
            progress_bar.progress((i + 1) / files_count)
        
        st.session_state['results'] = pd.DataFrame(master_list)
        st.rerun()

    if 'results' in st.session_state:
        df_res = st.session_state['results']
        st.dataframe(df_res, use_container_width=True)
        
        selected = st.selectbox("בחר מניה לניתוח עומק:", df_res['Ticker'].unique())
        if st.button("הצג גרפים תומכי החלטה"):
            data = get_indicators(yf.Ticker(selected).history(period="6mo"))
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                                row_heights=[0.5, 0.25, 0.25])
            # מחיר + בולינגר
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='gray', width=1), name='Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='gray', width=1), name='Lower'), row=1, col=1)
            # OBV
            fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV', line=dict(color='blue')), row=2, col=1)
            # MACD
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name='Signal'), row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            if st.button("הוסף לתיק"):
                pd.DataFrame({'Ticker': [selected]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
                st.success("נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE, names=['Ticker']))

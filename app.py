import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os

st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")

# --- 1. מנוע חישובים ---
def calculate_all(df, market_df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    df['Is_Spike'] = df['Volume'] > (df['Volume'].rolling(20).mean() * 2)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Divergence'] = (df['Close'] <= df['Close'].rolling(20).min()) & (df['MACD'] > df['MACD'].rolling(20).min())
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_df['Close'] / market_df['Close'].iloc[0])
    return df

# --- 2. ממשק משתמש ---
st.title("🛡️ Institutional Accumulation Scanner")

# סרגל צד לניהול קבצים
with st.sidebar:
    st.header("הגדרות סריקה")
    available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    index_option = st.selectbox("בחר רשימת מניות:", available_files)
    run_btn = st.button("🚀 הרץ סריקה", type="primary")

tabs = st.tabs(["🔍 סורק פעיל", "📁 ארכיון תוצאות"])

with tabs[0]:
    if run_btn:
        st.session_state['results'] = {}
        tickers = pd.read_csv(index_option, header=None)[0].tolist()
        market_df = yf.Ticker("SPY").history(period="1y")
        
        progress = st.progress(0)
        with st.spinner('סורק מניות, נא להמתין...'):
            for i, ticker in enumerate(tickers):
                progress.progress((i + 1) / len(tickers))
                try:
                    df = yf.Ticker(ticker.strip()).history(period="1y")
                    if len(df) > 50:
                        df = calculate_all(df, market_df.iloc[-len(df):])
                        if df.iloc[-1]['Divergence'] and df.iloc[-1]['Close'] > df.iloc[-1]['VWAP']:
                            st.session_state['results'][ticker] = df
                except: continue
        
        with open('scanner_history.json', 'w') as f:
            json.dump(list(st.session_state['results'].keys()), f)
        st.success("הסריקה הסתיימה!")

    if 'results' in st.session_state and st.session_state['results']:
        col_left, col_right = st.columns([1, 3])
        with col_left:
            selected_ticker = st.selectbox("בחר מניה מהתוצאות:", list(st.session_state['results'].keys()))
            st.session_state['selected'] = selected_ticker
            
            last = st.session_state['results'][selected_ticker].iloc[-1]
            indicators = {
                "Divergence": last['Divergence'], 
                "Price > VWAP": last['Close'] > last['VWAP'], 
                "RS > 1.0": last['RS'] > 1.0, 
                "RSI < 65": last['RSI'] < 65, 
                "Volume Spike": last['Is_Spike']
            }
            
            st.markdown("### סטטוס טכני")
            for name, status in indicators.items():
                st.metric(label=name, value="✅" if status else "❌")

        with col_right:
            df = st.session_state['results'][st.session_state['selected']]
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name='VWAP', line=dict(color='yellow', width=1)))
            
            if df.iloc[-1]['Divergence'] and df.iloc[-1]['Close'] > df.iloc[-1]['VWAP']:
                fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Low'].iloc[-1]*0.98], mode='markers', 
                                        marker=dict(symbol='triangle-up', size=15, color='lime'), name='אות קניה'))
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("📁 מניות מסריקות קודמות")
    if os.path.exists('scanner_history.json'):
        with open('scanner_history.json', 'r') as f:
            history = json.load(f)
        
        if not history:
            st.info("הארכיון ריק.")
        else:
            cols = st.columns(4)
            for i, ticker in enumerate(history):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.markdown(f"### 📈 {ticker}")
                        if st.button(f"טען גרף {ticker}", key=f"hist_{ticker}"):
                            st.switch_page("app.py") # במידה ואתה בתיקיית עבודה אחת
                            st.toast(f"מטען את {ticker}...")

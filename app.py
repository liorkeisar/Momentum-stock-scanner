import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import os

st.set_page_config(page_title="סורק פריצות מוסדי", layout="wide")
st.title("📈 סורק פריצות מוסדי")

@st.cache_data
def load_tickers(filename):
    try:
        # התיקון החשוב: header=None קורא את הקבצים שלך נכון
        df = pd.read_csv(filename, header=None)
        return df[0].dropna().tolist()
    except Exception as e:
        st.error(f"שגיאה בטעינת {filename}: {e}")
        return []

# מציאת קבצי ה-CSV באופן אוטומטי
available_files = [f for f in os.listdir('.') if f.endswith('.csv') and f != 'requirements.txt']
index_option = st.sidebar.selectbox("בחר קובץ מניות לסריקה:", available_files)

if index_option:
    ticker_list = load_tickers(index_option)
    st.sidebar.write(f"נסרקים כעת {len(ticker_list)} טיקרים מתוך {index_option}")

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / df['MA20']) * 100
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Hist'] = (exp12 - exp26) - (exp12 - exp26).ewm(span=9, adjust=False).mean()
    return df

def plot_interactive_chart(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='rgba(173, 216, 230, 0.5)', width=1), name='BB Upper'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='rgba(173, 216, 230, 0.5)', width=1), name='BB Lower', fill='tonexty'))
    fig.update_layout(title=f"גרף: {ticker}", template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
if 'all_data' not in st.session_state: st.session_state['all_data'] = pd.DataFrame()

if st.button(f'🚀 התחל סריקה ל-{index_option}'):
    found = []
    all_results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ticker_list):
        try:
            time.sleep(0.1)
            df = yf.Ticker(ticker).history(period="60d")
            if len(df) < 20: continue
            df = calculate_indicators(df)
            last, prev = df.iloc[-1], df.iloc[-2]
            all_results.append({'Ticker': ticker, 'BB_Width': round(last['BB_Width'], 2), 'MACD_Hist': round(last['MACD_Hist'], 4)})
            
            if (last['BB_Width'] <= 12 and last['MACD_Hist'] > prev['MACD_Hist'] and last['Volume'] > (last['Vol_MA20'] * 1.2)):
                found.append(ticker)
                st.session_state['results_cache'][ticker] = df
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    st.session_state['found_stocks'] = found
    st.session_state['all_data'] = pd.DataFrame(all_results)
    st.success("הסריקה הסתיימה!")

tab1, tab2 = st.tabs(["🎯 מניות לפריצה", "📊 כל נתוני המדד"])
with tab1:
    if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
        selected = st.selectbox("בחר מניה:", st.session_state['found_stocks'])
        plot_interactive_chart(st.session_state['results_cache'].get(selected), selected)
with tab2:
    if not st.session_state['all_data'].empty:
        st.dataframe(st.session_state['all_data'].sort_values('BB_Width'), use_container_width=True)

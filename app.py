import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import numpy as np
from datetime import datetime
import os

# --- אתחול מסד נתונים ---
def init_db():
    conn = sqlite3.connect('keisar_pro.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio 
                 (ticker TEXT, entry REAL, sl REAL, tp REAL, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- פונקציות חישוב ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        return df if not df.empty else None
    except:
        return None

def get_indicators(df):
    df = df.copy()
    # ממוצעים ואינדיקטורים
    df['MA20'] = df['Close'].rolling(window=20).mean()
    # VWAP (Institutional Benchmark)
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    high_low = df['High'] - df['Low']
    df['ATR'] = high_low.rolling(window=14).mean()
    return df.dropna()

# --- ממשק משתמש ---
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
st.title("◈ KEISAR: סורק מוסדי מקצועי")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    ticker_input = st.text_input("הזן סימול (למשל: AAPL, NVDA, TSLA):")
    if ticker_input:
        df = get_indicators(get_data(ticker_input))
        if df is not None:
            last_price = float(df['Close'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("מחיר נוכחי", f"${last_price:.2f}")
            c2.metric("RVOL", f"{df['RVOL'].iloc[-1]:.2f}")
            c3.metric("ATR", f"${atr:.2f}")
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר'))
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name='VWAP', line=dict(color='blue', width=1)))
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("הוסף לתיק המוסדי"):
                conn = sqlite3.connect('keisar_pro.db')
                conn.execute("INSERT INTO portfolio VALUES (?, ?, ?, ?, ?)", 
                             (ticker_input.upper(), last_price, last_price-(1.5*atr), last_price+(3*atr), datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success(f"{ticker_input.upper()} נוספה לתיק!")

with tab2:
    st.subheader("💼 התיק הפעיל")
    conn = sqlite3.connect('keisar_pro.db')
    df_port = pd.read_sql_query("SELECT * FROM portfolio", conn)
    conn.close()
    
    if not df_port.empty:
        for _, row in df_port.iterrows():
            curr_df = get_data(row['ticker'])
            if curr_df is not None:
                curr_p = float(curr_df['Close'].iloc[-1])
                pnl = ((curr_p - row['entry']) / row['entry']) * 100
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
                    c1.metric(row['ticker'], f"${curr_p:.2f}", f"{pnl:.2f}%")
                    c2.write(f"**כניסה:** ${row['entry']:.2f}")
                    c2.write(f"**SL:** ${row['sl']:.2f} | **TP:** ${row['tp']:.2f}")
                    if c3.button("סגור פוזיציה", key=row['ticker']):
                        conn = sqlite3.connect('keisar_pro.db')
                        conn.execute("DELETE FROM portfolio WHERE ticker = ?", (row['ticker'],))
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("התיק ריק.")

with tab3:
    st.header("🎓 מדריך: עבודה מוסדית")
    st.write("ה-VWAP הוא כלי מרכזי המציג את המחיר הממוצע המשוקלל בנפח. סוחרים מוסדיים משתמשים בו כדי לזהות היכן הכסף הגדול נכנס לעסקה.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- הגדרת רשימת מניות ה-S&P 500 (מקור פופולרי ומייצג לשוק) ---
@st.cache_data(ttl=86400) # שמירה במטמון ל-24 שעות
def get_sp500_tickers():
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    return table[0]['Symbol'].tolist()

# --- פונקציות עזר (אותן פונקציות עבודה משיחתנו הקודמת) ---
def is_bad(v): return v is None or pd.isna(v)
def safe_last(s): return s.iloc[-1] if len(s) > 0 else np.nan

def add_indicators(df):
    df = df.copy()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    
    # Wyckoff Logic
    df['CLV'] = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, np.nan)
    vol_ma20 = df['Volume'].rolling(20).mean()
    down_days = df['Close'] < df['Open']
    df['AbsorptionPower'] = (df['CLV'] * df['Volume'] * (df['Volume'] / vol_ma20.replace(0, np.nan))).where(down_days, 0).rolling(15).sum()
    df['LowVolumeTest'] = (df['Low'] <= df['Low'].rolling(10).min()) & (df['Volume'] < vol_ma20 * 0.7)
    df['SqueezeRatio'] = df['ATR'] / df['Close'].rolling(50).mean()
    df['SidewaysEnergy'] = df['SqueezeRatio'].rolling(20).apply(lambda x: 1 if x.iloc[-1] < x.iloc[0] else 0)
    return df

def compute_breakout_decision(df):
    try:
        abs_score = min(100, (safe_last(df['AbsorptionPower']) / df['AbsorptionPower'].rolling(60).max().mean() * 100)) if not is_bad(safe_last(df['AbsorptionPower'])) else 0
        score = (abs_score * 0.5) + (100 if safe_last(df['LowVolumeTest']) else 0) * 0.25 + (100 if safe_last(df['SidewaysEnergy']) else 0) * 0.25
        return int(score)
    except: return 0

# --- ממשק משתמש לסריקה ---
st.set_page_config(layout="wide")
st.title("🌎 סורק שוק מלא (S&P 500) — וייקוף")

if st.sidebar.button("🚀 התחל סריקה מקיפה"):
    tickers = get_sp500_tickers()
    progress = st.progress(0)
    final_list = []
    
    # כדי שלא ייקח נצח, נסרוק את ה-100 הראשונים כדוגמה, 
    # ניתן לשנות ל-len(tickers) לסריקה מלאה של 500 מניות
    for i, t in enumerate(tickers[:100]): 
        progress.progress((i+1)/100)
        df = yf.Ticker(t).history(period="6mo")
        if not df.empty:
            df = add_indicators(df)
            score = compute_breakout_decision(df)
            if score > 60: # סינון ראשוני של המבטיחות ביותר בלבד
                final_list.append({"Ticker": t, "Score": score})
    
    st.sidebar.success("הסריקה הסתיימה!")
    
    # הצגת הטבלה הסופית
    df_results = pd.DataFrame(final_list).sort_values("Score", ascending=False)
    st.table(df_results)

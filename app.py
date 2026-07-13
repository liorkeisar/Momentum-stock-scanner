import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- עיצוב ועקביות (נותר כפי שהגדרת) ---
st.set_page_config(page_title="Wyckoff Pro Pro", layout="wide")

# --- פונקציות תשתית משופרות ---
def is_bad(v):
    return v is None or pd.isna(v)

def safe_last(s):
    try: return s.iloc[-1] if len(s) > 0 else np.nan
    except: return np.nan

def score_component(value, low, high, invert=False):
    if is_bad(value): return 0
    v = (value - low) / (high - low) if high != low else 0
    v = max(0.0, min(1.0, v))
    return int(round((1.0 - v if invert else v) * 100))

# --- מנוע הוספת אינדיקטורים משודרג ---
def add_indicators(df):
    df = df.copy()
    # תנועה ומגמה
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    
    # 1. Absorption Logic
    df['CLV'] = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, np.nan)
    down_days = df['Close'] < df['Open']
    df['AbsorptionPower'] = (df['CLV'] * df['Volume'] * (df['Volume'] / df['Volume'].rolling(20).mean())).where(down_days, 0).rolling(15).sum()
    
    # 2. Wyckoff Accumulation/Test
    df['LowVolumeTest'] = (df['Low'] == df['Low'].rolling(10).min()) & (df['Volume'] < df['Volume'].rolling(20).mean() * 0.7)
    
    # 3. Volatility Squeeze (Sideways)
    df['SqueezeRatio'] = df['ATR'] / df['Close'].rolling(50).mean()
    df['SidewaysEnergy'] = df['SqueezeRatio'].rolling(20).apply(lambda x: 1 if x.iloc[-1] < x.iloc[0] else 0)
    
    # אינדיקטורים קלאסיים
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().clip(lower=0).rolling(14).mean() / (-df['Close'].diff().clip(upper=0)).rolling(14).mean())))
    df['SMA200'] = df['Close'].rolling(200).mean()
    return df

# --- מנוע החלטה מותאם למנועי איסוף ---
def compute_breakout_decision(df):
    comps = {}
    comps["absorption"] = score_component(safe_last(df['AbsorptionPower']), 0, df['AbsorptionPower'].rolling(60).max().mean() * 0.5)
    comps["test"] = 100 if safe_last(df['LowVolumeTest']) else 20
    comps["squeeze"] = 100 if safe_last(df['SidewaysEnergy']) else 40
    comps["trend_support"] = 100 if safe_last(df['Close']) > safe_last(df['SMA200']) else 20
    
    # שקלול משופר
    weights = {"absorption": 0.40, "test": 0.25, "squeeze": 0.20, "trend_support": 0.15}
    score = sum(comps[k] * weights[k] for k in weights)
    
    note = "מחפש סימני ספיגה בשוק"
    if comps["absorption"] > 70: note = "⚠️ איתות ספיגה חזק (ידיים חזקות קונות בירידות)"
    
    return {"score": int(score), "note": note}

# --- ממשק משתמש ---
st.markdown("## ◈ Wyckoff Accumulation Pro")
ticker = st.text_input("הקלד טיקר (למשל: NVDA, TSLA):", "NVDA")

if st.button("🚀 נתח מצב"):
    df = yf.Ticker(ticker).history(period="12mo")
    if not df.empty:
        df = add_indicators(df)
        res = compute_breakout_decision(df)
        
        # תצוגה
        st.metric("ציון פוטנציאל איסוף (Wyckoff)", f"{res['score']}/100")
        st.info(res['note'])
        
        # גרף
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index[-100:], open=df['Open'][-100:], 
                      high=df['High'][-100:], low=df['Low'][-100:], close=df['Close'][-100:]))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("לא נמצאו נתונים")


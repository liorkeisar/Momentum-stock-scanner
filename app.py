import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor

# --- מנוע חישובים טכני מקצועי ---
class TechnicalEngine:
    @staticmethod
    def get_indicators(df):
        # ATR לניהול סיכון
        hl = df['High'] - df['Low']
        atr = hl.rolling(14).mean().iloc[-1]
        
        # אינדיקטורים משולבים
        rsi = 100 - (100 / (1 + df['Close'].diff().clip(lower=0).rolling(14).mean() / 
                            df['Close'].diff().clip(upper=0).abs().rolling(14).mean().iloc[-1]))
        
        # Wyckoff Logic (Volume Ratio & Range Width)
        recent = df.tail(20)
        vr = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean() / \
             recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
        rw = (recent['High'].max() - recent['Low'].min()) / recent['Close'].mean() * 100
        
        return {"atr": atr, "rsi": rsi, "vr": vr, "rw": rw}

    @staticmethod
    def analyze(ticker):
        try:
            time.sleep(0.1) # הגנה אקטיבית מחסימה
            df = yf.Ticker(ticker).history(period="1y")
            if len(df) < 200: return None
            
            ind = TechnicalEngine.get_indicators(df)
            price = df['Close'].iloc[-1]
            
            # חישוב ציון "בית השקעות" (משוקלל)
            score = (ind['vr'] * 10) + (10 - ind['rw']) * 3 + (50 if ind['rsi'] < 40 else 0)
            
            return {
                "Ticker": ticker, "Price": round(price, 2),
                "Score": int(min(score, 100)),
                "Stop": round(price - (2 * ind['atr']), 2),
                "Target": round(price + (6 * ind['atr']), 2)
            }
        except: return None

# --- ממשק ניהול (UI) ---
st.set_page_config(layout="wide")
st.title("🏛️ Institutional Trading Terminal")

if st.button("הרץ סריקת עומק"):
    # רשימה שמחולקת ל-Batches למניעת עומס
    tickers = ["AAPL", "NVDA", "MSFT", "AMD", "META", "GOOGL"] # כאן טוענים את ה-Batch
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        data = list(executor.map(TechnicalEngine.analyze, tickers))
    
    df_results = pd.DataFrame([d for d in data if d]).sort_values("Score", ascending=False)
    st.dataframe(df_results, use_container_width=True)

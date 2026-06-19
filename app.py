import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="KEISAR Accumulation Hunter", layout="wide")
st.title("◈ KEISAR: אסטרטגיית איסוף מוסדי (OBV & Squeeze)")

def calculate_accumulation_score(df):
    """
    מחשב ציון לפי: OBV עולה + ירידת ATR (דחיסה) + מומנטום MACD
    """
    if len(df) < 50: return 0, 0, 0
    
    # 1. OBV Momentum: האם ה-OBV ב-20 יום האחרונים במגמת עלייה?
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    obv_trend = df['OBV'].tail(20).diff().mean()
    
    # 2. Squeeze: ירידת ATR (תנודתיות נמוכה)
    df['ATR'] = df['High'] - df['Low'] # פישוט לטווח יומי
    atr_trend = df['ATR'].tail(15).mean()
    atr_ratio = df['ATR'].iloc[-1] / df['ATR'].tail(30).mean() # יחס בין נוכחי לממוצע חודשי
    
    # 3. MACD Rebound: האם ההיסטוגרמה משתפרת?
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    macd_rebound = 1 if hist.iloc[-1] > hist.iloc[-2] else 0
    
    # חישוב הציון:
    # בונוס על OBV עולה, בונוס על ATR נמוך (Squeeze), בונוס על היפוך MACD
    score = 0
    if obv_trend > 0: score += 40
    if atr_ratio < 1.0: score += 40 # התכנסות
    if macd_rebound: score += 20
    
    return score, round(float(obv_trend), 0), round(float(atr_ratio), 2)

# --- ממשק ---
if st.button("🚀 סרוק מניות לפי חתימת ASST"):
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f]
    results = []
    
    for file in all_files:
        tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period="6mo")
                market_cap = stock.info.get('marketCap', 0)
                
                if market_cap > 300_000_000 and len(df) > 50:
                    score, obv_val, atr_rat = calculate_accumulation_score(df)
                    if score >= 60:
                        results.append({"Ticker": ticker, "Score": score, "OBV_Trend": obv_val, "ATR_Ratio": atr_rat})
            except: continue
            
    if results:
        st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False), use_container_width=True)
    else:
        st.write("לא נמצאו מניות עם חתימת איסוף כרגע.")

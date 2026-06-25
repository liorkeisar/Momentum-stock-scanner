import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("◈ KEISAR Pro Ultimate Scanner")

# --- מנוע אינדיקטורים מלא ---
def get_analysis(ticker):
    df = yf.Ticker(ticker).history(period="6mo")
    if len(df) < 50: return None
    
    # ממוצעים ודחיסות
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['Squeeze'] = (df['MA20'] + (df['STD'] * 2) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
    
    # RSI וסטייה (Divergence)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
    
    # ווליום יחסי
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # זיהוי סטייה (מחיר יורד + RSI עולה)
    df['Div'] = (df['Low'] < df['Low'].shift(1)) & (df['RSI'] > df['RSI'].shift(1))
    
    return df.iloc[-1]

# --- ממשק סריקה ---
uploaded_file = st.file_uploader("העלה קובץ סימולים (CSV)", type="csv")
if uploaded_file and st.button("🚀 הרץ סריקה מלאה"):
    symbols = pd.read_csv(uploaded_file, header=None).iloc[:, 0].dropna().unique()
    results = []
    
    with st.spinner("מנתח שוק..."):
        for s in symbols:
            s = str(s).strip().split(' ')[0]
            try:
                row = get_analysis(s)
                if row is None: continue
                
                # קריטריונים לסריקה "מושלמת"
                is_breakout = row['Close'] > row['MA20'] and row['RVOL'] > 1.5
                is_squeeze = row['Squeeze'] < 0.05
                is_div = row['Div']
                
                if is_breakout or is_squeeze or is_div:
                    results.append({
                        "Ticker": s, "Price": round(row['Close'], 2),
                        "RSI": round(row['RSI'], 1), "RVOL": round(row['RVOL'], 2),
                        "Breakout": is_breakout, "Squeeze": is_squeeze, "Divergence": is_div
                    })
            except: continue

    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.warning("לא נמצאו מניות בתנאי הסריקה.")

# 
# 

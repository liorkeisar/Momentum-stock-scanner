import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("◈ KEISAR Pro Scanner V2 (Python Engine)")

# --- פונקציות חישוב טכני (V2 Logic) ---
def calculate_indicators(df):
    df = df.sort_values('Date')
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    # OBV
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return df

def detect_divergence(df):
    # חישוב Pivot Lows (שפלים)
    df['is_pivot'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
    pivots = df[df['is_pivot']]
    if len(pivots) < 2: return False
    
    last_p = pivots.iloc[-1]
    prev_p = pivots.iloc[-2]
    
    # סטייה: מחיר יורד (Lower Low), RSI עולה (Higher Low)
    if (last_p['Low'] < prev_p['Low']) and (last_p['RSI'] > prev_p['RSI']):
        return True
    return False

# --- ממשק ---
all_files = [f for f in os.listdir('.') if f.endswith('.csv')]
selected_file = st.selectbox("בחר קובץ CSV לסריקה:", all_files)

if st.button("🚀 הרץ סריקה"):
    df_raw = pd.read_csv(selected_file)
    results = []
    
    # הנחה: הקובץ מכיל עמודה 'Symbol'
    for symbol, group in df_raw.groupby('Symbol'):
        df = calculate_indicators(group)
        if len(df) < 50: continue
        
        last = df.iloc[-1]
        div = detect_divergence(df)
        
        # חישוב ציונים (Weights)
        selloff = 1 if last['Close'] < last['SMA50'] else 0
        accum = 1 if div else 0
        score = (selloff * 40) + (accum * 60)
        
        if score > 0:
            results.append({
                "Symbol": symbol,
                "Close": last['Close'],
                "RSI": round(last['RSI'], 2),
                "Divergence": div,
                "Score": score
            })
    
    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("לא נמצאו מניות בתנאי הסריקה.")

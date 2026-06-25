import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("◈ KEISAR Pro Hunter (Stable Version)")

# --- פונקציות חישוב ---
def calculate_indicators(df):
    # וודא שהעמודות קיימות באותיות קטנות ליתר ביטחון
    df.columns = [c.capitalize() for c in df.columns]
    
    if 'Date' not in df.columns:
        return None
        
    df = df.sort_values('Date')
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def detect_divergence(df):
    if 'Low' not in df.columns or 'RSI' not in df.columns: return False
    df['is_pivot'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
    pivots = df[df['is_pivot']]
    if len(pivots) < 2: return False
    
    last_p = pivots.iloc[-1]
    prev_p = pivots.iloc[-2]
    
    return (last_p['Low'] < prev_p['Low']) and (last_p['RSI'] > prev_p['RSI'])

# --- ממשק משתמש ---
all_files = [f for f in os.listdir('.') if f.endswith('.csv')]
selected_file = st.selectbox("בחר קובץ CSV לסריקה:", all_files)

if st.button("🚀 הרץ סריקה"):
    try:
        df_raw = pd.read_csv(selected_file)
        results = []
        
        # ניקוי שמות עמודות בקלט
        df_raw.columns = [c.capitalize() for c in df_raw.columns]
        
        for symbol, group in df_raw.groupby('Symbol'):
            df = calculate_indicators(group)
            if df is None or len(df) < 50: continue
            
            last = df.iloc[-1]
            div = detect_divergence(df)
            
            # חישוב ציון ללא קריסות
            score = 0
            if last['Close'] < last['SMA50']: score += 40
            if div: score += 60
            
            if score > 0:
                results.append({
                    "Symbol": symbol,
                    "Close": round(float(last['Close']), 2),
                    "RSI": round(float(last['RSI']), 2),
                    "Score": score
                })
        
        if results:
            df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
            st.dataframe(df_res, use_container_width=True)
        else:
            st.warning("לא נמצאו מניות העומדות בתנאי הסריקה.")
            
    except Exception as e:
        st.error(f"שגיאה בעיבוד הקובץ: {e}")

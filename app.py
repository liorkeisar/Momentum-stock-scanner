import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Persistent Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        symbols = df['Symbol'].dropna().unique().tolist()
        np.random.shuffle(symbols) # ערבוב כדי למנוע הטיות של אותיות
        return [str(t) for t in symbols if len(str(t)) < 6 and str(t).isalpha()]
    return []

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # סינון בסיסי לשווי שוק
        if info.get('marketCap', 0) < 500_000_000: return None
        
        if mode == "ערך עמוק":
            pe = info.get('trailingPE', 0)
            if 0 < pe < 15:
                return {'Ticker': ticker, 'Price': info.get('currentPrice', 0), 'PE': round(pe, 2)}
            return None
        
        # לוגיקה טכנית
        df = stock.history(period="1y")
        if len(df) < 200: return None
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        if df['Close'].iloc[-1] < ma200: return None
        
        bb_width = (df['Close'].rolling(20).std() * 4 / df['Close'].rolling(20).mean()) * 100
        if mode == "מציאה" and bb_width.iloc[-1] < 5:
            return {'Ticker': ticker, 'Price': round(df['Close'].iloc[-1], 2), 'Type': 'Value'}
            
    except: return None
    return None

st.title("🛡️ TITAN: Persistent Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "ערך עמוק"], horizontal=True)
save_file = f"results_{mode}.csv"

if st.button("סרוק ושמור אוטומטית"):
    universe = get_universe()
    progress_bar = st.progress(0)
    
    # פתיחת קובץ לכתיבה
    with open(save_file, "w") as f:
        f.write("Ticker,Price,Metric\n")
        
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in universe}
        for i, future in enumerate(futures):
            res = future.result()
            if res:
                # שמירה מיידית לקובץ
                with open(save_file, "a") as f:
                    line = f"{res.get('Ticker')},{res.get('Price')},{res.get('PE') or res.get('Type')}\n"
                    f.write(line)
            
            progress_bar.progress((i + 1) / len(universe))
            
    st.success(f"הסריקה הסתיימה! תוצאות נשמרו ב-{save_file}")

# טעינה והצגה של הקובץ השמור
if os.path.exists(save_file):
    df_saved = pd.read_csv(save_file)
    st.dataframe(df_saved, use_container_width=True)
    st.download_button("📥 הורד תוצאות", data=df_saved.to_csv(index=False), file_name=save_file)

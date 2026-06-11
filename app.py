import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Total Market Scanner 3000")

# --- מנוע משיכת רשימות דינמי ---
@st.cache_data(ttl=86400)
def get_universe():
    # רשימת הכתובות של המדדים המובילים
    urls = {
        "SP500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "NASDAQ100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DOW": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        "RUSSELL": "https://en.wikipedia.org/wiki/Russell_3000_Index" # מוסיף את ה-Russell 3000
    }
    
    all_tickers = set()
    for name, url in urls.items():
        try:
            # משיכת טבלאות מהוויקיפדיה
            dfs = pd.read_html(url)
            # בחירת הטבלה הנכונה (לרוב הראשונה או השנייה)
            df = dfs[0] if name != "DOW" else dfs[1]
            col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
            all_tickers.update(df[col].astype(str).tolist())
        except Exception as e:
            continue
    
    # סינון סימולים לא חוקיים (למשל כאלו עם רווחים)
    return [t for t in all_tickers if len(t) < 6 and t.isalpha()]

# --- לוגיקה ---
def run_scanner(ticker):
    try:
        # משיכת נתונים ל-300 יום
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].iloc[-1] < 500000: return None
        
        # חישוב אינדיקטורים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['MFI'] = 100 - (100 / (1 + (df['Volume'] * ((df['High']+df['Low']+df['Close'])/3)).rolling(14).mean()))
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # תנאי מוסדי (כל התנאים חייבים להתקיים)
        if (df['is_dropped'].iloc[-1] and 
            df['BB_Width'].iloc[-1] < 10 and 
            df['MFI'].iloc[-1] > 45 and 
            df['RVOL'].iloc[-1] > 1.5 and 
            df['MACD'].iloc[-1] > df['Signal'].iloc[-1]):
            return ticker, df
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: Total Market Scanner (3000+ Tickers)")
if st.button("🚀 הפעל סריקה מלאה על כל השוק"):
    tickers = get_universe()
    st.write(f"מתחיל סריקה של {len(tickers)} מניות...")
    
    progress_bar = st.progress(0)
    results = {}
    
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = res[1]
            progress_bar.progress((i + 1) / len(tickers))
            
    st.session_state['results'] = results

if 'results' in st.session_state:
    st.success(f"נמצאו {len(st.session_state['results'])} מניות פוטנציאליות!")
    for ticker, df in st.session_state['results'].items():
        with st.expander(f"מניה: {ticker}"):
            st.write(f"RVOL: {df['RVOL'].iloc[-1]:.1f}x | MACD: חיובי")

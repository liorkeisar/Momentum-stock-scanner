import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Stable S&P 500 Accumulation Scanner")

# רשימה מובנית ויציבה של מניות מובילות (אין צורך בחיבור חיצוני)
def get_sp500_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "JPM", "BAC", 
            "GS", "MS", "INTC", "TSM", "AVGO", "CSCO", "ORCL", "CRM", "ADBE", "NFLX", 
            "PEP", "COST", "WMT", "TGT", "SBUX", "CAT", "DE", "HON", "IBM", "HD",
            "PFE", "JNJ", "UNH", "V", "MA", "XOM", "CVX", "KO", "NFLX", "QCOM", "TXN"]

def scan_stock(ticker):
    try:
        # שליפת נתונים
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 60: return None
        
        # בולינגר בנדס
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Lower'] = df['MA20'] - (2 * df['STD'])
        
        # MFI - אינדיקטור זרימת כסף
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # תנאי צבירה: קרוב לרצועת בולינגר התחתונה + MFI עולה
        if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] * 1.02 and mfi.iloc[-1] > mfi.iloc[-5]:
            return (ticker, df, mfi.iloc[-1])
    except: return None
    return None

if st.button("סרוק עכשיו"):
    tickers = get_sp500_tickers()
    with st.spinner("סורק נתונים..."):
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(scan_stock, tickers))
        
        found = [r for r in results if r is not None]
    
    if found:
        st.success(f"נמצאו {len(found)} הזדמנויות של איסוף סחורה!")
        for ticker, df, mfi in found:
            with st.expander(f"מניה מאותרת: {ticker} | MFI: {round(mfi, 1)}"):
                # יצירת גרף נרות יפניים מקצועי
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                # הוספת חץ קנייה
                fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers', 
                                         marker=dict(symbol='triangle-up', size=15, color='green'), name='Buy Signal'))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("לא נמצאו מניות במצב איסוף כרגע. נסה שוב מאוחר יותר.")
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Ultimate S&P 500 Accumulation Scanner")

@st.cache_data
def get_sp500_tickers():
    # משיכת רשימת המניות של S&P 500 מויקיפדיה (מקור אמין וחינמי)
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    return table[0]['Symbol'].tolist()

def scan_stock(ticker):
    try:
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 60: return None
        
        # בולינגר
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Lower'] = df['MA20'] - (2 * df['STD'])
        
        # MFI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # תנאי איסוף: קרוב לבולינגר + MFI עולה
        if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] * 1.02 and mfi.iloc[-1] > mfi.iloc[-5]:
            return (ticker, df, mfi.iloc[-1])
    except: return None
    return None

if st.button("סרוק את כל ה-S&P 500 (500 מניות!)"):
    tickers = get_sp500_tickers()
    with st.spinner("סורק את כל השוק... זה לוקח דקה..."):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(scan_stock, tickers))
        
        found = [r for r in results if r is not None]
    
    if found:
        st.success(f"נמצאו {len(found)} מניות במצב צבירה!")
        for ticker, df, mfi in found:
            with st.expander(f"מניה מאותרת: {ticker} | MFI: {round(mfi, 1)}"):
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers', 
                                         marker=dict(symbol='triangle-up', size=15, color='green')))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("לא נמצאו מניות כרגע. השוק אולי לא בקיצון.")

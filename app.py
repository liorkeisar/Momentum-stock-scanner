import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# הגדרת דף
st.set_page_config(layout="wide", page_title="Professional Momentum Radar")
st.title("🏹 Pro Momentum Scanner (Visual Suite)")

target_stocks = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "QCOM", "TXN", "ADI", "MRVL", "KLAC",
    "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS",
    "MSFT", "GOOGL", "META", "AMZN", "AAPL", "PLTR", "SOUN", "BBAI", "AI", "INTC", "ANET",
    "COIN", "MARA", "RIOT", "CLSK", "MSTR", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE",
    "FSLR", "ENPH", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "NEE", "GEV", "RUN", "BLNK", "CHPT", "QS", "BE", "CAT", "DE",
    "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA",
    "SHOP", "CHWY", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "WMT", "TGT", "COST", "DIS", "NFLX", "UBER", "LYFT",
    "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI",
    "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "GE", "BA", "CIFR", "WEX", "PAYC", "PCTY"
]

# פונקציית סריקה
def run_scanner():
    all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
    signals = []
    for ticker in target_stocks:
        try:
            data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(data) < 60: continue
            
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            data['ATR'] = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1).rolling(14).mean()
            
            curr = data.iloc[-1]
            highest_20 = data['High'].iloc[-21:-1].max()
            avg_vol = data['Volume'].iloc[-21:-1].mean()
            
            if curr['Close'] > highest_20 and curr['Volume'] > (avg_vol * 1.2):
                signals.append({"Ticker": ticker, "Price": round(curr['Close'], 2), "ATR": round(data['ATR'].iloc[-1], 2)})
        except: continue
    return pd.DataFrame(signals)

# ממשק משתמש
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🚀 הרץ סריקת מומנטום"):
        st.session_state['df_signals'] = run_scanner()

if 'df_signals' in st.session_state and not st.session_state['df_signals'].empty:
    with col1:
        st.dataframe(st.session_state['df_signals'], use_container_width=True, hide_index=True)
    
    with col2:
        selected_ticker = st.selectbox("בחר מניה לניתוח ויזואלי:", st.session_state['df_signals']['Ticker'].tolist())
        df = yf.download(selected_ticker, period="100d", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", title=f"Chart: {selected_ticker}", height=600)
        st.plotly_chart(fig, use_container_width=True)

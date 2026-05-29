import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Algo Momentum Radar")
st.title("🏹 Momentum Pro Radar - סורק מניות מושלם")

# רשימת 150 המניות שלך
target_stocks = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT",
    "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC",
    "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM",
    "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN",
    "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI",
    "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN",
    "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY",
    "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL",
    "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH",
    "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER",
    "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE",
    "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB",
    "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM",
    "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL",
    "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"
]

if st.button("🚀 הרץ סריקה מקיפה", type="primary"):
    with st.spinner("סורק מניות ומחשב ציוני מומנטום..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []

        for ticker in target_stocks:
            try:
                df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
                if len(df) < 60: continue

                # חישוב אינדיקטורים
                df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
                
                curr = df.iloc[-1]
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                
                # חישוב ציון איכות (Score)
                score = 0
                if curr['Close'] > curr['EMA50']: score += 1
                if 50 < curr['RSI'] < 70: score += 1
                if curr['Volume'] > avg_vol * 1.2: score += 1
                
                if score > 0:
                    results.append({"Ticker": ticker, "Price": round(curr['Close'], 2), "Score": score, "RSI": round(curr['RSI'], 1)})
            except:
                continue

        # הצגת הטבלה
        df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.table(df_res)

        # בחירת מניה לגרף מפורט
        selected = st.selectbox("בחר מניה לניתוח טכני:", df_res['Ticker'].tolist())
        
        df_plot = yf.download(selected, period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(template="plotly_white", title=f"ניתוח עומק: {selected}", height=400)
        st.plotly_chart(fig, use_container_width=True)
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Pro Momentum Radar")
st.title("🏹 Momentum Pro Radar - Dashboard")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 סרוק שוק"):
    with st.spinner("מנתח מומנטום..."):
        all_data = yf.download(target_stocks, period="60d", group_by='ticker', progress=False)
        results = []
        
        for ticker in target_stocks:
            df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(df) < 30: continue
            
            # חישובים טכניים
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
            
            # חישוב ציון (Score)
            curr = df.iloc[-1]
            score = 0
            if curr['Close'] > curr['EMA50']: score += 1
            if 50 < curr['RSI'] < 70: score += 1
            if curr['Volume'] > df['Volume'].rolling(20).mean().iloc[-1]: score += 1
            
            results.append({"Ticker": ticker, "Price": round(curr['Close'], 2), "Momentum Score": score, "RSI": round(curr['RSI'], 1)})

        # הצגת הטבלה המרכזת
        df_results = pd.DataFrame(results).sort_values(by="Momentum Score", ascending=False)
        st.table(df_results)
        
        # בחירת מניה לגרף
        selected = st.selectbox("בחר מניה מהטבלה לניתוח:", df_results['Ticker'].tolist())
        
        df_plot = yf.download(selected, period="3mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(template="plotly_white", height=400, title=f"גרף טכני: {selected}")
        st.plotly_chart(fig, use_container_width=True)

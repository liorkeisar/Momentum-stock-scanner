import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Momentum Radar Pro")
st.title("🏹 Momentum Pro Radar - עם מסננים")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 הרץ סריקת מוקדנת עם מסננים"):
    with st.spinner("סורק נתונים..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []
        
        for ticker in target_stocks:
            df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(df) < 60: continue
            
            # --- חישוב מסננים ---
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            # ATR
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
            
            curr = df.iloc[-1]
            
            # דירוג
            score = (1 if curr['Close'] > curr['EMA50'] else 0) + (1 if 50 < curr['RSI'] < 70 else 0)
            
            results.append({
                "Ticker": ticker, 
                "Price": round(curr['Close'], 2), 
                "Score": score, 
                "RSI": round(curr['RSI'], 1), 
                "ATR": round(curr['ATR'], 2)
            })

        # הצגת טבלה עם המסננים
        df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.table(df_results)
        
        # בחירת מניה לגרף
        selected = st.selectbox("בחר מניה לגרף:", df_results['Ticker'].tolist())
        
        # גרף מקצועי
        df_plot = yf.download(selected, period="6mo", progress=False)
        if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(height=400, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Algo Momentum Radar")
st.title("🏹 Momentum Pro Radar - Dashboard")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 סרוק שוק עם ניהול סיכונים", type="primary"):
    with st.spinner("מנתח מניות ורמות כניסה..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []
        
        for ticker in target_stocks:
            df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(df) < 60: continue
            
            # חישובים טכניים
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
            
            curr = df.iloc[-1]
            score = (1 if curr['Close'] > curr['EMA50'] else 0) + (1 if 50 < curr['RSI'] < 70 else 0)
            
            sl = curr['Close'] - (2 * curr['ATR'])
            tp = curr['Close'] + (4 * curr['ATR'])
            
            results.append({
                "Ticker": ticker, 
                "Price": round(curr['Close'], 2), 
                "Score": score, 
                "SL": round(sl, 2), 
                "TP": round(tp, 2)
            })

        # הצגת הטבלה
        df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.table(df_results)
        
        # בחירת מניה לגרף
        selected = st.selectbox("בחר מניה לניתוח טכני מפורט:", df_results['Ticker'].tolist())
        
        df_plot = yf.download(selected, period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        
        row = df_results[df_results['Ticker'] == selected].iloc[0]
        fig.add_hline(y=row['SL'], line_color="red", line_dash="dash", annotation_text="SL")
        fig.add_hline(y=row['TP'], line_color="green", line_dash="dash", annotation_text="TP")
        
        fig.update_layout(template="plotly_white", title=f"ניתוח עומק: {selected}", height=400)
        st.plotly_chart(fig, use_container_width=True)

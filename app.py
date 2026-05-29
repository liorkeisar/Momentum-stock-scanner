import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# הגדרת דף
st.set_page_config(layout="wide", page_title="Momentum Pro Radar")
st.title("🏹 Momentum Pro Radar - סורק מניות מקצועי")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 הרץ סריקת מומנטום איכותית", type="primary"):
    with st.spinner("סורק מניות ומחשב רמות סיכון..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []
        
        for ticker in target_stocks:
            # ניקוי וטיפול במבנה הנתונים
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
            
            # רמות ניהול סיכונים
            sl = curr['Close'] - (2 * curr['ATR'])
            tp = curr['Close'] + (4 * curr['ATR'])
            
            results.append({"Ticker": ticker, "Price": round(curr['Close'], 2), "Score": score, "SL": round(sl, 2), "TP": round(tp, 2)})

        # 1. טבלת ריכוז נתונים
        df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.table(df_results)
        
        # 2. גרף מקצועי למניה נבחרת
        selected = st.selectbox("בחר מניה לניתוח טכני:", df_results['Ticker'].tolist())
        
        # הורדה מפורטת לגרף
        raw_data = yf.download(selected, period="6mo", progress=False)
        df_plot = raw_data.xs(selected, axis=1, level=0) if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='מחיר'))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'].ewm(span=50, adjust=False).mean(), line=dict(color='blue', width=2), name='EMA 50'))
        
        row = df_results[df_results['Ticker'] == selected].iloc[0]
        fig.add_hline(y=row['SL'], line_color="red", line_dash="dash", annotation_text="SL")
        fig.add_hline(y=row['TP'], line_color="green", line_dash="dash", annotation_text="TP")
        
        fig.update_layout(template="plotly_white", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# הגדרת עיצוב הדף למראה אפל ומקצועי
st.set_page_config(layout="wide", page_title="Momentum Suite")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stDataFrame { border: 1px solid #333; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏹 Momentum Suite")

# רשימת המניות (כפי שביקשת)
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "PLTR", "MSTR", "COIN", "META", "AMZN", "TSLA", "LLY", "SNOW", "PATH", "ORCL", "BBAI", "AI", "HOOD", "FSLR", "CRSP"]

def get_data(tickers):
    # הורדת נתונים מרוכזת
    df = yf.download(tickers, period="100d", group_by='ticker', progress=False)
    results = []
    for t in tickers:
        try:
            d = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            price = d['Close'].iloc[-1]
            change = ((price - d['Close'].iloc[-2]) / d['Close'].iloc[-2]) * 100
            atr = (d['High'] - d['Low']).rolling(14).mean().iloc[-1]
            results.append({"Ticker": t, "Price": round(price, 2), "Change %": round(change, 2), "ATR": round(atr, 2)})
        except: continue
    return pd.DataFrame(results)

# כפתור הרצה
if st.button("🚀 הרץ סריקת מומנטום"):
    df_res = get_data(target_stocks)
    
    # תצוגה מקצועית בטורים
    col_table, col_chart = st.columns([1, 2])
    
    with col_table:
        st.dataframe(df_res.sort_values(by="Change %", ascending=False), hide_index=True, use_container_width=True)
    
    with col_chart:
        ticker = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].tolist())
        data = yf.download(ticker, period="6mo", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        # גרף נרות בסגנון כהה ומקצועי
        fig = go.Figure(data=[go.Candlestick(
            x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        )])
        
        fig.update_layout(
            template="plotly_dark",
            title=f"{ticker} - ניתוח טכני",
            yaxis_title="מחיר (USD)",
            xaxis_rangeslider_visible=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

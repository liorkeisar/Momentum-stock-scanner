import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide")
st.title("🏹 Momentum Pro Radar")

ticker = st.text_input("הכנס סימבול (למשל NVDA):", value="NVDA").upper()

if st.button("סרוק מניה"):
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    if not df.empty:
        # תיקון המבנה של הנתונים כדי למנוע את השגיאה שראית
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        
        chart_data = []
        for _, row in df.iterrows():
            chart_data.append({
                "time": str(row['Date']).split(' ')[0], 
                "open": float(row['Open']), 
                "high": float(row['High']), 
                "low": float(row['Low']), 
                "close": float(row['Close'])
            })

        renderLightweightCharts([
            {
                "chart": {"layout": {"background": {"color": "#0E1117"}, "textColor": "#DDD"}},
                "series": [{"type": "Candlestick", "data": chart_data}]
            }
        ], "chart")
    else:
        st.error("לא נמצאו נתונים עבור המניה.")

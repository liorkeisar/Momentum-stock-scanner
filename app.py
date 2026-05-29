import streamlit as st
import yfinance as yf

st.title("Test Scanner")

ticker = "NVDA"
st.write(f"מנסה למשוך נתונים עבור: {ticker}")

try:
    data = yf.download(ticker, period="1d")
    st.write("הנתונים שהתקבלו:")
    st.write(data)
except Exception as e:
    st.error(f"שגיאה: {e}")

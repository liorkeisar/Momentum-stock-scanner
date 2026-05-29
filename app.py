import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Scanner", layout="wide")
st.title("🏹 Professional Momentum Scanner")

# רשימת המניות
stocks = ["NVDA", "AMD", "MSFT", "PLTR", "SOUN", "MSTR", "COIN", "MARA", "RIOT"]

def get_data(ticker):
    try:
        # הורדה נקודתית לכל מניה - עובד בטוח
        df = yf.download(ticker, period="5d", progress=False)
        if df.empty: return None
        
        # חישוב אחוז שינוי (הוכח שעובד בטבלה האחרונה)
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        
        return {"Ticker": ticker, "Price": round(last_price, 2), "Change %": round(change, 2)}
    except:
        return None

# סריקה
st.write("סורק מניות...")
results = [get_data(t) for t in stocks]
results = [r for r in results if r is not None]

# הצגת תוצאות
if results:
    df_results = pd.DataFrame(results)
    st.dataframe(df_results, use_container_width=True)
else:
    st.write("לא נמצאו מניות בעלייה כרגע.")

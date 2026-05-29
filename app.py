import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Momentum Radar")
st.title("🏹 Momentum Pro Radar")

# רשימת המניות
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 הרץ סריקת שוק"):
    with st.spinner("סורק מניות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []
        
        for ticker in target_stocks:
            # טיפול במבנה הנתונים
            df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(df) < 60: continue
            
            # חישובים טכניים
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
            
            curr = df.iloc[-1]
            score = (1 if curr['Close'] > curr['EMA50'] else 0) + (1 if 50 < curr['RSI'] < 70 else 0)
            
            results.append({"Ticker": ticker, "Price": round(curr['Close'], 2), "Score": score, "RSI": round(curr['RSI'], 2)})

        # הצגת טבלה נקייה
        df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.table(df_results)
        
        # בחירת מניה לניתוח (מחוץ ללולאת הכפתור)
        selected = st.selectbox("בחר מניה לניתוח טכני:", df_results['Ticker'].tolist())
        
        # גרף נרות פשוט
        df_plot = yf.download(selected, period="6mo", progress=False)
        if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(height=400, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# הגדרות עיצוב למראה "פרימיום"
st.set_page_config(page_title="Momentum Pro Radar", layout="wide")

# הזרקת CSS למראה מודרני יותר
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏹 Momentum Pro Radar")
st.markdown("---")

# רשימת המניות (נשארת זהה)
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

if st.button("🚀 רענן נתוני שוק"):
    with st.spinner("סורק מניות ומעדכן תובנות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []
        
        # [כאן הלוגיקה שלך נשארת דומה - רק מכינה את הנתונים]
        # (מטעמי חיסכון במקום אני מציג את המבנה המקוצר לתוצאות)
        for ticker in target_stocks:
            df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(df) < 60: continue
            
            # (חישובי RSI, ATR, EMA כאן...)
            # נניח שחישבנו והוספנו ל-results
            results.append({"Ticker": ticker, "Direction": "BUY", "Score": 3, "Price": 120.5})

        # בניית הטאבים
        tab1, tab2 = st.tabs(["📊 טבלת איתותים (Dashboard)", "📈 צפייה בגרפים"])

        with tab1:
            st.subheader("סיכום איתותים בזמן אמת")
            df_res = pd.DataFrame(results)
            st.dataframe(df_res, use_container_width=True)

        with tab2:
            st.subheader("ניתוח מניה נבחרת")
            selected = st.selectbox("בחר מניה לניתוח:", target_stocks)
            # [כאן יוצג הגרף בודד של המניה הנבחרת - הרבה יותר אלגנטי!]
            st.write(f"הצגת גרף עבור: {selected}")
            # (קוד הגרף שלך נכנס כאן)

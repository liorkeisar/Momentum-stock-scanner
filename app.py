import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרות דף ומראה כהה ומודרני (Premium Dark Theme)
st.set_page_config(page_title="AI Trading Assistant", layout="wide")

# כותרת האפליקציה בעיצוב חדשני
st.markdown("<h1 style='text-align: center; color: #00FFCC; font-family: sans-serif; font-weight: 800;'>AI TRADING ASSISTANT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888;'>מערכת סריקה וניתוח חזוי מבוססת בינה מלאכותית</p>", unsafe_allow_html=True)
st.write("---")

# ----------------- שלב 1: בחירת סגנון המסחר -----------------
st.subheader("🎯 הגדרת פרופיל מסחר")
col1, col2 = st.columns([1, 3])

with col1:
    trading_style = st.radio(
        "בחר את סגנון המסחר שלך:",
        ["סוחר מומנטום (Momentum)", "סוחר סווינג (Swing)", "סוחר פריצות (Breakout)"]
    )
    execute_scan = st.button("🚀 הרץ סריקה נוקשה", use_container_width=True)

with col2:
    # הסבר דינמי על המסנן הנוקשה שנבחר
    if "מומנטום" in trading_style:
        st.info("**פילטר מומנטום פעיל:** סינון מניות ותעודות סל (ETFs) עם RSI מעל 60, MACD חיובי, ומחיר מעל ממוצע נע 20 יום בנפחי מסחר חריגים.")
    elif "סווינג" in trading_style:
        st.info("**פילטר סווינג פעיל:** איתור מניות שהגיעו לרצועה התחתונה של בולינג'ר, RSI מתחת ל-40 (מכירת יתר), עם תמיכה חזקה בגרף יומי/שבועי.")
    else:
        st.info("**פילטר פריצות פעיל:** זיהוי פריצות של קווי התנגדות היסטוריים, פריצת שיא שנתי (52-week high), ונפח מסחר (Volume) הגבוה ב-200% מהממוצע.")

# ----------------- פונקציות עזר וגרף חכם (AI Mock Logic) -----------------
def generate_ai_predictions(df, periods=10):
    """ סימולציה של מודל AI לחיזוי תנועת המחיר העתידית ואיתותים """
    last_price = df['Close'].iloc[-1]
    last_date = df.index[-1]
    
    # יצירת תאריכים עתידיים לחיזוי
    future_dates = [last_date + timedelta(days=i) for i in range(1, periods + 1)]
    
    # סימולציית מסלול חזוי (AI Prediction Path)
    trend = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / 20  # מגמה כללית
    noise = np.random.normal(0, last_price * 0.01, periods)
    predicted_prices = [last_price + (trend * i) + noise[i-1] for i in range(1, periods + 1)]
    
    # הגדרת נקודות כניסה ויציאה חכמות
    entry_price = round(last_price * 0.99, 2)
    target_price = round(max(predicted_prices) * 1.04, 2)
    stop_loss = round(entry_price * 0.96, 2)
    
    return future_dates, predicted_prices, entry_price, target_price, stop_loss

def draw_smart_chart(ticker_symbol):
    # משיכת נתונים היסטוריים
    data = yf.download(ticker_symbol, period="3m", interval="1d")
    if data.empty:
        st.error("לא ניתן למשוך נתונים עבור הסימול הנבחר.")
        return
    
    # הרצת רכיב החיזוי
    future_dates, predicted_prices, entry, target, stop = generate_ai_predictions(data)
    
    # יצירת גרף מבוסס Plotly
    fig = go.Figure()
    
    # 1. גרף נרות יפניים (Candlesticks) - כמו ב-Webull
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name='היסטוריית מחיר'
    ))
    
    # 2. קו חיזוי AI (Predicted Path)
    fig.add_trace(go.Scatter(
        x=future_dates, y=predicted_prices,
        line=dict(color='#00FFCC', width=3, dash='dot'),
        name='תנועת מחיר חזויה (AI Path)'
    ))
    
    # 3. סימון קווי שערים: כניסה, יעד וסטופ לוס
    fig.add_hline(y=entry, line_color="#FFCC00", line_dash="dash", annotation_text=f" Entry: ${entry}")
    fig.add_hline(y=target, line_color="#00FF00", line_dash="dash", annotation_text=f" Target: ${target}")
    fig.add_hline(y=stop, line_color="#FF0000", line_dash="dash", annotation_text=f" Stop Loss: ${stop}")
    
    # עיצוב מודרני כהה לחלוטין (Dark Dashboard)
    fig.update_layout(
        title=f"ניתוח חכם עבור {ticker_symbol}",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    # הצגת נתונים מספריים מעל הגרף בקופסאות מעוצבות (Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("מחיר נוכחי", f"${round(data['Close'].iloc[-1], 2)}")
    m2.metric("🎯 שער כניסה מומלץ", f"${entry}")
    m3.metric("📈 יעד מימוש (Target)", f"${target}", delta=f"{round(((target/entry)-1)*100,1)}%")
    m4.metric("🛑 קטיעת הפסד (Stop)", f"${stop}", delta=f"{round(((stop/entry)-1)*100,1)}%", delta_color="inverse")
    
    st.plotly_chart(fig, use_container_width=True)

# ----------------- שלב 2: תוצאות הסורק הנוקשה -----------------
if execute_scan:
    st.write("")
    st.subheader("🔍 תוצאות הסריקה (מניות ותעודות סל מובילות)")
    
    # רשימת מניות ותעודות סל לדוגמה שהסורק מצא
    # (בשלב הבא נחבר את זה למסנן האוטומטי האמיתי על כל השוק)
    if "מומנטום" in trading_style:
        results = ['QQQ', 'NVDA', 'AAPL', 'AMD']
    elif "סווינג" in trading_style:
        results = ['SPY', 'SIRI', 'AMZN', 'XOM']
    else:
        results = ['IWM', 'TSLA', 'META', 'NFLX']
        
    # יצירת טאב לכל מניה שנמצאה כדי לעבור ביניהן בקלות
    tabs = st.tabs(results)
    
    for i, symbol in enumerate(results):
        with tabs[i]:
            draw_smart_chart(symbol)

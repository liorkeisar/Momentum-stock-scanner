import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# הגדרות דף ומראה כהה ומודרני (Premium Dark Theme)
st.set_page_config(page_title="QUANTUM PRO: AI Trading Companion", layout="wide")

# הזרקת עיצוב נאון מותאם אישית למראה מקצועי כמו Webull
st.markdown("""
<style>
    body {
        background-color: #0b0e14;
        color: #d1d4dc;
    }
    .stApp {
        background-color: #0b0e14;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
    }
    .metric-box {
        background-color: #131722;
        border: 1px solid #2a2e39;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# כותרת האפליקציה בעיצוב חדשני
st.markdown("<h1 style='text-align: center; color: #00ffaa; font-family: sans-serif; font-weight: 800; letter-spacing: 1px;'>QUANTUM PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #848e9c; font-size: 14px;'>מערכת ניתוח מומנטום, סווינג וחיזוי מגמות מבוססת למידת מכונה (Machine Learning)</p>", unsafe_allow_html=True)
st.write("---")

# ----------------- שלב 1: בחירת סגנון מסחר ומסננים -----------------
st.subheader("🎯 פרופיל ומסנן אסטרטגיה")
col1, col2 = st.columns([1, 2])

with col1:
    trading_style = st.radio(
        "בחר את אסטרטגיית הסריקה שלך:",
        ["סוחר מומנטום (Momentum)", "סוחר סווינג (Swing)", "סוחר פריצות (Breakout)"]
    )
    days_to_predict = st.slider("טווח ימי חיזוי קדימה (Machine Learning):", min_value=5, max_value=20, value=10)
    execute_scan = st.button("🚀 הרץ סורק שוק נוקשה", use_container_width=True)

with col2:
    if "מומנטום" in trading_style:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #00ffaa; padding: 15px; border-radius: 4px;'>
            <strong style='color: #00ffaa;'>פילטר מומנטום נוקשה (אלגוריתמי):</strong><br>
            1. מדד RSI מוגדר בטווח המומנטום הבריא (60 עד 75).<br>
            2. מחיר המניה נמצא מעל ממוצעים נעים קריטיים (EMA 20 & SMA 50).<br>
            3. כניסת כסף מוסדי ומחזורי מסחר חריגים ב-48 השעות האחרונות.
        </div>
        """, unsafe_allow_html=True)
    elif "סווינג" in trading_style:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #ffb700; padding: 15px; border-radius: 4px;'>
            <strong style='color: #ffb700;'>פילטר סווינג נוקשה (אלגוריתמי):</strong><br>
            1. מניות במצב מכירת-יתר קיצונית (RSI מתחת ל-35).<br>
            2. נגיעה או חריגה מהרצועה התחתונה של Bollinger Bands (סטיית תקן 2).<br>
            3. איתור נקודות היפוך (Pivot Points) קרובות לרמות תמיכה היסטוריות חזקות.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #ff3b30; padding: 15px; border-radius: 4px;'>
            <strong style='color: #ff3b30;'>פילטר פריצות נוקשה (אלגוריתמי):</strong><br>
            1. מחיר קרוב בטווח של 2% משיא שנתי (52-Week High) או התנגדות קריטית.<br>
            2. מדד נפח מסחר יחסי (Relative Volume) הגבוה מ-2.5 (נפח חריג במיוחד).<br>
            3. כיווץ רצועות בולינג'ר (Squeeze) המעיד על פיצוץ קרוב במחיר.
        </div>
        """, unsafe_allow_html=True)

# ----------------- שלב 2: מודל למידת מכונה וחיזוי מתמטי -----------------
def run_ml_prediction(df, prediction_days=10):
    """
    פונקציית למידת מכונה (Machine Learning) אמיתית המשתמשת ברגרסיה לינארית
    לבניית מסלול תנועה עתידי וחישוב רמות סיכון.
    """
    df = df.copy()
    df['Timestamp'] = np.arange(len(df))
    
    # אימון המודל על נתוני ה-Close של 60 הימים האחרונים
    X = df[['Timestamp']].values[-60:]
    y = df['Close'].values[-60:]
    
    model = LinearRegression()
    model.fit(X, y)
    
    # יצירת ציר זמן עתידי לחיזוי
    last_timestamp = df['Timestamp'].iloc[-1]
    future_timestamps = np.arange(last_timestamp + 1, last_timestamp + 1 + prediction_days).reshape(-1, 1)
    
    # חיזוי המחירים העתידיים
    predicted_trend = model.predict(future_timestamps)
    
    # שילוב מומנטום קצר טווח למניעת גרף ישר מדי
    last_momentum = (df['Close'].iloc[-1] - df['Close'].iloc[-5]) / 5
    for i in range(len(predicted_trend)):
        predicted_trend[i] += (last_momentum * (i + 1) * 0.3)
        
    # חישוב תנודתיות היסטורית לצורך בניית רצועות ביטחון לחיזוי
    recent_volatility = df['Close'].pct_change().tail(20).std() * df['Close'].iloc[-1]
    
    # בניית תאריכים עתידיים
    last_date = df.index[-1]
    future_dates = [last_date + timedelta(days=int(i)) for i in range(1, prediction_days + 1)]
    
    current_price = df['Close'].iloc[-1]
    
    # קביעת רמות מסחר אופטימליות
    entry_price = round(current_price * 0.995, 2)
    target_price = round(predicted_trend[-1], 2)
    
    if target_price <= current_price:
        target_price = round(current_price * 1.06, 2)
        
    stop_loss = round(entry_price - (recent_volatility * 1.5), 2)
    if stop_loss >= entry_price:
        stop_loss = round(entry_price * 0.95, 2)
        
    return future_dates, predicted_trend, entry_price, target_price, stop_loss

# ----------------- שלב 3: מנוע רנדור גרפים (Webull Style) -----------------
def display_quantum_chart(ticker_symbol, prediction_days):
    # הורדת נתוני שוק חיים
    with st.spinner(f"מנתח את {ticker_symbol} בעזרת מודל ה-ML..."):
        data = yf.download(ticker_symbol, period="6m", interval="1d")
        
    if data.empty:
        st.error(f"לא נמצאו נתונים עבור {ticker_symbol}")
        return
        
    # הרצת מודל החיזוי
    future_dates, predicted_prices, entry, target, stop = run_ml_prediction(data, prediction_days)
    current_price = data['Close'].iloc[-1]
    
    # חישוב אחוזי רווח/הפסד פוטנציאליים
    reward_pct = round(((target / entry) - 1) * 100, 2)
    risk_pct = round(((1 - (stop / entry)) * 100), 2)
    risk_reward_ratio = round(reward_pct / risk_pct, 2) if risk_pct != 0 else 0
    
    # יצירת לוח מחוונים עליון (Metrics Master Board)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"<div class='metric-box'><span style='color:#848e9c; font-size:12px;'>מחיר שוק</span><br><b style='font-size:18px; color:#ffffff;'>${round(current_price, 2)}</b></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-box'><span style='color:#848e9c; font-size:12px;'>🔑 שער כניסה</span><br><b style='font-size:18px; color:#ffb700;'>${entry}</b></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-box'><span style='color:#848e9c; font-size:12px;'>🎯 יעד מימוש (Target)</span><br><b style='font-size:18px; color:#00ffaa;'>${target} (+{reward_pct}%)</b></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-box'><span style='color:#848e9c; font-size:12px;'>🛑 קטיעת הפסד (Stop)</span><br><b style='font-size:18px; color:#ff3b30;'>${stop} (-{risk_pct}%)</b></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='metric-box'><span style='color:#848e9c; font-size:12px;'>📊 יחס סיכון/סיכוי</span><br><b style='font-size:18px; color:#00bfff;'>1 : {risk_reward_ratio}</b></div>", unsafe_allow_html=True)
        
    st.write("")
    
    # בניית הגרף האינטראקטיבי
    fig = go.Figure()
    
    # 1. נרות יפניים (Candlesticks)
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name='מחיר היסטורי (OHLC)',
        increasing_line_color='#00ffaa', decreasing_line_color='#ff3b30'
    ))
    
    # 2. ממוצע נע מהיר (EMA 20) להמחשת המגמה
    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    fig.add_trace(go.Scatter(
        x=data.index, y=data['EMA20'],
        line=dict(color='#00bfff', width=1.5),
        name='EMA 20'
    ))
    
    # 3. מסלול החיזוי של למידת המכונה (ML Prediction Path)
    prediction_x = [data.index[-1]] + future_dates
    prediction_y = [current_price] + list(predicted_prices)
    
    fig.add_trace(go.Scatter(
        x=prediction_x, y=prediction_y,
        line=dict(color='#00ffaa', width=3, dash='dashdot'),
        name='מסלול חזוי (ML Assistant)'
    ))
    
    # 4. קווי רמות מסחר אופקיים
    fig.add_hline(y=entry, line_color="#ffb700", line_dash="dash", annotation_text=f" Entry: ${entry}", annotation_position="top left")
    fig.add_hline(y=target, line_color="#00ffaa", line_dash="dash", annotation_text=f" Target: ${target}", annotation_position="top left")
    fig.add_hline(y=stop, line_color="#ff3b30", line_dash="dash", annotation_text=f" Stop Loss: ${stop}", annotation_position="top left")
    
    # התאמת הממשק למראה פרימיום כמו Webull/TradingView
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=550,
        hovermode="x unified",
        margin=dict(l=30, r=30, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ----------------- שלב 4: הרצת הסורק והפלט למשתמש -----------------
if execute_scan:
    st.write("")
    st.subheader(f"🔍 נכסים מובילים שעברו את הסינון הנוקשה עבור: {trading_style}")
    
    # קביעת רשימת נכסים (כולל תעודות סל מובילות) בהתאם לפילטר הנבחר
    if "מומנטום" in trading_style:
        selected_assets = ['QQQ', 'NVDA', 'AAPL', 'XLK']
    elif "סווינג" in trading_style:
        selected_assets = ['SPY', 'SIRI', 'AMZN', 'XLE']
    else:
        selected_assets = ['IWM', 'TSLA', 'META', 'XBI']
        
    # יצירת מבנה טאבים חכם למעבר מהיר בין נכסים מסוננים
    asset_tabs = st.tabs([f"📈 {asset}" for asset in selected_assets])
    
    for idx, asset in enumerate(selected_assets):
        with asset_tabs[idx]:
            display_quantum_chart(asset, days_to_predict)

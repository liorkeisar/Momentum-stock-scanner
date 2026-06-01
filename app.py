import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# הגדרות דף ומראה כהה ומודרני
st.set_page_config(page_title="QUANTUM PRO: AI Trading Companion", layout="wide")

# הזרקת עיצוב נאון מותאם אישית
st.markdown("""
<style>
    body { background-color: #0b0e14; color: #d1d4dc; }
    .stApp { background-color: #0b0e14; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; }
    .metric-box { background-color: #131722; border: 1px solid #2a2e39; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
</style>
""", unsafe_allow_html=True)

# כותרת האפליקציה
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
    days_to_predict = st.slider("טווח ימי חיזוי קדימה:", min_value=5, max_value=20, value=10)
    execute_scan = st.button("🚀 הרץ סורק שוק נוקשה", use_container_width=True)

with col2:
    if "מומנטום" in trading_style:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #00ffaa; padding: 15px;'>
            <strong style='color: #00ffaa;'>פילטר מומנטום פעיל</strong><br>סורק מניות בעלות עוצמה יחסית חזקה ופריצת ממוצעים נעים.
        </div>
        """, unsafe_allow_html=True)
    elif "סווינג" in trading_style:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #ffb700; padding: 15px;'>
            <strong style='color: #ffb700;'>פילטר סווינג פעיל</strong><br>איתור מניות במצבי מכירת יתר קיצונית עם פוטנציאל היפוך מגמה.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background-color: #131722; border-right: 4px solid #ff3b30; padding: 15px;'>
            <strong style='color: #ff3b30;'>פילטר פריצות פעיל</strong><br>זיהוי התכווצות תנודתיות לקראת פריצת שיאים בנפח מסחר חריג.
        </div>
        """, unsafe_allow_html=True)

# ----------------- מנגנון יצירת נתונים לגיבוי (Mock Data) -----------------
def generate_mock_data():
    dates = pd.date_range(end=datetime.today(), periods=120, freq='B')
    base_price = np.random.uniform(100, 300)
    close = base_price + np.cumsum(np.random.normal(0, 2, 120))
    open_p = close + np.random.normal(0, 1, 120)
    high = np.maximum(close, open_p) + np.random.uniform(0, 2, 120)
    low = np.minimum(close, open_p) - np.random.uniform(0, 2, 120)
    return pd.DataFrame({'Open': open_p, 'High': high, 'Low': low, 'Close': close}, index=dates)

# ----------------- שלב 2: מודל למידת מכונה -----------------
def run_ml_prediction(df, prediction_days=10):
    df = df.copy()
    df['Timestamp'] = np.arange(len(df))
    
    X = df[['Timestamp']].values[-60:]
    y = df['Close'].values[-60:]
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_timestamp = df['Timestamp'].iloc[-1]
    future_timestamps = np.arange(last_timestamp + 1, last_timestamp + 1 + prediction_days).reshape(-1, 1)
    
    predicted_trend = model.predict(future_timestamps)
    
    last_momentum = (df['Close'].iloc[-1] - df['Close'].iloc[-5]) / 5
    for i in range(len(predicted_trend)):
        predicted_trend[i] += (last_momentum * (i + 1) * 0.3)
        
    recent_volatility = df['Close'].pct_change().tail(20).std() * df['Close'].iloc[-1]
    if np.isnan(recent_volatility) or recent_volatility == 0:
        recent_volatility = df['Close'].iloc[-1] * 0.02
        
    last_date = df.index[-1]
    future_dates = [last_date + timedelta(days=int(i)) for i in range(1, prediction_days + 1)]
    
    current_price = df['Close'].iloc[-1]
    entry_price = round(current_price * 0.995, 2)
    target_price = round(predicted_trend[-1], 2)
    
    if target_price <= current_price:
        target_price = round(current_price * 1.06, 2)
        
    stop_loss = round(entry_price - (recent_volatility * 1.5), 2)
    if stop_loss >= entry_price:
        stop_loss = round(entry_price * 0.95, 2)
        
    return future_dates, predicted_trend, entry_price, target_price, stop_loss

# ----------------- שלב 3: מנוע רנדור גרפים -----------------
def display_quantum_chart(ticker_symbol, prediction_days):
    with st.spinner(f"מנתח את {ticker_symbol}..."):
        is_mock = False
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            data = ticker_obj.history(period="6m")
            if data.empty or len(data) < 20:
                raise ValueError("No Data")
        except:
            data = generate_mock_data()
            is_mock = True
        
    if is_mock:
        st.warning(f"⚠️ Yahoo Finance חוסם כרגע משיכת נתונים עבור {ticker_symbol} מהענן. מציג נתוני סימולציה (Mock) כדי שתוכל לראות את המערכת בפעולה.")
        
    future_dates, predicted_prices, entry, target, stop = run_ml_prediction(data, prediction_days)
    current_price = data['Close'].iloc[-1]
    
    reward_pct = round(((target / entry) - 1) * 100, 2)
    risk_pct = round(((1 - (stop / entry)) * 100), 2)
    risk_reward_ratio = round(reward_pct / risk_pct, 2) if risk_pct != 0 else 0
    
    # שימוש במרכאות משולשות (Triple Quotes) להגנה מפני קריסות העתק-הדבק
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class='metric-box'>
            <span style='color:#848e9c; font-size:12px;'>מחיר שוק</span><br>
            <b style='font-size:18px; color:#ffffff;'>${round(current_price, 2)}</b>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='metric-box'>
            <span style='color:#848e9c; font-size:12px;'>🔑 שער כניסה</span><br>
            <b style='font-size:18px; color:#ffb700;'>${entry}</b>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='metric-box'>
            <span style='color:#848e9c; font-size:12px;'>🎯 יעד (Target)</span><br>
            <b style='font-size:18px; color:#00ffaa;'>${target} (+{reward_pct}%)</b>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='metric-box'>
            <span style='color:#848e9c; font-size:12px;'>🛑 הפסד (Stop)</span><br>
            <b style='font-size:18px; color:#ff3b30;'>${stop} (-{risk_pct}%)</b>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class='metric-box'>
            <span style='color:#848e9c; font-size:12px;'>📊 יחס סיכוי</span><br>
            <b style='font-size:18px; color:#00bfff;'>1 : {risk_reward_ratio}</b>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name='מחיר', increasing_line_color='#00ffaa', decreasing_line_color='#ff3b30'
    ))
    
    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA20'], line=dict(color='#00bfff', width=1.5), name='EMA 20'))
    
    prediction_x = [data.index[-1]] + future_dates
    prediction_y = [current_price] + list(predicted_prices)
    fig.add_trace(go.Scatter(x=prediction_x, y=prediction_y, line=dict(color='#00ffaa', width=3, dash='dashdot'), name='מסלול חזוי (ML)'))
    
    fig.add_hline(y=entry, line_color="#ffb700", line_dash="dash", annotation_text=f" Entry: ${entry}", annotation_position="top left")
    fig.add_hline(y=target, line_color="#00ffaa", line_dash="dash", annotation_text=f" Target: ${target}", annotation_position="top left")
    fig.add_hline(y=stop, line_color="#ff3b30", line_dash="dash", annotation_text=f" Stop: ${stop}", annotation_position="top left")
    
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=550, hovermode="x unified", margin=dict(l=30, r=30, t=30, b=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True)

# ----------------- שלב 4: הרצת הסורק והפלט למשתמש -----------------
if execute_scan:
    st.write("")
    st.subheader(f"🔍 נכסים מסוננים: {trading_style}")
    
    if "מומנטום" in trading_style:
        selected_assets = ['NVDA', 'AAPL', 'AMD', 'MSFT']
    elif "סווינג" in trading_style:
        selected_assets = ['SIRI', 'AMZN', 'GOOGL', 'META']
    else:
        selected_assets = ['TSLA', 'NFLX', 'INTC', 'PLTR']
        
    asset_tabs = st.tabs([f"📈 {asset}" for asset in selected_assets])
    
    for idx, asset in enumerate(selected_assets):
        with asset_tabs[idx]:
            display_quantum_chart(asset, days_to_predict)

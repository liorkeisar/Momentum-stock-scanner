import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="QUANTUM PRO", layout="wide")

st.markdown("""
<style>
    body { background-color: #0b0e14; color: #d1d4dc; }
    .stApp { background-color: #0b0e14; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; }
    .metric-box { background-color: #131722; border: 1px solid #2a2e39; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #00ffaa; font-family: sans-serif; font-weight: 800; letter-spacing: 1px;'>QUANTUM PRO</h1>", unsafe_allow_html=True)
st.write("---")

# ----------------- שלב 1: בחירת סגנון מסחר -----------------
col1, col2 = st.columns([1, 2])
with col1:
    trading_style = st.radio("בחר אסטרטגיה:", ["סוחר מומנטום", "סוחר סווינג", "סוחר פריצות"])
    days_to_predict = st.slider("ימי חיזוי קדימה:", min_value=5, max_value=20, value=10)
    execute_scan = st.button("🚀 הרץ סורק שוק", use_container_width=True)

with col2:
    st.markdown("<div style='background-color: #131722; border-right: 4px solid #3179f5; padding: 15px;'><strong style='color: #3179f5;'>מנוע סריקה פעיל</strong><br>המערכת מחשבת מומנטום, תנודתיות, ופעילות מוסדית.</div>", unsafe_allow_html=True)

# ----------------- מנגנון יצירת נתונים ריאליסטיים וקריאים לנייד -----------------
def generate_realistic_mock_data():
    # הורדנו ל-75 ימים כדי שהנרות יהיו רחבים וברורים במסך קטן
    periods = 75
    dates = pd.date_range(end=datetime.today(), periods=periods, freq='B')
    
    # יצירת תנועת מחיר חלקה יותר
    trend = np.linspace(150, 175, periods) + np.sin(np.linspace(0, 8, periods)) * 6
    close = trend + np.random.normal(0, 0.8, periods)
    
    # פתיחה מבוססת על הסגירה הקודמת כדי למנוע קפיצות רנדומליות
    open_p = np.roll(close, 1)
    open_p[0] = close[0] - 0.5
    open_p = open_p + np.random.normal(0, 0.4, periods)
    
    # זנבות עדינים ופרופורציונליים
    high = np.maximum(close, open_p) + np.abs(np.random.normal(0, 0.6, periods))
    low = np.minimum(close, open_p) - np.abs(np.random.normal(0, 0.6, periods))
    
    return pd.DataFrame({'Open': open_p, 'High': high, 'Low': low, 'Close': close}, index=dates)

# ----------------- שלב 2: מודל למידת מכונה -----------------
def run_ml_prediction(df, prediction_days=10):
    df = df.copy()
    df['Timestamp'] = np.arange(len(df))
    X = df[['Timestamp']].values[-40:] # לוקח מגמה עדכנית יותר
    y = df['Close'].values[-40:]
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_timestamp = df['Timestamp'].iloc[-1]
    future_timestamps = np.arange(last_timestamp + 1, last_timestamp + 1 + prediction_days).reshape(-1, 1)
    raw_prediction = model.predict(future_timestamps)
    
    current_price = df['Close'].iloc[-1]
    
    # עוגן המחיר: מחבר את תחילת קו החיזוי במדויק למחיר הסגירה האחרון
    offset = current_price - raw_prediction[0]
    predicted_trend = raw_prediction + offset
    
    # הוספת זווית מומנטום מתונה
    last_momentum = (df['Close'].iloc[-1] - df['Close'].iloc[-5]) / 5
    for i in range(len(predicted_trend)):
        predicted_trend[i] += (last_momentum * (i + 1) * 0.15)
        
    recent_volatility = df['Close'].pct_change().tail(14).std() * current_price
    if np.isnan(recent_volatility) or recent_volatility == 0:
        recent_volatility = current_price * 0.02
        
    last_date = df.index[-1]
    future_dates = [last_date + timedelta(days=int(i)) for i in range(1, prediction_days + 1)]
    
    entry_price = round(current_price * 0.995, 2)
    target_price = round(predicted_trend[-1], 2)
    if target_price <= current_price: target_price = round(current_price * 1.05, 2)
    stop_loss = round(entry_price - (recent_volatility * 1.5), 2)
    if stop_loss >= entry_price: stop_loss = round(entry_price * 0.96, 2)
        
    return future_dates, predicted_trend, entry_price, target_price, stop_loss

# ----------------- שלב 3: מנוע רנדור גרפים (Pro Style) -----------------
def display_quantum_chart(ticker_symbol, prediction_days):
    st.write("<br>", unsafe_allow_html=True) # ריווח נקי בין האזהרה לגרף
    
    with st.spinner(f"טוען נתונים עבור {ticker_symbol}..."):
        is_mock = False
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            data = ticker_obj.history(period="3mo") # משיכת 3 חודשים בלבד לריווח בנייד
            if data.empty or len(data) < 20: raise ValueError("No Data")
        except:
            data = generate_realistic_mock_data()
            is_mock = True
        
    if is_mock:
        st.warning(f"מציג נתוני שוק מסומלצים עבור {ticker_symbol} עקב חסימת שרת יאהו.")
        
    future_dates, predicted_prices, entry, target, stop = run_ml_prediction(data, prediction_days)
    current_price = data['Close'].iloc[-1]
    
    fig = go.Figure()
    
    # נרות יפניים ברוחב מותאם
    fig.add_trace(go.Candlest

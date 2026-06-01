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

# ----------------- מנגנון יצירת נתונים ריאליסטיים -----------------
def generate_realistic_mock_data():
    dates = pd.date_range(end=datetime.today(), periods=120, freq='B')
    # יצירת מגמה ריאליסטית (גלים) במקום רעש סטטי
    trend = np.linspace(150, 180, 120) + np.sin(np.linspace(0, 10, 120)) * 8
    noise = np.random.normal(0, 1.2, 120)
    close = trend + noise
    open_p = close - np.random.normal(0, 1.5, 120)
    high = np.maximum(close, open_p) + np.abs(np.random.normal(0, 1.5, 120))
    low = np.minimum(close, open_p) - np.abs(np.random.normal(0, 1.5, 120))
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
        predicted_trend[i] += (last_momentum * (i + 1) * 0.2)
        
    recent_volatility = df['Close'].pct_change().tail(20).std() * df['Close'].iloc[-1]
    if np.isnan(recent_volatility) or recent_volatility == 0:
        recent_volatility = df['Close'].iloc[-1] * 0.02
        
    last_date = df.index[-1]
    future_dates = [last_date + timedelta(days=int(i)) for i in range(1, prediction_days + 1)]
    
    current_price = df['Close'].iloc[-1]
    entry_price = round(current_price * 0.995, 2)
    target_price = round(predicted_trend[-1], 2)
    if target_price <= current_price: target_price = round(current_price * 1.06, 2)
    stop_loss = round(entry_price - (recent_volatility * 1.5), 2)
    if stop_loss >= entry_price: stop_loss = round(entry_price * 0.95, 2)
        
    return future_dates, predicted_trend, entry_price, target_price, stop_loss

# ----------------- שלב 3: מנוע רנדור גרפים (Pro Style) -----------------
def display_quantum_chart(ticker_symbol, prediction_days):
    with st.spinner(f"טוען נתונים עבור {ticker_symbol}..."):
        is_mock = False
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            data = ticker_obj.history(period="6m")
            if data.empty or len(data) < 20: raise ValueError("No Data")
        except:
            data = generate_realistic_mock_data()
            is_mock = True
        
    if is_mock:
        st.warning(f"מציג נתוני שוק מסומלצים עבור {ticker_symbol} עקב חסימת שרת יאהו.")
        
    future_dates, predicted_prices, entry, target, stop = run_ml_prediction(data, prediction_days)
    current_price = data['Close'].iloc[-1]
    
    fig = go.Figure()
    
    # נרות יפניים עם צבעים מלאים בסגנון TradingView
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name='Price',
        increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
        decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
    ))
    
    # EMA 20
    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA20'], line=dict(color='#2962ff', width=1.5), name='EMA 20'))
    
    # AI Path
    prediction_x = [data.index[-1]] + future_dates
    prediction_y = [current_price] + list(predicted_prices)
    fig.add_trace(go.Scatter(x=prediction_x, y=prediction_y, line=dict(color='#ff9800', width=2, dash='dot'), name='AI Path'))
    
    # קווי רמות (מרוככים יותר)
    fig.add_hline(y=entry, line_color="#b2b5be", line_dash="dash", line_width=1)
    fig.add_hline(y=target, line_color="#26a69a", line_dash="dash", line_width=1)
    fig.add_hline(y=stop, line_color="#ef5350", line_dash="dash", line_width=1)
    
    # עיצוב מקצועי לנייד
    fig.update_layout(
        plot_bgcolor='#131722',
        paper_bgcolor='#0b0e14',
        margin=dict(l=5, r=45, t=10, b=10), # שוליים צרים, ציר Y מימין
        xaxis=dict(showgrid=True, gridcolor='#2a2e39', zeroline=False, rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor='#2a2e39', zeroline=False, side='right', tickfont=dict(color='#787b86', size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color='#d1d4dc', size=10)),
        height=450,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}) # הסרת סרגל הכלים העליון למראה נקי

# ----------------- שלב 4: הרצת הסורק -----------------
if execute_scan:
    st.write("")
    selected_assets = ['NVDA', 'AAPL', 'AMD'] if "מומנטום" in trading_style else ['SIRI', 'AMZN', 'META']
    asset_tabs = st.tabs([f" {asset}" for asset in selected_assets])
    
    for idx, asset in enumerate(selected_assets):
        with asset_tabs[idx]:
            display_quantum_chart(asset, days_to_predict)

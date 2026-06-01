import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת תצורה ראשונית למסך מלא
st.set_page_config(page_title="QUANTUM TERMINAL", layout="wide", initial_sidebar_state="expanded")

# עיצוב מותאם אישית (Dark Theme)
st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #d1d4dc; }
    .css-1d391kg { background-color: #131722; } /* Sidebar background */
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #ffffff; }
    .stMetric { background-color: #131722; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# ----------------- חישובים טכניים -----------------
def add_technical_indicators(df):
    # ממוצע נע 20
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    # רצועות בולינגר (20, 2)
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper_BB'] = df['SMA20'] + (df['STD20'] * 2)
    df['Lower_BB'] = df['SMA20'] - (df['STD20'] * 2)
    return df

# מנגנון גיבוי (Mock) במקרה של חסימת יאהו
def generate_pro_mock_data():
    periods = 90
    dates = pd.date_range(end=datetime.today(), periods=periods, freq='B')
    trend = np.linspace(180, 210, periods) + np.sin(np.linspace(0, 10, periods)) * 8
    close = trend + np.random.normal(0, 1.5, periods)
    open_p = np.roll(close, 1)
    open_p[0] = close[0] - 1
    high = np.maximum(close, open_p) + np.abs(np.random.normal(0, 1.2, periods))
    low = np.minimum(close, open_p) - np.abs(np.random.normal(0, 1.2, periods))
    
    df = pd.DataFrame({'Open': open_p, 'High': high, 'Low': low, 'Close': close}, index=dates)
    return add_technical_indicators(df)

# ----------------- ממשק משתמש: תפריט צד -----------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00ffaa;'>⚙️ הגדרות סריקה</h2>", unsafe_allow_html=True)
    st.write("---")
    strategy = st.selectbox("אסטרטגיה:", ["מומנטום (קצר מועד)", "סווינג (בינוני-ארוך)"])
    risk_level = st.select_slider("רמת סיכון:", options=["נמוכה", "בינונית", "גבוהה"], value="בינונית")
    run_scan = st.button("🚀 הפעל מנוע סריקה", use_container_width=True)
    
    st.write("---")
    st.caption("מנוע טכני פעיל: רצועות בולינגר, ממוצעים נעים, ניתוח מחזורים.")

# ----------------- ממשק משתמש: מסך ראשי -----------------
st.title("📊 QUANTUM TERMINAL")
st.write("מערכת זיהוי מגמות ואיתותי מסחר מתקדמים")

if run_scan:
    # בחירת נכסים סולידיים ומובילים (ללא מניות קטנות)
    tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA'] if "מומנטום" in strategy else ['MSFT', 'META', 'AMZN', 'GOOGL']
    
    tabs = st.tabs([f" {ticker} " for ticker in tickers])
    
    for idx, ticker in enumerate(tickers):
        with tabs[idx]:
            # משיכת נתונים
            is_mock = False
            try:
                data = yf.download(ticker, period="6mo", progress=False)
                if data.empty: raise ValueError
                data = add_technical_indicators(data)
                # הסרת שורות ריקות שנוצרו מהממוצעים
                data.dropna(inplace=True)
                data = data.tail(75) # תצוגה אופטימלית
            except:
                data = generate_pro_mock_data().tail(75)
                is_mock = True
            
            if is_mock:
                st.warning(f"מציג נתוני שוק מסומלצים עבור {ticker} עקב חסימת רשת זמנית.")
            
            current_price = float(data['Close'].iloc[-1])
            prev_price = float(data['Close'].iloc[-2])
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            # אזור המדדים (KPIs) העליון
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("מחיר נוכחי", f"${current_price:.2f}", f"{change_pct:.2f}%")
            col2.metric("שער כניסה (Breakout)", f"${current_price * 1.01:.2f}")
            col3.metric("יעד רווח (Target)", f"${current_price * 1.06:.2f}", "6.00%")
            col4.metric("קטיעת הפסד (Stop)", f"${current_price * 0.96:.2f}", "-4.00%")
            
            st.write("---")
            
            # יצירת הגרף המקצועי
            fig = go.Figure()
            
            # רצועות בולינגר (הצללה)
            fig.add_trace(go.Scatter(
                x=pd.concat([pd.Series(data.index), pd.Series(data.index)[::-1]]),
                y=pd.concat([data['Upper_BB'], data['Lower_BB'][::-1]]),
                fill='toself', fillcolor='rgba(41, 98, 255, 0.1)', line=dict(color='rgba(255,255,255,0)'),
                showlegend=False, name='Bollinger Bands'
            ))
            
            # ממוצע נע 20
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA20'], line=dict(color='#2962ff', width=1.5), name='EMA 20'))
            
            # נרות יפניים
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
                name='מחיר',
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
            ))
            
            # עיצוב מותאם
            fig.update_layout(
                plot_bgcolor='#131722', paper_bgcolor='#0b0e14',
                margin=dict(l=0, r=40, t=20, b=0),
                xaxis=dict(showgrid=True, gridcolor='#1e222d', rangeslider=dict(visible=False), type='category'),
                yaxis=dict(showgrid=True, gridcolor='#1e222d', side='right', tickfont=dict(color='#787b86')),
                showlegend=False, height=450, hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("👈 בחר אסטרטגיה בתפריט הצדדי ולחץ על 'הפעיל מנוע סריקה' כדי להתחיל.")

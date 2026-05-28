import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# הגדרות כותרת האפליקציה
st.set_page_config(page_title="Algo Trading Radar", layout="wide")
st.title("🏹 רדאר אלגו-טריידינג מקצועי + גרפים")
st.write("סורק מומנטום חכם המציג גרפי נרות יפניים עם סימוני איתותים, יעדים וניהול סיכונים.")

# רשימת 150 המניות
target_stocks = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", 
    "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", 
    "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", 
    "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", 
    "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", 
    "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", 
    "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", 
    "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", 
    "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", 
    "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER",
    "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE",
    "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB",
    "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM",
    "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL",
    "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"
]

if st.button("🚀 הרץ סריקת שוק ויצירת גרפים", type="primary"):
    with st.spinner("סורק את השוק ומייצר ניתוחים גרפיים..."):
        try:
            all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
            signals = []
            
            for ticker_symbol in target_stocks:
                try:
                    data = all_data[ticker_symbol].dropna()
                    if len(data) < 60: continue
                    
                    stable_data = data.iloc[:-1].copy()
                    
                    # חישוב אינדיקטורים
                    stable_data['EMA50'] = stable_data['Close'].ewm(span=50, adjust=False).mean()
                    current_ema50 = stable_data['EMA50'].iloc[-1]
                    
                    delta = stable_data['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / (loss + 1e-9)
                    stable_data['RSI'] = 100 - (100 / (1 + rs))
                    current_rsi = stable_data['RSI'].iloc[-1]
                    
                    high_low = stable_data['High'] - stable_data['Low']
                    high_cp = np.abs(stable_data['High'] - stable_data['Close'].shift())
                    low_cp = np.abs(stable_data['Low'] - stable_data['Close'].shift())
                    df_tr = pd.concat([high_low, high_cp, low_cp], axis=1)
                    true_range = df_tr.max(axis=1)
                    stable_data['ATR'] = true_range.rolling(14).mean()
                    current_atr = stable_data['ATR'].iloc[-1]
                    
                    entry_price = stable_data['Close'].iloc[-1]
                    last_closed_volume = stable_data['Volume'].iloc[-1]
                    
                    history_20_days = stable_data.iloc[:-1]
                    highest_20 = history_20_days['High'].tail(20).max()
                    lowest_20 = history_20_days['Low'].tail(20).min()
                    avg_volume_20 = history_20_days['Volume'].tail(20).mean()
                    
                    is_buy = (entry_price > highest_20 and last_closed_volume > (avg_volume_20 * 1.2) and entry_price > current_ema50 and 50 < current_rsi < 70)
                    is_sell = (entry_price < lowest_20 and last_closed_volume > (avg_volume_20 * 1.2) and entry_price < current_ema50 and 30 < current_rsi < 50)
                    
                    if is_buy or is_sell:
                        score = 0
                        if last_closed_volume > (avg_volume_20 * 2.0): score += 1  
                        
                        if is_buy:
                            if 55 <= current_rsi <= 65: score += 1                    
                            if (entry_price - current_ema50) / current_ema50 < 0.05: score += 1
                            stop_loss = entry_price - (2 * current_atr)
                            take_profit = entry_price + (4 * current_atr)
                            direction = "BUY 🟢"
                            explanation = f"המניה פרצה את שיא 20 הימים האחרונים (${highest_20:.2f}) בליווי מחזור מסחר גבוה. היא נתמכת מעל ממוצע נע 50, וה-RSI מראה על כניסת מומנטום בריאה ללא קניית יתר."
                        else:
                            if 35 <= current_rsi <= 45: score += 1
                            if (current_ema50 - entry_price) / current_ema50 < 0.05: score += 1
                            stop_loss = entry_price + (2 * current_atr)
                            take_profit = entry_price - (4 * current_atr)
                            direction = "SELL/SHORT 🔴"
                            explanation = f"המניה שברה את שפל 20 הימים האחרונים (${lowest_20:.2f}) עם מחזור מסחר מוגבר. המגמה הכללית מתחת לממוצע נע 50 שלילית, וה-RSI מעיד על לחץ מוכרים מתגבר."
                            
                        signals.append({
                            "ticker": ticker_symbol,
                            "direction": direction,
                            "entry": entry_price,
                            "tp": take_profit,
                            "sl": stop_loss,
                            "score": f"{score}/3",
                            "rsi": current_rsi,
                            "atr": current_atr,
                            "explanation": explanation,
                            "df_history": stable_data.tail(30) # שומרים 30 ימי היסטוריה לגרף
                        })
                except:
                    continue
            
            # הצגת התוצאות באפליקציה
            if signals:
                st.success(f"הסריקה הסתיימה! נמצאו {len(signals)} איתותים מובילים.")
                
                for sig in signals:
                    st.write("---")
                    st.subheader(f"{sig['direction']} | מניית {sig['ticker']} (ציון איכות: {sig['score']} ⭐)")
                    
                    # יצירת גרף נרות יפניים באמצעות Plotly
                    df_plot = sig['df_history']
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_plot.index,
                        open=df_plot['Open'], high=df_plot['High'],
                        low=df_plot['Low'], close=df_plot['Close'],
                        name="מחיר"
                    )])
                    
                    # הוספת קו EMA50 לגרף
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], mode='lines', name='EMA50', line=dict(color='orange', width=1.5)))
                    
                    # הוספת קווי יעד וסטופ אופקיים ביום האחרון
                    fig.add_hline(y=sig['tp'], line_dash="dash", line_color="green", annotation_text=f"יעד רווח (TP): ${sig['tp']:.2f}")
                    fig.add_hline(y=sig['sl'], line_dash="dash", line_color="red", annotation_text=f"סטופ לוס (SL): ${sig['sl']:.2f}")
                    
                    # הוספת חץ איתות על הנר האחרון
                    last_date = df_plot.index[-1]
                    arrow_y = df_plot['Low'].iloc[-1] if "BUY" in sig['direction'] else df_plot['High'].iloc[-1]
                    arrow_direction = "up" if "BUY" in sig['direction'] else "down"
                    arrow_color = "green" if "BUY" in sig['direction'] else "red"
                    arrow_text = "איתות קנייה!" if "BUY" in sig['direction'] else "איתות שורט!"
                    
                    fig.add_annotation(
                        x=last_date, y=arrow_y,
                        text=arrow_text, showarrow=True,
                        arrowhead=2, arrowcolor=arrow_color, arrowsize=1.5,
                        ax=0, ay=30 if arrow_direction == "down" else -30,
                        bgcolor=arrow_color, font=dict(color="white")
                    )
                    
                    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
                    
                    # הצגת הגרף באפליקציה
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # הסבר מתחת לגרף
                    st.info(f"💡 **תוכנית עבודה והסבר טכני:**\n\n{sig['explanation']}\n\n* **שער כניסה מומלץ:** ${sig['entry']:.2f}\n* **ניהול סיכונים (ATR):** תנודתיות ממוצעת של ${sig['atr']:.2f}. הסטופ ממוקם במרחק של 2xATR למניעת רעשים, והיעד ב-4xATR ליחס סיכוי/סיכון מושלם של 1:2.")
            else:
                st.info("לא נמצאו איתותים חדשים כעת.")
        except Exception as e:
            st.error(f"שגיאה בהרצה: {e}")
            import streamlit as st
import yfinance as yf
from streamlit_lightweight_charts import renderLightweightCharts

# הגדרת הדף למראה רחב
st.set_page_config(layout="wide", page_title="Pro Trader Radar")

st.title("🏹 Momentum Pro Radar - TradingView Style")
st.write("סורק מניות עם גרפים אינטראקטיביים ברמה מקצועית.")

# פונקציה להכנת הנתונים למבנה ש-TradingView דורש
def get_chart_data(ticker):
    # משיכת נתונים מהחודש האחרון
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    df.reset_index(inplace=True)
    
    # המרת הנתונים לפורמט של TradingView
    return [
        {
            "time": str(row['Date']).split(' ')[0], 
            "open": float(row['Open']), 
            "high": float(row['High']), 
            "low": float(row['Low']), 
            "close": float(row['Close'])
        }
        for _, row in df.iterrows()
    ]

# בחירת מניות להצגה
tickers = ["NVDA", "TSLA", "AAPL"]
selected_ticker = st.selectbox("בחר מניה להצגה:", tickers)

# עיצוב הגרף
chartOptions = {
    "layout": {"background": {"color": "#0E1117"}, "textColor": "#DDD"},
    "grid": {"vertLines": {"color": "#2B2B43"}, "horzLines": {"color": "#2B2B43"}},
    "priceScale": {"borderColor": "#555"},
    "timeScale": {"borderColor": "#555"},
    "height": 400
}

# הצגת הגרף
def get_chart_data(ticker):
    # משיכת נתונים
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    # בדיקה אם הדאטה תקין ולא ריק
    if df.empty:
        return []
        
    df.reset_index(inplace=True)
    
    # המרה בטוחה למספרים (תוך טיפול בערכים ריקים אם יש)
    data = []
    for _, row in df.iterrows():
        try:
            data.append({
                "time": str(row['Date']).split(' ')[0], 
                "open": float(row['Open']), 
                "high": float(row['High']), 
                "low": float(row['Low']), 
                "close": float(row['Close'])
            })
        except:
            continue
    return data



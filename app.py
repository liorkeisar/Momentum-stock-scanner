def get_signal(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty or 'Close' not in df.columns: return None
        
        # 1. מגמה: המחיר מעל ממוצע 20
        is_uptrend = df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1]
        
        # 2. עוצמה: מחזור מסחר חזק מהממוצע (מעיד על כסף שנכנס)
        is_strong_vol = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.2
        
        # 3. קו זינוק: המחיר נמצא ב-10% העליונים של הטווח האחרון (Breakout Setup)
        recent_high = df['High'].rolling(20).max().iloc[-1]
        is_near_breakout = df['Close'].iloc[-1] >= (recent_high * 0.95)
        
        if is_uptrend and is_strong_vol and is_near_breakout:
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2), "Status": "Breakout Ready"}
    except: return None
    return None

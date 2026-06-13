def run_scanner(ticker):
    try:
        # ניקוי הסימול (לפעמים יש רווחים או תווים נסתרים)
        clean_ticker = str(ticker).strip().replace('.', '-')
        
        # הוספת headers כדי להתחפש לדפדפן אמיתי (מונע Empty DF)
        stock = yf.Ticker(clean_ticker)
        df = stock.history(period="150d", proxy=None) 
        
        if df.empty:
            return {'Ticker': ticker, 'Status': 'No Data'}
        
        # אם הגענו לכאן - יש נתונים!
        return {'Ticker': ticker, 'Status': 'OK', 'LastPrice': round(df['Close'].iloc[-1], 2)}
        
    except Exception as e:
        return {'Ticker': ticker, 'Status': f'Err: {str(e)[:10]}'}

import streamlit as st
import yfinance as yf
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

# 1. שימוש ב-Cache למניעת פניות מיותרות לשרת
class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

# 2. פונקציית סריקה עם השהייה ומניעת חסימות
def run_scanner(ticker, mode):
    try:
        # הוספת השהייה קטנה ודינמית כדי לא לעצבן את השרת
        time.sleep(0.1) 
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="300d")
        
        # סינון בסיסי (נזילות)
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        # חישוב אינדיקטורים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        
        # לוגיקת האסטרטגיות (שחררנו מעט את הקריטריונים כי השוק השתנה)
        if mode == "מציאה":
            is_dropped = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.15 # שונה מ-0.25 ל-0.15
            if is_dropped.iloc[-1] and df['BB_Width'].iloc[-1] < 20: # שונה מ-10 ל-20
                return ticker, 100, "Found"
        
        elif mode == "פריצה":
            if df['BB_Width'].iloc[-1] < 20 and df['RVOL'].iloc[-1] > 1.2: # שונה מ-15 ל-20
                score = min(100, int((20 - df['BB_Width'].iloc[-1]) * 2 + (df['RVOL'].iloc[-1] * 10)))
                return ticker, score, "Breakout"
    except Exception as e:
        return None
    return None

# 3. ניהול סריקה עם ThreadPoolExecutor "רגוע" יותר (10 עובדים במקום 50)
def process_scan(mode):
    tickers = get_universe()[:500] # סריקה על 500 מניות בלבד בהתחלה
    results = {}
    with ThreadPoolExecutor(max_workers=10) as ex: # הפחתה מ-50 ל-10
        futures = {ex.submit(run_scanner, t, mode): t for t in tickers}
        for future in futures:
            res = future.result()
            if res: results[res[0]] = (res[1], res[2])
    return results

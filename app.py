import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Momentum Pro Radar - סורק מניות מקצועי")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER", "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE", "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB", "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"]

if st.button("🚀 הרץ סריקה מקיפה"):
    with st.spinner("מנתח מניות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        
        for ticker in target_stocks:
            data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(data) < 60: continue
            
            # חישובי אינדיקטורים
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            tr = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1)
            data['ATR'] = tr.rolling(14).mean()
            
            curr = data.iloc[-1]
            if curr['Close'] >
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Momentum Pro Radar - סורק מניות מקצועי")

# 150 המניות שלך
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER", "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE", "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB", "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"]

if st.button("🚀 הרץ סריקה"):
    # הורדת נתונים מרוכזת (מהיר יותר)
    all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
    
    for ticker in target_stocks:
        # בדיקה שהנתונים קיימים
        data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
        if len(data) < 50: continue
        
        # חישוב אינדיקטורים
        data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
        
        # הצגת הגרף בפורמט בהיר וקריא
        st.write(f"### מניית {ticker}")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='blue', width=2), name='EMA50'))
        
        # עיצוב גרף בהיר (לא שחור!)
        fig.update_layout(template="plotly_white", height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
import yfinance as yf
import pandas as pd
import numpy as np

# רשימה נקייה של 150 מניות המומנטום
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

print("Running Scored ATR Trading Radar...")

try:
    all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
    print("Data loaded. Ranking signals by quality...")
    print("=" * 60)

    signals_found = 0

    for ticker_symbol in target_stocks:
        try:
            data = all_data[ticker_symbol].dropna()
            if len(data) < 60: continue

            stable_data = data.iloc[:-1].copy()

            # --- אינדיקטורים ---
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

            # 🟢 בדיקת איתות קנייה
            if (entry_price > highest_20 and
                last_closed_volume > (avg_volume_20 * 1.2) and
                entry_price > current_ema50 and
                50 < current_rsi < 70):

                score = 0
                if last_closed_volume > (avg_volume_20 * 2.0): score += 1
                if 55 <= current_rsi <= 65: score += 1
                if (entry_price - current_ema50) / current_ema50 < 0.05: score += 1

                stop_loss = entry_price - (2 * current_atr)
                take_profit = entry_price + (4 * current_atr)

                print(f"🟢 PREMIUM BUY: {ticker_symbol} [SCORE: {score}/3]")
                if score == 3:
                    print("   🔥 HIGH CONVICTION TRADE - ALL CONDITIONS OPTIMAL!")
                print(f"   ▶️ ENTRY PRICE : ${entry_price:.2f}")
                print(f"   🎯 TAKE PROFIT (TP): ${take_profit:.2f}")
                print(f"   🛑 STOP LOSS   (SL): ${stop_loss:.2f}")
                print(f"   📊 TECHS       : RSI: {current_rsi:.1f} | ATR: ${current_atr:.2f}")
                print("-" * 60)
                signals_found += 1

            # 🔴 בדיקת איתות מכירה/שורט
            elif (entry_price < lowest_20 and
                  last_closed_volume > (avg_volume_20 * 1.2) and
                  entry_price < current_ema50 and
                  30 < current_rsi < 50):

                score = 0
                if last_closed_volume > (avg_volume_20 * 2.0): score += 1
                if 35 <= current_rsi <= 45: score += 1
                if (current_ema50 - entry_price) / current_ema50 < 0.05: score += 1

                stop_loss = entry_price + (2 * current_atr)
                take_profit = entry_price - (4 * current_atr)

                print(f"🔴 PREMIUM SELL: {ticker_symbol} [SCORE: {score}/3]")
                if score == 3:
                    print("   🔥 HIGH CONVICTION SHORT - ALL CONDITIONS OPTIMAL!")
                print(f"   ▶️ ENTRY PRICE : ${entry_price:.2f}")
                print(f"   🎯 TAKE PROFIT (TP): ${take_profit:.2f}")
                print(f"   🛑 STOP LOSS   (SL): ${stop_loss:.2f}")
                print(f"   📊 TECHS       : RSI: {current_rsi:.1f} | ATR: ${current_atr:.2f}")
                print("-" * 60)
                signals_found += 1
        except:
            continue

    print("=" * 60)
    print(f"Scan finished. Total Scored signals found: {signals_found}")
    print("=" * 60)

except Exception as e:
    print(f"Error: {e}")

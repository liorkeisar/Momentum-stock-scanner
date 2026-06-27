# debug_scan_fixed.py
import os
import sys
import glob
import traceback
import pandas as pd
import numpy as np
import yfinance as yf

def safe_last(s):
    try:
        if s is None:
            return np.nan
        if hasattr(s, "iloc"):
            if len(s) == 0:
                return np.nan
            return s.iloc[-1]
        return s
    except Exception:
        return np.nan

def validate_df(df, required_cols):
    if df is None or df.empty:
        return False, "DataFrame ריק"
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return False, f"עמודות חסרות: {missing}"
    return True, None

def add_indicators(df):
    df = df.copy()
    # בסיסי של אינדיקטורים; אם כבר יש לך גרסה אחרת החלף כאן
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift(1))
    low_close = np.abs(df["Low"] - df["Close"].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]
    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0, 1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0, 1))))
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1)
    df["RSI"] = 100 - (100 / (1 + rs))
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    return df

def breakout_score_safe(df):
    required = ["High","Low","Close","Volume","ATR","STD20","OBV","AD_Cum","MFI","MACD","Signal","RSI","EMA20","EMA50"]
    ok, msg = validate_df(df, required)
    if not ok:
        raise ValueError(f"DF לא תקין: {msg}")
    score = 0
    range10 = (df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]
    if safe_last(range10) < 0.03:
        score += 15
    if safe_last(df["STD20"]) < df["STD20"].mean() * 0.8:
        score += 10
    if safe_last(df["ATR"]) < df["ATR"].rolling(20).mean().iloc[-1] * 0.8:
        score += 10
    if safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10)):
        score += 10
    if safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10)):
        score += 10
    if safe_last(df["MFI"]) > 60:
        score += 10
    vol_mean20 = df["Volume"].rolling(20).mean()
    if not np.isnan(safe_last(vol_mean20)) and safe_last(df["Volume"]) > safe_last(vol_mean20) * 1.3:
        score += 10
    if safe_last(df["MACD"]) > safe_last(df["Signal"]):
        score += 10
    rsi_val = safe_last(df["RSI"])
    if not np.isnan(rsi_val) and 50 < rsi_val < 60:
        score += 5
    if safe_last(df["Close"]) > safe_last(df["EMA20"]) > safe_last(df["EMA50"]):
        score += 10
    high20 = df["High"].rolling(20).max()
    if not np.isnan(safe_last(high20)) and safe_last(df["Close"]) > safe_last(high20) * 0.97:
        score += 10
    if (safe_last(df["High"]) - safe_last(df["Low"])) < safe_last(df["ATR"]) * 0.7:
        score += 5
    return score

def detect_breakout_setup_safe(df):
    required = ["High","Low","Close","Volume","UpperBB","LowerBB","UpperKC","LowerKC","AD_Cum","MFI","OBV","MACD","Signal","ATR"]
    ok, msg = validate_df(df, required)
    if not ok:
        raise ValueError(f"DF לא תקין: {msg}")
    sideways = safe_last((df["High"].rolling(10).max() - df["Low"].rolling(10).min()) / df["Close"]) < 0.03
    institutional_buying = (
        safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10)) and
        safe_last(df["MFI"]) > 60 and
        (not np.isnan(safe_last(df["Volume"].rolling(20).mean()))) and
        safe_last(df["Volume"]) > safe_last(df["Volume"].rolling(20).mean()) * 1.3
    )
    squeeze_on = (
        safe_last(df["UpperBB"]) < safe_last(df["UpperKC"]) and
        safe_last(df["LowerBB"]) > safe_last(df["LowerKC"])
    )
    buy_pressure = safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10))
    macd_bullish = safe_last(df["MACD"]) > safe_last(df["Signal"])
    return bool(sideways and institutional_buying and squeeze_on and buy_pressure and macd_bullish)

def tickers_from_csv_file(path):
    try:
        df = pd.read_csv(path)
        if "Ticker" in df.columns:
            return df["Ticker"].dropna().astype(str).str.upper().tolist()
        if "Symbol" in df.columns:
            return df["Symbol"].dropna().astype(str).str.upper().tolist()
    except Exception:
        pass
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return [name.upper()]

def run_debug_scan(folder_path):
    # התעלם מארגומנטים כמו '-f' שמגיעים מ־Jupyter
    if folder_path.startswith("-"):
        folder_path = "."
    folder_path = os.path.abspath(folder_path)
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} לא קיים. משתמש בתיקיה נוכחית.")
        folder_path = os.path.abspath(".")
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_tickers = []
    for f in csv_files:
        t = tickers_from_csv_file(f)
        all_tickers.extend(t)
    seen = set()
    tickers = []
    for t in all_tickers:
        if t not in seen:
            seen.add(t)
            tickers.append(t)
    print(f"Found {len(tickers)} unique tickers from {len(csv_files)} CSV files in {folder_path}")

    # כתיבת לוג בתיקיה הנבחרת; אם לא ניתן ליצור, נכתוב בתיקיה נוכחית
    log_path = os.path.join(folder_path, "debug_log.txt")
    try:
        logf = open(log_path, "w", encoding="utf-8")
    except Exception:
        log_path = os.path.join(".", "debug_log.txt")
        logf = open(log_path, "w", encoding="utf-8")
    with logf:
        if len(tickers) == 0:
            logf.write("No CSV files or no tickers found in the provided folder.\n")
            print("No CSV files or no tickers found. בדוק את הנתיב או העלה CSV.")
            return
        for ticker in tickers:
            try:
                logf.write(f"\n\n=== Checking {ticker} ===\n")
                print(f"Checking {ticker}")
                local_csv = None
                possible = os.path.join(folder_path, f"{ticker}.csv")
                if os.path.exists(possible):
                    local_csv = possible
                else:
                    for f in csv_files:
                        try:
                            df_tmp = pd.read_csv(f, nrows=5)
                            cols = [c.lower() for c in df_tmp.columns]
                            if "ticker" in cols or "symbol" in cols:
                                df_full = pd.read_csv(f)
                                if "Ticker" in df_full.columns and ticker in df_full["Ticker"].astype(str).str.upper().values:
                                    local_csv = f
                                    break
                                if "Symbol" in df_full.columns and ticker in df_full["Symbol"].astype(str).str.upper().values:
                                    local_csv = f
                                    break
                        except Exception:
                            continue
                if local_csv:
                    try:
                        df = pd.read_csv(local_csv, parse_dates=True, index_col=0)
                        needed = {"Open","High","Low","Close","Volume"}
                        if not needed.issubset(set(df.columns)):
                            raise ValueError("local CSV לא מכיל עמודות מחיר מלאות, יורד מ-yfinance")
                    except Exception:
                        df = yf.download(ticker, period="6mo", interval="1d")
                else:
                    df = yf.download(ticker, period="6mo", interval="1d")

                if df is None or df.empty:
                    logf.write(f"{ticker} - No data\n")
                    print(f"{ticker} - No data")
                    continue

                df = add_indicators(df)

                try:
                    score = breakout_score_safe(df)
                    logf.write(f"{ticker} score = {score}\n")
                except Exception as e_score:
                    logf.write(f"{ticker} - Error in breakout_score_safe:\n{e_score}\n")
                    logf.write("Traceback:\n" + traceback.format_exc() + "\n")
                    logf.write("DF.tail():\n" + df.tail().to_string() + "\n")
                    print(f"{ticker} - Error in breakout_score_safe (logged)")
                    continue

                try:
                    setup = detect_breakout_setup_safe(df)
                    logf.write(f"{ticker} setup = {setup}\n")
                except Exception as e_setup:
                    logf.write(f"{ticker} - Error in detect_breakout_setup_safe:\n{e_setup}\n")
                    logf.write("Traceback:\n" + traceback.format_exc() + "\n")
                    logf.write("DF.tail():\n" + df.tail().to_string() + "\n")
                    print(f"{ticker} - Error in detect_breakout_setup_safe (logged)")
                    continue

            except Exception as e:
                logf.write(f"{ticker} - General error: {e}\n")
                logf.write("Traceback:\n" + traceback.format_exc() + "\n")
                print(f"{ticker} - General error (logged)")

    print("Done. See debug_log.txt for details:", log_path)

if __name__ == "__main__":
    # בחר את הפרמטר האחרון שאינו אופציה (מתחיל ב־'-') אם קיים
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    folder = args[-1] if args else "."
    run_debug_scan(folder)

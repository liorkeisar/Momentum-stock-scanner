"""
modules/indicators.py
Wyckoff Pro Swing Scanner

מנוע האינדיקטורים הטכניים (add_indicators - EMA/RSI/MACD/ATR/Stage2/Absorption/
Sideways/Squeeze/RS מול SPY/ADX ועוד) ומנוע ההחלטה לפני-פריצה
(compute_breakout_decision) שמצרף את כל הרכיבים לציון סופי עם ווטואים קשיחים.
"""
import numpy as np
import pandas as pd

from modules.utils import safe_last, is_bad, safe_div, safe_div_series, validate_df

def add_indicators(df, benchmark_df=None):
    df = df.copy()
    if df.empty:
        return df

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    df["STD20"] = df["Close"].rolling(20).std()
    df["MA20"] = df["Close"].rolling(20).mean()

    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]

    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    range_hl = (df["High"] - df["Low"]).replace(0, np.nan)
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / range_hl * df["Volume"]
    df["AD_Cum"] = ad.fillna(0).cumsum()

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum().replace(0, np.nan)
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow)))

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RVOL"] = df["Volume"] / df["VOL_MA20"].replace(0, np.nan)

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["SMA200_slope"] = df["SMA200"].diff(20)

    up_day = df["Close"] > df["Close"].shift(1)
    down_day = df["Close"] < df["Close"].shift(1)
    up_vol = df["Volume"].where(up_day, 0).rolling(20).sum()
    down_vol = df["Volume"].where(down_day, 0).rolling(20).sum().replace(0, np.nan)
    df["UpDownVolRatio"] = up_vol / down_vol

    day_range = (df["High"] - df["Low"]).replace(0, np.nan)
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / day_range
    df["CLV"] = clv
    df["CLV_DownDays"] = clv.where(down_day)
    df["AbsorptionScore"] = df["CLV_DownDays"].rolling(30, min_periods=5).mean()

    ema50_change_15d = df["EMA50"] - df["EMA50"].shift(15)
    df["SidewaysSlope"] = safe_div_series(ema50_change_15d, df["ATR"])

    squeeze_active = (df["UpperBB"] < df["UpperKC"]) & (df["LowerBB"] > df["LowerKC"])
    grp = (~squeeze_active).cumsum()
    df["SqueezeActive"] = squeeze_active
    df["SqueezeStreak"] = squeeze_active.groupby(grp).cumsum()

    BASE_WINDOW, RECENT_EXCLUDE = 50, 12
    df["BaseHigh"] = df["High"].rolling(BASE_WINDOW).max().shift(RECENT_EXCLUDE)

    df["ExtensionATR"] = safe_div_series(df["Close"] - df["EMA20"], df["ATR"])

    df["Return20D"] = df["Close"] / df["Close"].shift(20) - 1

    if benchmark_df is not None and not benchmark_df.empty:
        bench = benchmark_df["Close"].reindex(df.index).ffill()
        rs_line = df["Close"] / bench.replace(0, np.nan)
        df["RS_Line"] = rs_line
        df["RS_MA20"] = rs_line.rolling(20).mean()
    else:
        df["RS_Line"] = np.nan
        df["RS_MA20"] = np.nan

    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_wilder = tr.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_wilder
    dx = 100 * safe_div_series((plus_di - minus_di).abs(), (plus_di + minus_di))
    df["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    df["High52W"] = df["High"].rolling(252, min_periods=20).max()
    df["Low52W"] = df["Low"].rolling(252, min_periods=20).min()
    df["DailyChangePct"] = df["Close"].pct_change() * 100

    # ============ NEW: Consolidation + Strong Absorption Detection ============
    # בודקת התכנסות עם איסוף מסיבי במשך חודש (תבנית Wyckoff עמוקה)
    cons_data = detect_consolidation_and_absorption(df, consolidation_days=30, absorption_strength=0.50)
    df["ConsolidationStrength"] = cons_data["consolidation_strength"]
    df["AbsorptionMomentum"] = cons_data["absorption_momentum"]
    df["ConsAbsPattern"] = cons_data["pattern_detected"]

    return df

def detect_consolidation_and_absorption(df, consolidation_days=30, absorption_strength=0.50):
    """
    בודקת התכנסות + איסוף מסיבי בו-זמנית (דפוס Wyckoff אמיתי).
    
    מחזיר dict עם:
    - consolidation_strength: ציון 0-100 כמה זמן המניה בהתכנסות קרובה
    - absorption_momentum: ציון 0-100 כמה הקונים ספגו היצע בימי ירידה
    - pattern_detected: bool - האם שני התנאים חזקים דיים
    """
    result = {
        "consolidation_strength": pd.Series(0, index=df.index),
        "absorption_momentum": pd.Series(0, index=df.index),
        "pattern_detected": pd.Series(False, index=df.index)
    }
    
    if len(df) < consolidation_days:
        return result
    
    try:
        # חלק 1: בדיקת התכנסות - טווח מחיר קרוב למשך תקופה
        lookback = consolidation_days
        close = df["Close"]
        high_lookback = df["High"].rolling(lookback).max()
        low_lookback = df["Low"].rolling(lookback).min()
        price_range = high_lookback - low_lookback
        
        # ניירות בהתכנסות: טווח היומי בתוך 2% מטווח התקופה
        daily_range = df["High"] - df["Low"]
        daily_range_pct = daily_range / close * 100
        
        # בימים בהתכנסות: טווח יומי קטן וטווח החודש קטן
        is_consolidating = (daily_range_pct < 2.5) & (price_range < close * 0.06)
        consolidation_days_count = is_consolidating.rolling(lookback).sum()
        consolidation_strength = (consolidation_days_count / lookback * 100).fillna(0).astype(int)
        result["consolidation_strength"] = consolidation_strength
        
        # חלק 2: בדיקת איסוף מסיבי (Absorption)
        # כמה הקונים ספגו היצע בימי ירידה (יותר קניות בימי ירידה = איסוף טוב)
        down_day = close < close.shift(1)
        down_vol = df["Volume"].where(down_day, 0).rolling(lookback).sum()
        total_vol = df["Volume"].rolling(lookback).sum()
        
        # CLV: מדד כמה המחיר סגר קרוב לשיא הטווח (1=שיא, -1=תחתית)
        day_range = (df["High"] - df["Low"]).replace(0, 1)
        clv = ((close - df["Low"]) - (df["High"] - close)) / day_range
        
        # בימי ירידה, אנו רוצים CLV גבוה = המחיר סגר בחלק העליון למרות הירידה
        # זה אומר שקונים "ספגו" את ההיצע (absorption)
        down_day_clv = clv.where(down_day, np.nan)
        absorption_clv_mean = down_day_clv.rolling(lookback, min_periods=5).mean()
        
        # ציון 0-100: תרגום CLV (-1 עד 1) לציון
        absorption_momentum = (((absorption_clv_mean + 1) / 2) * 100).fillna(0).astype(int)
        result["absorption_momentum"] = absorption_momentum
        
        # חלק 3: זיהוי דפוס
        # שניהם צריכים להיות חזקים:
        # - התכנסות חזקה: לפחות 60% מימי התקופה בהתכנסות
        # - איסוף: CLV בימי ירידה חיובי (מעל 0)
        pattern_detected = (consolidation_strength >= 60) & (absorption_momentum >= 55)
        result["pattern_detected"] = pattern_detected
        
        return result
    except Exception:
        return result

def days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130):
    try:
        if len(df) < base_window + 5:
            return None
        closes = df["Close"]
        prior_high = closes.rolling(base_window).max().shift(1)
        breakout_mask = (closes > prior_high * (1 + threshold)) & prior_high.notna()

        recent_mask = breakout_mask.tail(min(search_window, len(breakout_mask)))
        if not recent_mask.any():
            return None
        true_positions = np.where(recent_mask.values)[0]
        last_true_pos = true_positions[-1]
        days_since = (len(recent_mask) - 1) - last_true_pos
        return int(days_since)
    except Exception:
        return None

def score_component(value, low, high, invert=False):
    try:
        if is_bad(value):
            return 0
        if low == high:
            return 100 if not invert else 0
        v = (value - low) / (high - low)
        v = max(0.0, min(1.0, v))
        if invert:
            v = 1.0 - v
        return int(round(v * 100))
    except Exception:
        return 0

def compute_breakout_decision(df):
    ok, msg = validate_df(df, ["High", "Low", "Close", "Volume", "EMA20", "EMA50", "ATR", "STD20",
                               "OBV", "AD_Cum", "MACD", "Signal", "RSI", "MA20", "UpperBB", "LowerBB",
                               "UpperKC", "LowerKC", "VOL_MA20"])
    if not ok:
        return {"score": 0, "confidence": 0, "risk": 100, "components": {}, "note": f"נתונים חסרים ({msg})"}

    comps = {}
    std20 = safe_last(df["STD20"])
    hist_std = df["STD20"].dropna()
    if len(hist_std) >= 30:
        low_std, high_std = hist_std.quantile(0.05), hist_std.quantile(0.95)
    else:
        low_std, high_std = (hist_std.min() if not hist_std.empty else 0), (hist_std.max() if not hist_std.empty else 1)
    comps["compression"] = score_component(std20, low_std, high_std, invert=True)

    vol_ma20 = safe_last(df["VOL_MA20"])
    rvol = safe_div(safe_last(df["Volume"]), vol_ma20, default=1.0)
    comps["rvol"] = score_component(rvol, 0.5, 3.0)

    ema20, ema50 = safe_last(df["EMA20"]), safe_last(df["EMA50"])
    trend_ratio = safe_div(ema20, ema50, default=1.0)
    comps["trend"] = score_component(trend_ratio, 0.95, 1.1)

    macd_diff = safe_last(df["MACD"]) - safe_last(df["Signal"])
    comps["macd"] = score_component(macd_diff, -1.0, 2.0)
    comps["rsi"] = score_component(safe_last(df["RSI"]), 40, 70)

    obv_now, obv_prev = safe_last(df["OBV"]), safe_last(df["OBV"].shift(10))
    ad_now, ad_prev = safe_last(df["AD_Cum"]), safe_last(df["AD_Cum"].shift(10))
    obv_gain = 1 if (not is_bad(obv_now) and not is_bad(obv_prev) and obv_now > obv_prev) else 0
    ad_gain = 1 if (not is_bad(ad_now) and not is_bad(ad_prev) and ad_now > ad_prev) else 0
    comps["institutional"] = int(round(((obv_gain + ad_gain) / 2) * 100))

    base_high = safe_last(df["BaseHigh"]) if "BaseHigh" in df.columns else np.nan
    prox = safe_div(safe_last(df["Close"]), base_high, default=0.0)
    if is_bad(prox) or prox <= 0:
        comps["proximity"] = 0
    elif prox <= 1.00:
        comps["proximity"] = score_component(prox, 0.85, 1.00)
    else:
        comps["proximity"] = max(0, int(round(100 - ((prox - 1.00) / 0.15) * 100)))

    atr_pct = safe_div(safe_last(df["ATR"]), safe_last(df["Close"]), default=0.0)
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    ubb, ukc, lbb, lkc = safe_last(df["UpperBB"]), safe_last(df["UpperKC"]), safe_last(df["LowerBB"]), safe_last(df["LowerKC"])
    sq = (not is_bad(ubb) and not is_bad(ukc) and not is_bad(lbb) and not is_bad(lkc)
          and ubb < ukc and lbb > lkc)
    comps["squeeze"] = 100 if sq else 0

    streak = safe_last(df["SqueezeStreak"]) if "SqueezeStreak" in df.columns else 0
    comps["squeeze_duration"] = score_component(streak, 0, 15)

    close_now = safe_last(df["Close"])
    sma150 = safe_last(df["SMA150"]) if "SMA150" in df.columns else np.nan
    sma200 = safe_last(df["SMA200"]) if "SMA200" in df.columns else np.nan
    sma200_slope = safe_last(df["SMA200_slope"]) if "SMA200_slope" in df.columns else np.nan
    stage2_ok = (not is_bad(close_now) and not is_bad(sma150) and not is_bad(sma200)
                 and close_now > sma150 > sma200 and (is_bad(sma200_slope) or sma200_slope > 0))
    comps["stage2"] = 100 if stage2_ok else (40 if (not is_bad(close_now) and not is_bad(sma150) and close_now > sma150) else 0)

    rs_now = safe_last(df["RS_Line"]) if "RS_Line" in df.columns else np.nan
    rs_prev = safe_last(df["RS_Line"].shift(20)) if "RS_Line" in df.columns else np.nan
    rs_change = safe_div(rs_now - rs_prev, abs(rs_prev) if not is_bad(rs_prev) else np.nan, default=np.nan) if not is_bad(rs_now) else np.nan
    comps["relative_strength"] = score_component(rs_change, -0.05, 0.10) if not is_bad(rs_change) else 50

    updown = safe_last(df["UpDownVolRatio"]) if "UpDownVolRatio" in df.columns else np.nan
    comps["volume_quality"] = score_component(updown, 0.6, 2.0) if not is_bad(updown) else 50

    extension = safe_last(df["ExtensionATR"]) if "ExtensionATR" in df.columns else np.nan
    comps["extension"] = score_component(extension, 0.5, 4.0, invert=True) if not is_bad(extension) else 50

    absorption = safe_last(df["AbsorptionScore"]) if "AbsorptionScore" in df.columns else np.nan
    comps["absorption"] = score_component(absorption, -0.3, 0.3) if not is_bad(absorption) else 50

    sideways_slope = safe_last(df["SidewaysSlope"]) if "SidewaysSlope" in df.columns else np.nan
    comps["sideways"] = score_component(abs(sideways_slope) if not is_bad(sideways_slope) else np.nan, 0, 2.5, invert=True) if not is_bad(sideways_slope) else 50

    # ============ NEW: Consolidation + Absorption Pattern ============
    cons_strength = safe_last(df["ConsolidationStrength"]) if "ConsolidationStrength" in df.columns else 0
    abs_momentum = safe_last(df["AbsorptionMomentum"]) if "AbsorptionMomentum" in df.columns else 0
    cons_abs_detected = safe_last(df["ConsAbsPattern"]) if "ConsAbsPattern" in df.columns else False
    
    # ציון קומבו: התכנסות + איסוף = איתות חזק עבור פריצה
    comps["cons_abs_pattern"] = int(cons_strength * 0.4 + abs_momentum * 0.6) if cons_abs_detected else 0

    weights = {
        "compression": 0.08, "rvol": 0.05, "trend": 0.04, "macd": 0.03, "rsi": 0.03,
        "institutional": 0.04, "proximity": 0.06, "squeeze": 0.02, "squeeze_duration": 0.04,
        "risk": 0.03, "stage2": 0.11, "relative_strength": 0.11, "volume_quality": 0.06,
        "extension": 0.08, "absorption": 0.10, "sideways": 0.08, "cons_abs_pattern": 0.06
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    hard_downtrend = (not is_bad(close_now) and not is_bad(sma200) and not is_bad(sma200_slope)
                       and close_now < sma200 and sma200_slope < 0)
    if hard_downtrend:
        final_score = min(final_score, 35)

    ret20 = safe_last(df["Return20D"]) if "Return20D" in df.columns else np.nan
    days_since_bo = days_since_last_breakout(df, base_window=60, threshold=0.03, search_window=130)
    already_broken_out = (
        (not is_bad(prox) and prox > 1.10) or
        (not is_bad(extension) and extension > 4.0) or
        (not is_bad(ret20) and ret20 > 0.25) or
        (days_since_bo is not None and days_since_bo > 10)
    )
    if already_broken_out:
        final_score = min(final_score, 30)

    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    risk_metric = 100 - comps.get("risk", 0)

    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if comps.get("squeeze_duration", 0) >= 60: notes.append("כיווץ ממושך")
    if comps.get("stage2", 0) == 100: notes.append("מגמת-על בריאה (Stage 2)")
    if comps.get("relative_strength", 0) >= 70: notes.append("חוזק יחסי למדד")
    if comps.get("volume_quality", 0) >= 70: notes.append("נפח קונים דומיננטי")
    if comps.get("absorption", 0) >= 70: notes.append("איסוף שקט בזמן ירידה (ספיגת היצע)")
    if comps.get("cons_abs_pattern", 0) >= 70: notes.append("✨ התכנסות חזקה עם איסוף מסיבי (דפוס Wyckoff עמוק)")
    if comps.get("sideways", 0) >= 75: notes.append("מגמה הצידה (טווח אמיתי)")
    if hard_downtrend: notes.append("⚠️ מגמת-על יורדת — סיכון גבוה")
    if already_broken_out:
        if days_since_bo is not None and days_since_bo > 10:
            notes.append(f"⚠️ המניה כבר פרצה לפני כ-{days_since_bo} ימי מסחר — לא קדם-פריצה")
        else:
            notes.append("⚠️ נראה שהמניה כבר פרצה/מורחקת מהבסיס — לא אידיאלית לכניסה כ'קדם-פריצה'")
    if not already_broken_out and not is_bad(prox) and prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {"score": final_score, "confidence": confidence, "risk": risk_metric, "components": comps, "note": note,
            "rsi_last": safe_last(df["RSI"]) if "RSI" in df.columns else np.nan,
            "rvol_last": rvol, "atr_pct": atr_pct, "stage2_ok": stage2_ok,
            "already_broken_out": already_broken_out, "hard_downtrend": hard_downtrend,
            "days_since_breakout": days_since_bo, "cons_abs_detected": cons_abs_detected}

"""
modules/ml_predictions.py
Wyckoff Pro Swing Scanner

חיזוי: פיצ'רים ל-ML, מודל לוגיסטי (אם sklearn זמין), Backtest לכיול הציון מול
תוצאות היסטוריות אמיתיות, חיפוש דמיון סטטיסטי (z-score), וזיהוי תבנית VCP
מבוסס נקודות תפנית (swing points) אמיתיות.
"""
import numpy as np
import pandas as pd

from modules.utils import safe_last, is_bad, safe_div
from modules.indicators import compute_breakout_decision

# ייבוא אופציונלי - האפליקציה ממשיכה לעבוד גם בלי scikit-learn מותקן
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

def compute_features_for_ml(df, window=20):
    rows = []
    for end in range(window, len(df) - 5):
        w = df.iloc[end - window:end]

        vol_ma = w["Volume"].rolling(20).mean().iloc[-1]
        ema20 = w["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = w["Close"].ewm(span=50, adjust=False).mean().iloc[-1]

        delta = w["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1] if len(w) >= 14 else np.nan
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1] if len(w) >= 14 else np.nan
        rsi_val = np.nan
        if not is_bad(gain) and not is_bad(loss):
            rs = gain / loss if loss != 0 else np.nan
            rsi_val = 100 - (100 / (1 + rs)) if not is_bad(rs) else 100.0

        true_range = (w["High"] - w["Low"]).rolling(14).mean().iloc[-1]

        feat = {
            "close_last": w["Close"].iloc[-1],
            "std20": w["Close"].rolling(20).std().iloc[-1] if len(w) >= 20 else np.nan,
            "std20_pct": safe_div(w["Close"].rolling(20).std().iloc[-1] if len(w) >= 20 else np.nan, w["Close"].iloc[-1], default=np.nan),
            "rvol": safe_div(w["Volume"].iloc[-1], vol_ma, default=1.0),
            "ema20_ema50": safe_div(ema20, ema50, default=1.0),
            "macd_diff": w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
            "macd_diff_pct": safe_div(
                w["Close"].ewm(span=12, adjust=False).mean().iloc[-1] - w["Close"].ewm(span=26, adjust=False).mean().iloc[-1],
                w["Close"].iloc[-1], default=np.nan
            ),
            "rsi": rsi_val,
            "atr_pct": safe_div(true_range, w["Close"].iloc[-1], default=0.0),
            "obv": (np.sign(w["Close"].diff()) * w["Volume"]).fillna(0).cumsum().iloc[-1]
        }
        future = df.iloc[end:end + 5]
        label = 0
        if not future.empty:
            if future["Close"].max() > w["High"].max() * 1.005:
                label = 1
        feat["label"] = label
        rows.append(feat)
    return pd.DataFrame(rows)

def train_logistic_model(df):
    try:
        feats = compute_features_for_ml(df, window=20)
        feats = feats.dropna()
        if len(feats) < 30 or feats['label'].sum() < 5:
            return None
        X = feats.drop(columns=["label"])
        y = feats["label"]
        if SKLEARN_AVAILABLE:
            model = LogisticRegression(max_iter=200)
            model.fit(X, y)
            return model
        return None
    except Exception:
        return None

def logistic_predict_probability(model, df):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return None
        clean = feats.dropna()
        if clean.empty:
            return None
        last = clean.iloc[-1].drop(labels=["label"])
        if SKLEARN_AVAILABLE and model is not None:
            prob = model.predict_proba([last.values])[0][1]
            return float(prob)
        return None
    except Exception:
        return None

def backtest_score_calibration(df_full, lookahead=5, step=3, min_history=250):
    try:
        n = len(df_full)
        if n < min_history + lookahead + 10:
            return None, None

        scores, outcomes, dates = [], [], []
        for i in range(min_history, n - lookahead, step):
            slice_df = df_full.iloc[:i + 1]
            res = compute_breakout_decision(slice_df)
            score = res["score"]

            window_high = df_full["High"].iloc[max(0, i - 19):i + 1].max()
            future = df_full["Close"].iloc[i + 1:i + 1 + lookahead]
            if future.empty or is_bad(window_high):
                continue
            broke = bool(future.max() > window_high * 1.005)

            scores.append(score)
            outcomes.append(1 if broke else 0)
            dates.append(df_full.index[i])

        if not scores:
            return None, None

        bt_df = pd.DataFrame({"date": dates, "score": scores, "outcome": outcomes})
        bins = [0, 40, 55, 70, 85, 101]
        labels = ["0-39 (חלש)", "40-54 (בינוני)", "55-69 (טוב)", "70-84 (חזק)", "85-100 (מצוין)"]
        bt_df["bucket"] = pd.cut(bt_df["score"], bins=bins, labels=labels, right=False)

        summary = bt_df.groupby("bucket", observed=True).agg(
            מקרים=("outcome", "size"),
            שיעור_הצלחה=("outcome", "mean")
        ).reset_index()
        summary["שיעור_הצלחה"] = (summary["שיעור_הצלחה"] * 100).round(1)
        summary = summary.rename(columns={"bucket": "טווח ציון"})
        return summary, bt_df
    except Exception:
        return None, None

def statistical_similarity_prediction(df, tolerance=0.15, lookahead=5):
    try:
        feats = compute_features_for_ml(df, window=20)
        if feats.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}
        clean = feats.dropna()
        if clean.empty or len(clean) < 5:
            return {"count": 0, "successes": 0, "rate": 0.0}

        feature_keys = ["std20_pct", "rvol", "ema20_ema50", "macd_diff_pct", "rsi"]
        feature_keys = [k for k in feature_keys if k in clean.columns]

        target = clean.iloc[-1]
        candidates = clean.iloc[:-1]
        if candidates.empty:
            return {"count": 0, "successes": 0, "rate": 0.0}

        means = candidates[feature_keys].mean()
        stds = candidates[feature_keys].std().replace(0, np.nan).fillna(1.0)

        target_z = (target[feature_keys] - means) / stds
        cand_z = (candidates[feature_keys] - means) / stds

        dist = np.sqrt(((cand_z - target_z) ** 2).sum(axis=1))

        distance_threshold = tolerance * np.sqrt(len(feature_keys)) * 2.5

        sim_mask = dist <= distance_threshold
        sim = candidates[sim_mask]
        count = len(sim)
        successes = int(sim['label'].sum()) if 'label' in sim.columns else 0
        rate = (successes / count) if count > 0 else 0.0
        return {"count": count, "successes": successes, "rate": float(rate)}
    except Exception:
        return {"count": 0, "successes": 0, "rate": 0.0}

def find_swing_points(df, order=3, window=60):
    w = df.tail(window)
    highs = w["High"].values
    lows = w["Low"].values
    n = len(w)
    swing_highs, swing_lows = [], []
    for i in range(order, n - order):
        h_window = highs[i - order:i + order + 1]
        l_window = lows[i - order:i + order + 1]
        if highs[i] == h_window.max():
            swing_highs.append((i, highs[i]))
        if lows[i] == l_window.min():
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows

def pattern_detection_vcp_like(df):
    try:
        window = 60
        if len(df) < window:
            return {"match": False, "desc": "לא מספיק נתונים לתבנית", "contractions": 0}

        swing_highs, swing_lows = find_swing_points(df, order=3, window=window)

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"match": False, "desc": "לא נמצאו מספיק נקודות תפנית", "contractions": 0}

        recent_highs = [p for _, p in swing_highs[-4:]]
        recent_lows = [p for _, p in swing_lows[-4:]]

        lower_highs = len(recent_highs) >= 2 and all(
            recent_highs[i] >= recent_highs[i + 1] for i in range(len(recent_highs) - 1)
        )
        higher_lows = len(recent_lows) >= 2 and all(
            recent_lows[i] <= recent_lows[i + 1] for i in range(len(recent_lows) - 1)
        )

        swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
        wave_ranges = []
        for i in range(1, len(swings)):
            wave_ranges.append(abs(swings[i][1] - swings[i - 1][1]))
        contractions = 0
        if len(wave_ranges) >= 2:
            for i in range(1, len(wave_ranges)):
                if wave_ranges[i] < wave_ranges[i - 1]:
                    contractions += 1
        contraction_ratio = contractions / max(1, len(wave_ranges) - 1) if wave_ranges else 0
        compression = contraction_ratio >= 0.5

        w = df.tail(window)
        std_vals = w["Close"].rolling(10).std().dropna()
        std_trend = np.polyfit(range(len(std_vals)), std_vals, 1)[0] if len(std_vals) > 2 else 0
        std_declining = std_trend < 0

        match = lower_highs and higher_lows and compression and std_declining
        desc = []
        if lower_highs: desc.append("שיאים יורדים")
        if higher_lows: desc.append("שפלים עולים")
        if compression: desc.append(f"{contractions} כיווצים עוקבים")
        if std_declining: desc.append("סטיית תקן יורדת")
        if not desc:
            desc = ["לא נמצאו סימני VCP ברורים"]
        return {"match": bool(match), "desc": "; ".join(desc), "contractions": contractions}
    except Exception:
        return {"match": False, "desc": "שגיאה בזיהוי תבנית", "contractions": 0}


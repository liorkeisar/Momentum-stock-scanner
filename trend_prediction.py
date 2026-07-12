# -*- coding: utf-8 -*-
"""
trend_prediction.py
--------------------
רכיב "חיזוי מגמה" ל-Wyckoff Pro Swing Scanner (app.py).

מותאם ישירות למבנה הנתונים הקיים אצלך:
    res  = details[ticker]["res"]      # הפלט של compute_breakout_decision()
    df   = details[ticker]["df_tail"]  # df.tail(120) עם DatetimeIndex בשם 'Date'

שילוב ב-app.py:
    1) בראש הקובץ, ליד שאר ה-imports:
         from trend_prediction import render_trend_prediction

    2) בלולאה שמציגה כל מניה (איפה שקוראים ל-render_stock_card(ticker, res, df_tail)),
       מיד אחרי הקריאה הזו:
         render_trend_prediction(df_tail, res, ticker)

הערה: קו התחזית בגרף הוא המחשה חזותית של כיוון/עוצמת ה-Composite Score
הקיים אצלך - הוא אינו מודל שמנבא מחיר עתידי, ואין להציג אותו ככזה.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# פלטת הצבעים — זהה לזו שב-app.py, כך שהרכיב נראה מאוחד עם שאר האפליקציה
# ---------------------------------------------------------------------------
BG = "#0b0f17"
PANEL = "#12161f"
PANEL_ALT = "#171c28"
BORDER = "#242a38"
TEXT_MUTED = "#8891a5"
TEXT_MAIN = "#f2f4f8"

# ירוק/אדום בלבד לחיזוי, בדיוק כמו הנרות ב-plot_advanced()
COLOR_BULL = "#1fc46a"
COLOR_BEAR = "#e2543b"
COLOR_NEUTRAL = "#8891a5"   # לדשדוש בלבד - לא נכלל ב"ירוק/אדום" כי זה לא כיוון


def _is_bad(v):
    try:
        return v is None or bool(pd.isna(v))
    except Exception:
        return v is None


# ---------------------------------------------------------------------------
# 1) לוגיקת סיווג הכיוון — מבוסס ישירות על res מ-compute_breakout_decision
# ---------------------------------------------------------------------------
COMPONENT_LABELS_HE = {
    "compression": "דחיסת מחיר (Squeeze)",
    "rvol": "נפח יחסי (RVOL)",
    "trend": "טרנד קצר טווח (EMA20/50)",
    "macd": "MACD",
    "rsi": "RSI",
    "institutional": "כסף מוסדי (OBV/AD)",
    "proximity": "קרבה להתנגדות ישנה",
    "squeeze": "Squeeze פעיל",
    "squeeze_duration": "משך ה-Squeeze",
    "risk": "ניקוד סיכון (ATR)",
    "stage2": "מגמת-על (Stage 2)",
    "relative_strength": "חוזק יחסי מול SPY",
    "volume_quality": "איכות נפח (עולה/יורד)",
    "extension": "קרבה לממוצע (Extension)",
    "absorption": "איסוף שקט (Wyckoff Absorption)",
    "sideways": "תנועה הצידה (טווח אמיתי)",
}


def predict_trend(res: dict) -> dict:
    score = float(res.get("score", 0))
    confidence = float(res.get("confidence", 0))
    comps = res.get("components", {}) or {}
    hard_downtrend = bool(res.get("hard_downtrend", False))
    already_broken_out = bool(res.get("already_broken_out", False))

    rs = float(comps.get("relative_strength", 50))
    absorption = float(comps.get("absorption", 50))

    if hard_downtrend or already_broken_out:
        direction = "ירידה סבירה" if hard_downtrend else "דשדוש / לא ברור"
        icon = "⬇️" if hard_downtrend else "➡️"
        color = COLOR_BEAR if hard_downtrend else COLOR_NEUTRAL
        conf = max(15.0, min(90.0, 100 - score)) if hard_downtrend else 40.0
    elif score >= 70 and rs >= 55 and absorption >= 55:
        direction = "עלייה סבירה"
        icon = "⬆️"
        color = COLOR_BULL
        conf = min(97.0, max(score, confidence))
    elif score <= 35:
        direction = "ירידה סבירה"
        icon = "⬇️"
        color = COLOR_BEAR
        conf = min(95.0, max(100 - score, 100 - confidence))
    else:
        direction = "דשדוש / לא ברור"
        icon = "➡️"
        color = COLOR_NEUTRAL
        conf = max(20.0, 50.0 - abs(score - 50) * 0.4)

    conf = max(5.0, min(99.0, conf))

    strong = sorted(
        [(k, v) for k, v in comps.items() if k in COMPONENT_LABELS_HE],
        key=lambda x: -x[1]
    )[:5]
    reasons = [{"label": COMPONENT_LABELS_HE[k], "value": f"{v:.0f}/100"} for k, v in strong]
    reasons.append({"label": "ציון מורכב (Composite Score)", "value": f"{score:.0f}/100"})

    return {
        "direction": direction, "icon": icon, "color": color,
        "confidence": conf, "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# 2) קו התחזית המקווקו — ויזואלי בלבד, נגזר מהביטחון ומה-ATR האמיתי של המניה
# ---------------------------------------------------------------------------
def _generate_forecast_curve(last_close: float, direction: str, confidence: float,
                              atr: float, periods: int = 12, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    strength = (confidence - 50) / 50.0

    if direction.startswith("עלייה"):
        drift = abs(strength) * atr * 0.35
    elif direction.startswith("ירידה"):
        drift = -abs(strength) * atr * 0.35
    else:
        drift = 0.0

    steps = np.linspace(0, 1, periods)
    trend_component = drift * steps
    noise = rng.normal(0, atr * 0.07, size=periods)
    noise = np.cumsum(noise) / np.sqrt(np.arange(1, periods + 1))
    curve = last_close + trend_component + noise
    curve[0] = last_close
    return curve


# ---------------------------------------------------------------------------
# 3) בניית הגרף — נרות (באותם צבעים כמו plot_advanced) + קו מקווקו
# ---------------------------------------------------------------------------
def _build_chart(price_df: pd.DataFrame, prediction: dict, symbol: str,
                  lookback: int = 60) -> go.Figure:
    plot_df = price_df.tail(lookback).copy()
    plot_df["Date"] = pd.to_datetime(plot_df["Date"])

    last_close = float(plot_df["Close"].iloc[-1])
    if "ATR" in plot_df.columns and not _is_bad(plot_df["ATR"].iloc[-1]):
        atr = float(plot_df["ATR"].iloc[-1])
    else:
        atr = float((plot_df["High"] - plot_df["Low"]).rolling(14).mean().iloc[-1])
    if not np.isfinite(atr) or atr <= 0:
        atr = last_close * 0.01

    diffs = plot_df["Date"].diff().dropna()
    step = diffs.median() if len(diffs) else pd.Timedelta(days=1)

    forecast_periods = 12
    forecast_prices = _generate_forecast_curve(
        last_close, prediction["direction"], prediction["confidence"], atr, periods=forecast_periods,
    )
    forecast_dates = [plot_df["Date"].iloc[-1] + step * i for i in range(forecast_periods)]

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=plot_df["Date"], open=plot_df["Open"], high=plot_df["High"],
        low=plot_df["Low"], close=plot_df["Close"],
        increasing_line_color=COLOR_BULL, increasing_fillcolor=COLOR_BULL,
        decreasing_line_color=COLOR_BEAR, decreasing_fillcolor=COLOR_BEAR,
        line_width=1, name=symbol, showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=forecast_dates, y=forecast_prices,
        mode="lines",
        line=dict(color=prediction["color"], width=3, dash="dot"),
        name="חיזוי מגמה (להמחשה)",
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=[plot_df["Date"].iloc[-1]], y=[last_close],
        mode="markers",
        marker=dict(color=prediction["color"], size=9, line=dict(color=TEXT_MAIN, width=1)),
        showlegend=False,
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(color=TEXT_MAIN, size=12),
        xaxis=dict(showgrid=False, rangeslider_visible=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", side="right"),
        title=dict(text=f"{symbol} — חיזוי מגמה", x=0.02, font=dict(size=15)),
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# 4) כרטיס ביטחון + נימוקים (CSS ירוק/אדום, תואם לעיצוב app.py)
# ---------------------------------------------------------------------------
def _inject_css():
    st.markdown(f"""
    <style>
    .tp-card {{
        border-radius: 16px;
        padding: 18px 20px;
        margin-top: 8px;
        margin-bottom: 16px;
        background: {PANEL};
        border: 1px solid {BORDER};
        direction: rtl;
        text-align: right;
    }}
    .tp-direction {{ font-size: 26px; font-weight: 800; margin-bottom: 4px; }}
    .tp-conf-label {{ font-size: 13px; color: {TEXT_MUTED}; margin-bottom: 6px; }}
    .tp-bar-bg {{
        width: 100%; height: 10px; border-radius: 6px;
        background: {PANEL_ALT}; overflow: hidden; margin-bottom: 4px;
    }}
    .tp-bar-fill {{ height: 100%; border-radius: 6px; }}
    .tp-reason-row {{
        display: flex; justify-content: space-between; padding: 7px 0;
        border-bottom: 1px solid {BORDER}; font-size: 14px;
    }}
    .tp-reason-row:last-child {{ border-bottom: none; }}
    .tp-reason-label {{ color: {TEXT_MUTED}; }}
    .tp-reason-value {{ font-weight: 700; color: {TEXT_MAIN}; }}
    .tp-disclaimer {{
        margin-top: 14px; padding: 10px 12px; border-radius: 10px;
        background: rgba(226,84,59,0.08); border: 1px solid rgba(226,84,59,0.35);
        color: #ffb4a8; font-size: 12.5px; line-height: 1.5;
    }}
    </style>
    """, unsafe_allow_html=True)


def _render_prediction_card(prediction: dict):
    color = prediction["color"]
    conf = prediction["confidence"]

    reasons_html = "".join(
        f"""<div class="tp-reason-row">
                <span class="tp-reason-label">{r['label']}</span>
                <span class="tp-reason-value">{r['value']}</span>
            </div>"""
        for r in prediction["reasons"]
    )

    st.markdown(f"""
    <div class="tp-card">
        <div class="tp-direction" style="color:{color};">
            {prediction['icon']} {prediction['direction']}
        </div>
        <div class="tp-conf-label">רמת ביטחון של המודל</div>
        <div class="tp-bar-bg">
            <div class="tp-bar-fill" style="width:{conf:.0f}%; background:{color};"></div>
        </div>
        <div style="text-align:left; font-size:13px; color:{color}; font-weight:700; margin-bottom:10px;">
            {conf:.0f}%
        </div>
        <div style="font-size:14px; font-weight:700; margin-bottom:4px; color:{TEXT_MAIN};">מבוסס על:</div>
        {reasons_html}
        <div class="tp-disclaimer">
            ⚠️ החיזוי מבוסס על ניתוח סטטיסטי והיסטורי של האינדיקטורים בלבד,
            אינו מהווה ייעוץ או המלצת השקעה, ואינו מבטיח תוצאה עתידית כלשהי.
            כל החלטת מסחר היא באחריות המשתמש בלבד.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 5) פונקציית הכניסה הראשית
# ---------------------------------------------------------------------------
def render_trend_prediction(df_tail: pd.DataFrame, res: dict, symbol: str,
                             key_prefix: str = "tp"):
    """
    כפתור "חיזוי מגמה" לכרטיס מניה. קרא לזה מיד אחרי render_stock_card().
    """
    btn_key = f"{key_prefix}_predict_btn_{symbol}"
    show_key = f"{key_prefix}_predict_show_{symbol}"

    if show_key not in st.session_state:
        st.session_state[show_key] = False

    if st.button(f"🔮 חיזוי מגמה — {symbol}", key=btn_key, use_container_width=True):
        st.session_state[show_key] = not st.session_state[show_key]

    if not st.session_state[show_key]:
        return

    if df_tail is None or df_tail.empty or len(df_tail) < 15:
        st.warning("אין מספיק נתוני מחיר להצגת חיזוי מגמה.")
        return

    price_df = df_tail.reset_index()
    if "Date" not in price_df.columns:
        price_df = price_df.rename(columns={price_df.columns[0]: "Date"})

    required = {"Date", "Open", "High", "Low", "Close"}
    if not required.issubset(set(price_df.columns)):
        st.warning("חסרות עמודות מחיר (Open/High/Low/Close) בהצגת חיזוי מגמה.")
        return

    _inject_css()
    prediction = predict_trend(res)

    fig = _build_chart(price_df, prediction, symbol)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    _render_prediction_card(prediction)

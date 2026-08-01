"""
modules/ui_components.py
Wyckoff Pro Swing Scanner - updated to match SwingAI-inspired UI
"""
import streamlit as st
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from modules.utils import is_bad, safe_last, fmt_compact_number
from modules.styles import ACCENT, BUY_COLOR, SELL_COLOR, PANEL, PANEL_ALT, BORDER, TEXT_MUTED, get_theme

# (functions unchanged omitted for brevity in commit) - we'll keep existing helpers

def render_stock_card(ticker, res, df_tail, phase=None):
    """
    Updated card layout to match SwingAI reference: larger score ring on right,
    pill tags, compact sparkline bars, bold price in orange when active, and
    responsive spacings for mobile.
    """
    score = res.get("score", 0)
    sig_class, sig_label, strength_label = classify_signal(score)

    notes_list = [n.strip() for n in res.get("note", "").split(",") if n.strip()]

    if df_tail is None or df_tail.empty:
        notes_html = "".join(f"<div>• {n}</div>" for n in notes_list[:4])
        nodata_html = f"""
        <div class="stock-card-v3">
            <div class="v3-ticker-row">
                <div style="display:flex;gap:8px;align-items:center;">
                    <span class="v3-ticker">{ticker}</span>
                    <span class="pill pill-neutral">אין נתונים</span>
                </div>
            </div>
            <div class="stock-note" style="margin-top:6px;">{notes_html if notes_html else "לא ניתן היה לטעון נתונים לטיקר זה"}</div>
        </div>"""
        st.markdown("".join(line.strip() for line in nodata_html.split("\n")), unsafe_allow_html=True)
        return

    last_price = safe_last(df_tail["Close"])
    chg_pct = safe_last(df_tail["DailyChangePct"]) if "DailyChangePct" in df_tail.columns else np.nan
    price_html = f'<span class="v3-price" style="color:{ACCENT};">${last_price:,.2f}</span>' if not is_bad(last_price) else ""
    chg_html = ""
    if not is_bad(chg_pct):
        c_color = BUY_COLOR if chg_pct >= 0 else SELL_COLOR
        arrow = "▲" if chg_pct >= 0 else "▼"
        chg_html = f'<span class="v3-chg" style="color:{c_color};">{arrow} {abs(chg_pct):.2f}%</span>'

    bars_vals = df_tail["Close"].tail(20).tolist()
    bars_html = f'<div class="v3-bars">{sparkline_bars_svg(bars_vals, width=220, height=44)}</div>'

    proximity_score = res.get("components", {}).get("proximity", 0)
    near_breakout_html = ""
    if proximity_score >= 70:
        near_breakout_html = '<span class="pill pill-green">🔥 קרוב לפריצה</span>'

    pattern_label = None
    if phase and phase.get("phase") != "unknown":
        pattern_label = f'{phase["icon"]} {phase["label"]}'
    elif notes_list:
        pattern_label = notes_list[0]
    pattern_pill_html = f'<span class="pill pill-navy">{pattern_label}</span>' if pattern_label else ""

    score_color_val = score_color(score)

    # new layout: left content + right score ring
    card_html = f"""
    <div class="stock-card-v3" style="display:flex;gap:12px;align-items:center;">
        <div style="flex:1;min-width:0;">
            <div class="v3-ticker-row" style="justify-content:space-between;">
                <div style="display:flex;flex-direction:column;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span class="v3-ticker">{ticker}</span>
                        {pattern_pill_html}
                    </div>
                    <div class="stock-sub">{res.get('note','')}</div>
                </div>
                <div style="text-align:right;">
                    {price_html}
                    {chg_html}
                </div>
            </div>
            {bars_html}
            <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;gap:8px;align-items:center;">{near_breakout_html}</div>
                <div class="v3-score">ציון: <b style="color:{score_color_val};">{score}</b></div>
            </div>
        </div>
        <div style="width:78px;display:flex;align-items:center;justify-content:center;">
            {score_ring_big_html(score)}
        </div>
    </div>"""

    st.markdown("".join(line.strip() for line in card_html.split("\n")), unsafe_allow_html=True)

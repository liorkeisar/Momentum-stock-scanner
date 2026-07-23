"""
modules/charting.py
Professional charting using lightweight-charts (TradingView library)

Provides:
- Professional candlestick charts with smooth rendering
- Drawing tools (lines, channels, levels)
- Advanced indicators (Volume Profile, VWAP, etc.)
- Interactive zoom & pan
- Export capabilities
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from modules.utils import is_bad, safe_last
from modules.styles import get_theme, BUY_COLOR, SELL_COLOR, ACCENT, PANEL, BORDER, TEXT_MUTED

def prepare_candlestick_data(df: pd.DataFrame) -> List[Dict]:
    """
    Convert DataFrame to Lightweight Charts candlestick format
    Expected columns: Open, High, Low, Close, and optionally Volume
    """
    data = []
    for idx, row in df.iterrows():
        # Convert index (datetime) to Unix timestamp
        if hasattr(idx, 'timestamp'):
            time = int(idx.timestamp())
        else:
            time = int(pd.Timestamp(idx).timestamp())
        
        candle = {
            "time": time,
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        }
        data.append(candle)
    
    return data

def prepare_volume_data(df: pd.DataFrame) -> List[Dict]:
    """Convert volume to Lightweight Charts format"""
    data = []
    for idx, row in df.iterrows():
        if hasattr(idx, 'timestamp'):
            time = int(idx.timestamp())
        else:
            time = int(pd.Timestamp(idx).timestamp())
        
        # Color based on candle direction
        color = "#1fc46a66" if row["Close"] >= row["Open"] else "#e2543b66"
        
        data.append({
            "time": time,
            "value": float(row["Volume"]),
            "color": color
        })
    
    return data

def prepare_line_data(df: pd.DataFrame, column: str) -> List[Dict]:
    """Convert a line series (MA, EMA, etc.) to Lightweight Charts format"""
    if column not in df.columns:
        return []
    
    data = []
    for idx, row in df.iterrows():
        if is_bad(row[column]):
            continue
        
        if hasattr(idx, 'timestamp'):
            time = int(idx.timestamp())
        else:
            time = int(pd.Timestamp(idx).timestamp())
        
        data.append({
            "time": time,
            "value": float(row[column])
        })
    
    return data

def create_professional_chart(
    df: pd.DataFrame,
    ticker: str,
    height: int = 600,
    show_volume: bool = True,
    show_ma20: bool = True,
    show_ma50: bool = True,
    show_sma200: bool = True,
    show_bb: bool = False,
    days: int = 90
) -> None:
    """
    Create a professional Lightweight Charts candlestick chart
    with multiple indicators and interactive features
    """
    
    df_plot = df.tail(days).copy().reset_index(drop=True)
    
    # Prepare data
    candles = prepare_candlestick_data(df_plot)
    volume = prepare_volume_data(df_plot) if show_volume else []
    ma20 = prepare_line_data(df_plot, "MA20") if show_ma20 else []
    ma50 = prepare_line_data(df_plot, "MA50") if show_ma50 else []
    sma200 = prepare_line_data(df_plot, "SMA200") if show_sma200 else []
    
    # Theme colors
    theme = get_theme()
    is_dark = theme["bg"].lower() == "#0b0f17"
    
    # Lightweight Charts HTML/JS
    chart_html = f"""
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
                background: {theme['bg']};
                color: {theme['text_main']};
            }}
            #chart {{
                width: 100%;
                height: {height}px;
                background: {theme['panel']};
            }}
            .controls {{
                padding: 10px;
                background: {theme['panel_alt']};
                border-bottom: 1px solid {theme['border']};
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}
            button {{
                padding: 6px 12px;
                background: {ACCENT}22;
                border: 1px solid {ACCENT}55;
                color: {ACCENT};
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }}
            button:hover {{
                background: {ACCENT}44;
            }}
            button.active {{
                background: {ACCENT};
                color: {theme['bg']};
            }}
        </style>
    </head>
    <body>
        <div class="controls">
            <button onclick="toggleMA20()" class="active" id="btn-ma20">MA20</button>
            <button onclick="toggleMA50()" class="active" id="btn-ma50">MA50</button>
            <button onclick="toggleSMA200()" class="active" id="btn-sma200">SMA200</button>
            <button onclick="resetChart()">🔄 Reset</button>
            <button onclick="downloadChart()">📥 Save PNG</button>
        </div>
        <div id="chart"></div>
        
        <script>
            const chartContainer = document.getElementById('chart');
            const chart = LightweightCharts.createChart(chartContainer, {{
                layout: {{
                    background: {{ color: '{theme['panel']}' }},
                    textColor: '{theme['text_secondary']}',
                }},
                width: window.innerWidth,
                height: {height},
                timeScale: {{
                    timeVisible: true,
                    secondsVisible: false,
                }},
                rightPriceScale: {{
                    borderColor: '{theme['border']}',
                }},
            }});
            
            // Candlestick series
            const candlestickSeries = chart.addCandlestickSeries({{
                upColor: '#1fc46a',
                downColor: '#e2543b',
                borderUpColor: '#1fc46a',
                borderDownColor: '#e2543b',
                wickUpColor: '#1fc46a',
                wickDownColor: '#e2543b',
            }});
            candlestickSeries.setData({json.dumps(candles)});
            
            // Volume series
            {f'''
            const volumeSeries = chart.addHistogramSeries({{
                color: '#26a69a',
                priceFormat: {{ type: 'volume' }},
            }});
            volumeSeries.setData({json.dumps(volume)});
            chart.priceScale('right').attachSeries(volumeSeries);
            ''' if show_volume else ''}
            
            // Moving averages
            {f'''
            const ma20Series = chart.addLineSeries({{
                color: '#f2c94c',
                lineWidth: 2,
                title: 'MA20',
            }});
            ma20Series.setData({json.dumps(ma20)});
            ''' if show_ma20 else ''}
            
            {f'''
            const ma50Series = chart.addLineSeries({{
                color: '#ff9800',
                lineWidth: 2,
                title: 'MA50',
            }});
            ma50Series.setData({json.dumps(ma50)});
            ''' if show_ma50 else ''}
            
            {f'''
            const sma200Series = chart.addLineSeries({{
                color: '#9c27b0',
                lineWidth: 2,
                title: 'SMA200',
                lineStyle: 1,
            }});
            sma200Series.setData({json.dumps(sma200)});
            ''' if show_sma200 else ''}
            
            // Auto-fit price scale
            chart.timeScale().fitContent();
            
            // Toggle functions
            function toggleMA20() {{
                const btn = document.getElementById('btn-ma20');
                if (ma20Series.isVisible()) {{
                    ma20Series.applyOptions({{ visible: false }});
                    btn.classList.remove('active');
                }} else {{
                    ma20Series.applyOptions({{ visible: true }});
                    btn.classList.add('active');
                }}
            }}
            
            function toggleMA50() {{
                const btn = document.getElementById('btn-ma50');
                if (ma50Series.isVisible()) {{
                    ma50Series.applyOptions({{ visible: false }});
                    btn.classList.remove('active');
                }} else {{
                    ma50Series.applyOptions({{ visible: true }});
                    btn.classList.add('active');
                }}
            }}
            
            function toggleSMA200() {{
                const btn = document.getElementById('btn-sma200');
                if (sma200Series.isVisible()) {{
                    sma200Series.applyOptions({{ visible: false }});
                    btn.classList.remove('active');
                }} else {{
                    sma200Series.applyOptions({{ visible: true }});
                    btn.classList.add('active');
                }}
            }}
            
            function resetChart() {{
                chart.timeScale().fitContent();
            }}
            
            function downloadChart() {{
                const image = chart.takeScreenshot();
                const link = document.createElement('a');
                link.href = image;
                link.download = '{ticker}_chart.png';
                link.click();
            }}
            
            // Responsive
            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: window.innerWidth }});
            }});
        </script>
    </body>
    </html>
    """
    
    components.html(chart_html, height=height + 50, scrolling=False)

def render_chart_with_tools(
    df: pd.DataFrame,
    ticker: str,
    show_indicators: bool = True
) -> None:
    """
    Main function to render professional chart in Streamlit
    with all the bells and whistles
    """
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days = st.select_slider(
            "📅 טווח ימים",
            options=[30, 60, 90, 120, 180],
            value=90,
            label_visibility="collapsed"
        )
    
    with col2:
        show_volume = st.checkbox("📊 נפח", value=True, label_visibility="collapsed")
    
    with col3:
        show_ma = st.checkbox("📈 ממוצעים", value=True, label_visibility="collapsed")
    
    with col4:
        show_bb = st.checkbox("🎯 בולינגר", value=False, label_visibility="collapsed")
    
    # Create chart
    create_professional_chart(
        df,
        ticker,
        height=600,
        show_volume=show_volume,
        show_ma20=show_ma,
        show_ma50=show_ma,
        show_sma200=show_ma,
        show_bb=show_bb,
        days=days
    )
    
    # Stats below chart
    st.divider()
    
    last_price = safe_last(df["Close"])
    last_high = safe_last(df["High"])
    last_low = safe_last(df["Low"])
    last_vol = safe_last(df["Volume"])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 מחיר אחרון", f"${last_price:.2f}" if not is_bad(last_price) else "—")
    
    with col2:
        st.metric("📈 שיא", f"${last_high:.2f}" if not is_bad(last_high) else "—")
    
    with col3:
        st.metric("📉 שפל", f"${last_low:.2f}" if not is_bad(last_low) else "—")
    
    with col4:
        chg_pct = ((last_price - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100) if len(df) > 1 else 0
        color = "green" if chg_pct >= 0 else "red"
        st.metric(f"{'📈' if chg_pct >= 0 else '📉'} שינוי יומי", f"{chg_pct:+.2f}%")
    
    with col5:
        st.metric("📦 נפח", f"{last_vol/1e6:.1f}M" if not is_bad(last_vol) else "—")

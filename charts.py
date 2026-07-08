"""
charts.py
Wyckoff Pro v3

Professional charts:
- Candlestick
- Volume
- Moving averages
- Bollinger Bands
- Wyckoff signals
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots



# =====================================================
# Main Stock Chart
# =====================================================

def create_stock_chart(
        df,
        ticker="Stock",
        wyckoff=None):


    fig = make_subplots(

        rows=3,

        cols=1,

        shared_xaxes=True,

        vertical_spacing=0.03,

        row_heights=[
            0.6,
            0.2,
            0.2
        ]

    )



    # -------------------------
    # Candlestick
    # -------------------------

    fig.add_trace(

        go.Candlestick(

            x=df.index,

            open=df["Open"],

            high=df["High"],

            low=df["Low"],

            close=df["Close"],

            name="Price"

        ),

        row=1,

        col=1

    )



    # -------------------------
    # Moving averages
    # -------------------------

    if "EMA20" in df:

        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["EMA20"],

                name="EMA20",

                line=dict(width=2)

            ),

            row=1,

            col=1

        )



    if "EMA50" in df:

        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["EMA50"],

                name="EMA50"

            ),

            row=1,

            col=1

        )



    # -------------------------
    # Bollinger
    # -------------------------

    if "BB_UPPER" in df:


        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["BB_UPPER"],

                name="BB Upper",

                opacity=0.4

            ),

            row=1,

            col=1

        )


        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["BB_LOWER"],

                name="BB Lower",

                opacity=0.4

            ),

            row=1,

            col=1

        )



    # -------------------------
    # Volume
    # -------------------------

    fig.add_trace(

        go.Bar(

            x=df.index,

            y=df["Volume"],

            name="Volume"

        ),

        row=2,

        col=1

    )



    # -------------------------
    # RSI
    # -------------------------

    if "RSI" in df:

        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["RSI"],

                name="RSI"

            ),

            row=3,

            col=1

        )



    # -------------------------
    # Wyckoff markers
    # -------------------------

    if wyckoff:


        if wyckoff.get(
            "spring",
            False
        ):


            fig.add_annotation(

                x=df.index[-1],

                y=df["Low"].iloc[-1],

                text="SPRING",

                showarrow=True

            )



        if wyckoff.get(
            "sos",
            False
        ):


            fig.add_annotation(

                x=df.index[-1],

                y=df["High"].iloc[-1],

                text="SOS",

                showarrow=True

            )



        if wyckoff.get(
            "lps",
            False
        ):


            fig.add_annotation(

                x=df.index[-1],

                y=df["Close"].iloc[-1],

                text="LPS",

                showarrow=True

            )



    # -------------------------
    # Layout
    # -------------------------

    score=""

    if wyckoff:

        score = (
            f" | Wyckoff "
            f"{wyckoff.get('wyckoff_score',0)}/10 "
            f"| {wyckoff.get('signal','')}"
        )



    fig.update_layout(

        title=
        f"{ticker}{score}",

        height=900,

        xaxis_rangeslider_visible=False,

        template="plotly_dark",

        hovermode="x unified"

    )



    return fig



# =====================================================
# Mini Chart
# =====================================================

def create_mini_chart(df,ticker):


    fig=go.Figure()


    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["Close"],

            name=ticker

        )

    )


    fig.update_layout(

        height=300,

        title=ticker,

        template="plotly_dark"

    )


    return fig

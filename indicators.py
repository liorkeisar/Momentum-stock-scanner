"""
indicators.py
Wyckoff Pro v3

Technical indicators engine
"""

import pandas as pd
import numpy as np


# =====================================================
# Moving Averages
# =====================================================

def add_moving_averages(df):

    df = df.copy()

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["EMA20"] = (
        df["Close"]
        .ewm(span=20, adjust=False)
        .mean()
    )

    df["EMA50"] = (
        df["Close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    df["EMA200"] = (
        df["Close"]
        .ewm(span=200, adjust=False)
        .mean()
    )

    return df



# =====================================================
# RSI
# =====================================================

def add_rsi(df, period=14):

    df = df.copy()

    delta = df["Close"].diff()

    gain = delta.where(
        delta > 0,
        0
    )

    loss = -delta.where(
        delta < 0,
        0
    )


    avg_gain = (
        gain
        .rolling(period)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(period)
        .mean()
    )


    rs = avg_gain / avg_loss.replace(0,np.nan)


    df["RSI"] = (
        100 -
        (100/(1+rs))
    )


    return df



# =====================================================
# MACD
# =====================================================

def add_macd(df):

    df = df.copy()


    ema12 = (
        df["Close"]
        .ewm(span=12,adjust=False)
        .mean()
    )

    ema26 = (
        df["Close"]
        .ewm(span=26,adjust=False)
        .mean()
    )


    df["MACD"] = ema12 - ema26


    df["MACD_SIGNAL"] = (
        df["MACD"]
        .ewm(span=9,adjust=False)
        .mean()
    )


    df["MACD_HIST"] = (
        df["MACD"]
        -
        df["MACD_SIGNAL"]
    )


    return df



# =====================================================
# ATR
# =====================================================

def add_atr(df, period=14):

    df = df.copy()


    high_low = (
        df["High"]
        -
        df["Low"]
    )


    high_close = (
        df["High"]
        -
        df["Close"].shift(1)
    ).abs()


    low_close = (
        df["Low"]
        -
        df["Close"].shift(1)
    ).abs()


    tr = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)


    df["ATR"] = (
        tr
        .rolling(period)
        .mean()
    )


    df["ATR_PERCENT"] = (
        df["ATR"]
        /
        df["Close"]
    ) * 100


    return df



# =====================================================
# Bollinger Bands
# =====================================================

def add_bollinger(df, period=20):

    df = df.copy()


    ma = (
        df["Close"]
        .rolling(period)
        .mean()
    )


    std = (
        df["Close"]
        .rolling(period)
        .std()
    )


    df["BB_MIDDLE"] = ma

    df["BB_UPPER"] = (
        ma + (2*std)
    )


    df["BB_LOWER"] = (
        ma - (2*std)
    )


    df["BB_WIDTH"] = (
        df["BB_UPPER"]
        -
        df["BB_LOWER"]
    ) / df["BB_MIDDLE"]


    return df



# =====================================================
# Keltner Channel
# =====================================================

def add_keltner(df):

    df = df.copy()


    middle = (
        df["Close"]
        .ewm(span=20)
        .mean()
    )


    df["KC_MIDDLE"] = middle


    df["KC_UPPER"] = (
        middle
        +
        1.5*df["ATR"]
    )


    df["KC_LOWER"] = (
        middle
        -
        1.5*df["ATR"]
    )


    return df



# =====================================================
# Volume Indicators
# =====================================================

def add_volume_indicators(df):

    df = df.copy()


    df["VOL_MA20"] = (
        df["Volume"]
        .rolling(20)
        .mean()
    )


    df["RVOL"] = (
        df["Volume"]
        /
        df["VOL_MA20"]
    )


    # Volume spike

    df["VOLUME_SPIKE"] = (
        df["RVOL"] >= 2
    )


    return df



# =====================================================
# OBV
# =====================================================

def add_obv(df):

    df = df.copy()


    direction = np.sign(
        df["Close"].diff()
    )


    df["OBV"] = (
        direction
        *
        df["Volume"]
    ).fillna(0).cumsum()


    return df



# =====================================================
# Accumulation / Distribution
# =====================================================

def add_ad_line(df):

    df = df.copy()


    money_flow = (

        (
        (df["Close"]-df["Low"])
        -
        (df["High"]-df["Close"])
        )

        /

        (df["High"]-df["Low"])
        .replace(0,np.nan)

    )


    money_flow = (
        money_flow
        *
        df["Volume"]
    )


    df["AD_LINE"] = (
        money_flow
        .fillna(0)
        .cumsum()
    )


    return df



# =====================================================
# MFI
# =====================================================

def add_mfi(df,period=14):

    df = df.copy()


    typical = (
        df["High"]
        +
        df["Low"]
        +
        df["Close"]
    ) / 3


    money = (
        typical
        *
        df["Volume"]
    )


    positive = (
        money
        .where(
            typical > typical.shift(1),
            0
        )
        .rolling(period)
        .sum()
    )


    negative = (
        money
        .where(
            typical < typical.shift(1),
            0
        )
        .rolling(period)
        .sum()
    )


    ratio = (
        positive /
        negative.replace(0,np.nan)
    )


    df["MFI"] = (
        100 -
        (100/(1+ratio))
    )


    return df



# =====================================================
# VWAP
# =====================================================

def add_vwap(df):

    df = df.copy()


    typical = (
        df["High"]
        +
        df["Low"]
        +
        df["Close"]
    ) / 3


    df["VWAP"] = (

        typical
        *
        df["Volume"]

    ).cumsum() / df["Volume"].cumsum()


    return df



# =====================================================
# Master Function
# =====================================================

def add_all_indicators(df):

    if df is None or df.empty:

        return pd.DataFrame()


    df = df.copy()


    df = add_moving_averages(df)

    df = add_rsi(df)

    df = add_macd(df)

    df = add_atr(df)

    df = add_bollinger(df)

    df = add_keltner(df)

    df = add_volume_indicators(df)

    df = add_obv(df)

    df = add_ad_line(df)

    df = add_mfi(df)

    df = add_vwap(df)


    return df

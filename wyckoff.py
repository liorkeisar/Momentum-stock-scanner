"""
wyckoff.py
Wyckoff Pro v3

Wyckoff analysis engine:
- Accumulation
- Distribution
- Spring
- SOS
- LPS
- Smart Money Score
- Wyckoff Score 0-10
"""

import numpy as np
import pandas as pd



# =====================================================
# Helpers
# =====================================================

def last_value(series):

    try:
        return float(series.iloc[-1])
    except:
        return 0



def normalize(value, minimum, maximum):

    if maximum == minimum:
        return 0

    score = (value-minimum)/(maximum-minimum)

    return max(0,min(1,score))



# =====================================================
# Volume / Smart Money
# =====================================================

def smart_money_score(df):

    score = 0


    # OBV rising

    if (
        last_value(df["OBV"])
        >
        last_value(df["OBV"].shift(20))
    ):
        score += 30



    # Accumulation line

    if (
        last_value(df["AD_LINE"])
        >
        last_value(df["AD_LINE"].shift(20))
    ):
        score += 30



    # Volume support

    if (
        last_value(df["RVOL"])
        >
        1.2
    ):
        score += 40



    return score



# =====================================================
# Price Compression
# =====================================================

def compression_score(df):

    if len(df)<30:
        return 0


    volatility_old = (
        df["Close"]
        .pct_change()
        .rolling(20)
        .std()
        .iloc[-20]
    )


    volatility_new = (
        df["Close"]
        .pct_change()
        .rolling(20)
        .std()
        .iloc[-1]
    )


    if volatility_old == 0:
        return 0


    reduction = (
        1 -
        volatility_new/volatility_old
    )


    return max(
        0,
        min(
            100,
            reduction*100
        )
    )



# =====================================================
# Spring Detection
# =====================================================

def detect_spring(df):

    if len(df)<30:
        return False


    recent = df.tail(30)


    support = (
        recent["Low"]
        .min()
    )


    last = recent.iloc[-1]


    spring = (

        last["Low"] < support*1.02

        and

        last["Close"] > support

        and

        last["Volume"] > recent["Volume"].mean()

    )


    return bool(spring)



# =====================================================
# SOS (Sign Of Strength)
# =====================================================

def detect_sos(df):

    if len(df)<40:
        return False


    high20 = (
        df["High"]
        .rolling(20)
        .max()
        .iloc[-2]
    )


    last = df.iloc[-1]


    sos = (

        last["Close"] > high20

        and

        last["RVOL"] > 1.5

    )


    return bool(sos)



# =====================================================
# LPS (Last Point Support)
# =====================================================

def detect_lps(df):

    if len(df)<30:
        return False


    last = df.iloc[-1]


    lps = (

        last["Close"] >
        last["EMA50"]

        and

        last["RVOL"] < 1.2

        and

        last["RSI"] > 45

    )


    return bool(lps)



# =====================================================
# Distribution Detection
# =====================================================

def detect_distribution(df):

    score = 0


    if (
        last_value(df["Close"])
        <
        last_value(df["EMA50"])
    ):
        score += 40


    if (
        last_value(df["OBV"])
        <
        last_value(df["OBV"].shift(20))
    ):
        score += 30


    if (
        last_value(df["RVOL"])
        >
        1.5
    ):
        score += 30



    return score >= 70



# =====================================================
# Accumulation Detection
# =====================================================

def detect_accumulation(df):

    score = 0


    if (
        last_value(df["Close"])
        >
        last_value(df["EMA50"])
    ):
        score += 30



    if smart_money_score(df)>50:
        score += 40



    if compression_score(df)>50:
        score += 30



    return score>=70



# =====================================================
# Main Wyckoff Engine
# =====================================================

def calculate_wyckoff(df):


    result = {


        "wyckoff_score":0,

        "phase":"UNKNOWN",

        "spring":False,

        "sos":False,

        "lps":False,

        "smart_money":0,

        "signal":"WAIT"


    }



    if df is None or df.empty:

        return result



    smart = smart_money_score(df)

    compression = compression_score(df)


    spring = detect_spring(df)

    sos = detect_sos(df)

    lps = detect_lps(df)



    score = 0



    # Smart money

    score += smart*0.25


    # Compression

    score += compression*0.20



    # Patterns

    if spring:
        score += 15


    if sos:
        score += 20


    if lps:
        score += 10



    # Trend

    if (
        last_value(df["Close"])
        >
        last_value(df["EMA50"])
    ):
        score += 10



    score = min(
        100,
        score
    )



    wyckoff10 = round(
        score/10,
        1
    )



    if detect_accumulation(df):

        phase="ACCUMULATION"

    elif detect_distribution(df):

        phase="DISTRIBUTION"

    else:

        phase="NEUTRAL"



    if wyckoff10 >=8:

        signal="STRONG BUY"

    elif wyckoff10 >=6:

        signal="BUY"

    elif wyckoff10 >=4:

        signal="WATCH"

    else:

        signal="AVOID"



    result.update({

        "wyckoff_score":wyckoff10,

        "phase":phase,

        "spring":spring,

        "sos":sos,

        "lps":lps,

        "smart_money":round(smart,1),

        "signal":signal

    })


    return result

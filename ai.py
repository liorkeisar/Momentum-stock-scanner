"""
ai.py
Wyckoff Pro v3

AI Prediction Engine:
- Feature engineering
- Machine learning model
- Breakout probability
- Model save/load
- Backtest support
"""

import os
import pickle
import numpy as np
import pandas as pd

from utils import log, log_error


MODEL_FILE = "wyckoff_ai_model.pkl"


# =====================================================
# Feature Engineering
# =====================================================

def create_features(df):

    try:

        data = df.copy()


        features = pd.DataFrame(index=data.index)


        features["return_5"] = (
            data["Close"]
            .pct_change(5)
        )


        features["return_20"] = (
            data["Close"]
            .pct_change(20)
        )


        features["volume_ratio"] = (
            data["Volume"]
            /
            data["Volume"]
            .rolling(20)
            .mean()
        )


        features["rsi"] = data["RSI"]


        features["macd"] = (
            data["MACD_HIST"]
        )


        features["atr"] = (
            data["ATR_PERCENT"]
        )


        features["obv_change"] = (
            data["OBV"]
            .pct_change(20)
        )


        features["smart_money"] = (

            (
                data["AD_LINE"]
                .pct_change(20)

            )

        )


        features["bb_width"] = (
            data["BB_WIDTH"]
        )


        features["trend"] = (

            data["Close"]
            /
            data["EMA50"]

        )


        features.replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan,
            inplace=True
        )


        features.dropna(
            inplace=True
        )


        return features



    except Exception as e:

        log_error(e)

        return pd.DataFrame()



# =====================================================
# Create Labels
# =====================================================

def create_labels(
        df,
        days=10,
        target=0.05):


    labels=[]


    prices=df["Close"].values


    for i in range(
        len(prices)
    ):


        if i+days >= len(prices):

            labels.append(
                np.nan
            )

            continue



        future=max(
            prices[i+1:i+days+1]
        )


        change = (
            future-prices[i]
        ) / prices[i]



        if change >= target:

            labels.append(1)

        else:

            labels.append(0)



    return pd.Series(
        labels,
        index=df.index
    )



# =====================================================
# Train Model
# =====================================================

def train_model(df):

    try:

        from sklearn.ensemble import RandomForestClassifier


        X=create_features(
            df
        )


        y=create_labels(
            df
        )


        y=y.loc[
            X.index
        ]


        data=pd.concat(
            [
                X,
                y.rename("target")
            ],
            axis=1
        )


        data.dropna(
            inplace=True
        )


        if len(data)<100:

            return None



        X=data.drop(
            "target",
            axis=1
        )


        y=data["target"]



        model=RandomForestClassifier(

            n_estimators=200,

            max_depth=6,

            random_state=42

        )



        model.fit(
            X,
            y
        )



        save_model(
            model
        )


        return model



    except Exception as e:

        log_error(e)

        return None



# =====================================================
# Save / Load
# =====================================================

def save_model(model):

    try:

        with open(
            MODEL_FILE,
            "wb"
        ) as f:

            pickle.dump(
                model,
                f
            )


        return True


    except Exception as e:

        log_error(e)

        return False




def load_model():

    try:

        if not os.path.exists(
            MODEL_FILE
        ):

            return None



        with open(
            MODEL_FILE,
            "rb"
        ) as f:

            return pickle.load(f)



    except:

        return None



# =====================================================
# Prediction
# =====================================================

def predict_breakout(
        df,
        model=None):


    try:


        if model is None:

            model=load_model()



        if model is None:

            return {

                "probability":0,

                "signal":"NO MODEL"

            }



        features=create_features(
            df
        )


        if features.empty:

            return {

                "probability":0,

                "signal":"NO DATA"

            }



        last=features.tail(1)



        probability=model.predict_proba(
            last
        )[0][1]



        if probability>=0.75:

            signal="STRONG BUY"


        elif probability>=0.55:

            signal="BUY"


        elif probability>=0.40:

            signal="WATCH"


        else:

            signal="AVOID"



        return {

            "probability":
                round(
                    probability*100,
                    2
                ),

            "signal":
                signal

        }



    except Exception as e:

        log_error(e)

        return {

            "probability":0,

            "signal":"ERROR"

        }



# =====================================================
# Simple Backtest
# =====================================================

def backtest_predictions(
        df,
        model):


    try:

        features=create_features(
            df
        )


        predictions=model.predict(
            features
        )


        result=pd.DataFrame({

            "prediction":
                predictions

        },
        index=features.index)



        return result



    except Exception as e:

        log_error(e)

        return pd.DataFrame()

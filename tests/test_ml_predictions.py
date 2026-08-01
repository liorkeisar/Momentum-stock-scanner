import pandas as pd
import numpy as np
from modules import ml_predictions
from tests._helpers import create_price_df


def test_compute_features_for_ml_non_empty():
    df = create_price_df(400)
    feats = ml_predictions.compute_features_for_ml(df, window=20)
    assert isinstance(feats, pd.DataFrame)
    # expect at least some rows
    assert len(feats) > 0
    # expected feature columns
    for col in ["close_last", "std20", "rvol", "ema20_ema50", "macd_diff", "rsi", "label"]:
        assert col in feats.columns


def test_train_and_predict_prob():
    df = create_price_df(600)
    # train may return None if sklearn missing or not enough positive labels; that's acceptable
    model = ml_predictions.train_logistic_model(df)
    prob = ml_predictions.logistic_predict_probability(model, df)
    # prob should be None or a float in [0,1]
    if prob is not None:
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

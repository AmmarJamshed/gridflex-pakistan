"""Demand / flexibility / solar forecasting with classical ML."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression

from app.services.simulation import _demand_shape, _solar_shape


def _synthetic_history(n_days: int = 21, seed: int = 7) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    hours = n_days * 24
    demand = np.array([_demand_shape(h % 24) * 1500 * (1 + rng.normal(0, 0.03)) for h in range(hours)])
    solar = np.array([_solar_shape(h % 24) * 400 * (1 + rng.normal(0, 0.05)) for h in range(hours)])
    flex = demand * 0.12 * (1 + rng.normal(0, 0.04, size=hours))
    return {"demand": demand, "solar": solar, "flexibility": flex}


def _train_rf(y: np.ndarray) -> RandomForestRegressor:
    X, target = [], []
    for i in range(24, len(y)):
        hour = i % 24
        X.append([hour, y[i - 1], y[i - 2], y[i - 24], np.mean(y[i - 24 : i])])
        target.append(y[i])
    model = RandomForestRegressor(n_estimators=80, random_state=42)
    model.fit(np.array(X), np.array(target))
    return model


def _predict_horizon(model: RandomForestRegressor, series: np.ndarray, steps: int) -> list[float]:
    hist = list(series)
    preds: list[float] = []
    for _ in range(steps):
        i = len(hist)
        hour = i % 24
        features = np.array(
            [[hour, hist[-1], hist[-2], hist[-24], float(np.mean(hist[-24:]))]]
        )
        pred = float(model.predict(features)[0])
        preds.append(round(max(0.0, pred), 3))
        hist.append(pred)
    return preds


def forecast_all() -> dict[str, Any]:
    data = _synthetic_history()
    out: dict[str, Any] = {}
    horizons = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}

    for name in ("demand", "flexibility", "solar"):
        series = data[name]
        # Linear trend baseline
        idx = np.arange(len(series)).reshape(-1, 1)
        lr = LinearRegression().fit(idx, series)
        rf = _train_rf(series)
        out[name] = {
            "model_name": "RandomForestRegressor+LinearRegression",
            "horizons": {},
        }
        for label, steps in horizons.items():
            rf_preds = _predict_horizon(rf, series, steps)
            # Blend slight linear drift
            drift = float(lr.coef_[0]) * np.arange(1, steps + 1)
            blended = [round(max(0.0, p + d * 0.1), 3) for p, d in zip(rf_preds, drift)]
            out[name]["horizons"][label] = [
                {"step": i + 1, "value": v, "unit": "MW"} for i, v in enumerate(blended)
            ]
    return out


def isolation_forest_scores(values: list[float] | None = None) -> dict[str, Any]:
    data = _synthetic_history()
    series = np.array(values) if values else data["demand"]
    X = np.array([[i % 24, v] for i, v in enumerate(series)])
    clf = IsolationForest(contamination=0.05, random_state=42)
    preds = clf.fit_predict(X)
    scores = clf.decision_function(X)
    anomalies = [
        {"index": int(i), "value": float(series[i]), "score": float(scores[i])}
        for i, p in enumerate(preds)
        if p == -1
    ]
    return {
        "model_name": "IsolationForest",
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:50],
    }
"""Exploratory research regimes on risk levels and dependence, retaining raw-return controls."""

import numpy as np
import pandas as pd
from research.common import validate_returns
from research.models import filter_sequence, forward_step, emission
from research.practical_models import fit_hmm, smooth_origin, ewma_matrices


def risk_features(r):
    validate_returns(r)
    fast = ewma_matrices(r.to_numpy(), 0.90, 63)
    slow = ewma_matrices(r.to_numpy(), 0.97, 63)
    variance = np.diagonal(fast, axis1=1, axis2=2)
    groups = {
        "Equity log risk": ["SPY", "EFA", "EEM"],
        "Treasury log risk": ["IEF", "TLT"],
        "Credit log risk": ["LQD"],
        "Real-asset log risk": ["GLD", "DBC"],
    }
    result = {}
    for name, assets in groups.items():
        indices = [r.columns.get_loc(a) for a in assets]
        result[name] = 0.5 * np.log(np.maximum(variance[:, indices].mean(axis=1), 1e-12))
    i, j = r.columns.get_loc("SPY"), r.columns.get_loc("TLT")
    correlation = slow[:, i, j] / np.sqrt(slow[:, i, i] * slow[:, j, j])
    result["Equity–bond dependence"] = np.arctanh(np.clip(correlation, -0.95, 0.95))
    return pd.DataFrame(result, index=r.index).iloc[63:]


def fit_feature_hmm(x, raw_returns, states=3, seed=19):
    model = fit_hmm(x, states, seed)
    # Ordering by fitted log-risk levels, not feature volatility or macro names.
    model["order"] = np.argsort(model["hmm"].means_[:, :4].mean(axis=1))
    if model["valid"]:
        z = (x - model["mean"]) / model["std"]
        p = model["hmm"].predict_proba(z)
        model["second"] = (p.T @ (raw_returns**2)) / np.maximum(p.sum(axis=0)[:, None], 1e-12)
    return model


def replay_feature_hmm(r, states=3, seed=19, lookback=504, lags=(5, 20)):
    validate_returns(r)
    features = risk_features(r)
    r = r.reindex(features.index)
    x = features.to_numpy()
    dates = r.index
    if len(r) < lookback + 1:
        raise ValueError("Insufficient training history")
    model = None
    rows = []
    revisions = []
    fits = []
    history = []
    for t in range(lookback - 1, len(r)):
        refit = model is None or dates[t].to_period("M") != dates[t - 1].to_period("M")
        accepted = False
        if refit:
            candidate = fit_feature_hmm(
                x[t - lookback + 1 : t + 1],
                r.iloc[t - lookback + 1 : t + 1].to_numpy(),
                states,
                seed,
            )
            fits.append(
                {
                    "date": dates[t],
                    "training_start": dates[t - lookback + 1],
                    **{k: candidate[k] for k in ["valid", "gain", "iterations", "warnings"]},
                }
            )
            if candidate["valid"]:
                model = candidate
                z = (x[t - lookback + 1 : t + 1] - model["mean"]) / model["std"]
                h = model["hmm"]
                history = list(filter_sequence(z, h.startprob_, h.transmat_, h.means_, h._covars_))
                accepted = True
        if model is None:
            rows.append(
                {
                    "date": dates[t],
                    "p_high": np.nan,
                    "entropy": np.nan,
                    "label": np.nan,
                    "valid": False,
                    **{f"v_{a}": np.nan for a in r.columns},
                }
            )
            continue
        h = model["hmm"]
        if not accepted:
            z = (x[t] - model["mean"]) / model["std"]
            history.append(
                forward_step(history[-1] @ h.transmat_, emission(z, h.means_, h._covars_))
            )
        alpha = history[-1]
        ordered = alpha[model["order"]]
        risk = np.mean(
            [
                (alpha @ np.linalg.matrix_power(h.transmat_, j)) @ model["second"]
                for j in range(1, 6)
            ],
            axis=0,
        )
        row = {
            "date": dates[t],
            "p_high": ordered[-1],
            "entropy": -np.sum(ordered * np.log(np.maximum(ordered, 1e-300))) / np.log(states),
            "label": int(np.argmax(ordered)),
            "valid": True,
            **{f"p{j}": p for j, p in enumerate(ordered)},
            **{f"v_{a}": risk[j] for j, a in enumerate(r.columns)},
        }
        rows.append(row)
        for lag in lags:
            z = (x[t - lag + 1 : t + 1] - model["mean"]) / model["std"]
            ell = np.array([emission(v, h.means_, h._covars_) for v in z])
            p = smooth_origin(history[-lag - 1], ell, h.transmat_)[model["order"]]
            revisions.append(
                {
                    "state_date": dates[t - lag],
                    "available_date": dates[t],
                    "lag": lag,
                    "label": int(np.argmax(p)),
                    "p_high": p[-1],
                    "entropy": -np.sum(p * np.log(np.maximum(p, 1e-300))) / np.log(states),
                }
            )
        if len(history) > lookback + 31:
            history = history[-(lookback + 31) :]
    return pd.DataFrame(rows).set_index("date"), pd.DataFrame(revisions), pd.DataFrame(fits)

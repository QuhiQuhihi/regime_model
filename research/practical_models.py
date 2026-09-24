"""Regime recognition, delayed labels, review alarms and explicit recalibration policies."""

import hashlib
import json
import warnings
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from threadpoolctl import threadpool_limits
from research.models import emission, filter_sequence, forward_step
from research.common import sha, validate_returns
from research.practical_config import ROOT, PATHS, MANIFEST, SETTINGS


def smooth_origin(alpha, future_emissions, transition):
    """p(z_s | x through s+lag) from p(z_s | x through s), fixed parameters."""
    beta = np.zeros(len(alpha))
    log_a = np.log(np.maximum(transition, 1e-300))
    for e in np.asarray(future_emissions)[::-1]:
        beta = logsumexp(log_a + e[None, :] + beta[None, :], axis=1)
        beta -= logsumexp(beta)
    logp = np.log(np.maximum(alpha, 1e-300)) + beta
    return np.exp(logp - logsumexp(logp))


def fit_hmm(x, states=3, seed=19):
    mean, std = x.mean(axis=0), x.std(axis=0, ddof=1)
    if (std <= 0).any():
        raise ValueError("Constant feature")
    z = (x - mean) / std
    model = GaussianHMM(
        n_components=states,
        covariance_type="diag",
        n_iter=300,
        tol=0.01,
        min_covar=0.001,
        random_state=seed,
    )
    with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as caught:
        model.fit(z)
    history = list(model.monitor_.history)
    gain = history[-1] - history[-2] if len(history) > 1 else np.inf
    valid = (
        np.isfinite(model.means_).all()
        and np.isfinite(model._covars_).all()
        and (model._covars_ > 0).all()
        and -0.01 <= gain < 0.01
    )
    order = np.argsort(np.mean(model._covars_ + model.means_**2, axis=1))
    raw_second = model._covars_ * std**2 + (model.means_ * std + mean) ** 2
    return {
        "hmm": model,
        "mean": mean,
        "std": std,
        "order": order,
        "second": raw_second,
        "valid": bool(valid),
        "gain": float(gain),
        "iterations": int(model.monitor_.iter),
        "warnings": len(caught),
    }


def replay_hmm(r, states=3, seed=19, lookback=504, lags=(5, 20)):
    validate_returns(r)
    x = r.to_numpy()
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
            candidate = fit_hmm(x[t - lookback + 1 : t + 1], states, seed)
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


def cached_hmm(r, name="primary", representation="features", **kwargs):
    PATHS.mkdir(parents=True, exist_ok=True)
    inputs = {
        str(p.relative_to(ROOT)): sha(p)
        for p in [
            MANIFEST,
            ROOT / "research/practical_models.py",
            ROOT / "research/models.py",
            ROOT / "research/practical_config.py",
            ROOT / "research/feature_regimes.py",
        ]
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            {"inputs": inputs, "kwargs": kwargs, "representation": representation}, sort_keys=True
        ).encode()
    ).hexdigest()
    meta = PATHS / f"hmm_{name}.json"
    files = [PATHS / f"{name}_{suffix}.csv" for suffix in ["states", "revisions", "fits"]]
    if meta.exists() and all(f.exists() for f in files):
        saved = json.loads(meta.read_text())
        if saved["fingerprint"] == fingerprint and all(
            sha(f) == saved["hashes"][f.name] for f in files
        ):
            print("Reused HMM checkpoint:", name, flush=True)
            return (
                pd.read_csv(files[0], index_col="date", parse_dates=True),
                pd.read_csv(files[1], parse_dates=["state_date", "available_date"]),
                pd.read_csv(files[2], parse_dates=["date", "training_start"]),
            )
    if representation == "features":
        from research.feature_regimes import replay_feature_hmm

        result = replay_feature_hmm(r, **kwargs)
    else:
        result = replay_hmm(r, **kwargs)
    for i, (f, d) in enumerate(zip(files, result)):
        temp = f.with_suffix(".partial")
        d.to_csv(temp, index=i == 0)
        temp.replace(f)
    meta.write_text(
        json.dumps(
            {"fingerprint": fingerprint, "hashes": {f.name: sha(f) for f in files}}, indent=2
        )
        + "\n"
    )
    print("Saved HMM checkpoint:", name, flush=True)
    return result


def review_alarms(signal, threshold, confirmation=2, cooldown=21):
    """Confirmed threshold episode, rearmed below threshold, with a minimum spacing."""
    a = np.asarray(signal, float)
    flags = np.zeros(len(a), bool)
    count = 0
    armed = True
    previous = -cooldown
    for i, value in enumerate(a):
        if not np.isfinite(value) or value <= threshold:
            count = 0
            armed = True
        else:
            count += 1
            if armed and count >= confirmation and i - previous >= cooldown:
                flags[i] = True
                previous = i
                armed = False
    return flags


def ewma_matrices(x, decay, warmup):
    out = np.full((len(x), x.shape[1], x.shape[1]), np.nan)
    m = x[:warmup].T @ x[:warmup] / warmup
    out[warmup - 1] = m
    for t in range(warmup, len(x)):
        m = decay * m + (1 - decay) * np.outer(x[t], x[t])
        out[t] = m
    return out


def reset_matrices(x, alarms, warmup, settings):
    out = np.full((len(x), x.shape[1], x.shape[1]), np.nan)
    fast = np.zeros(len(x), bool)
    m = x[:warmup].T @ x[:warmup] / warmup
    remaining = 0
    for t in range(warmup - 1, len(x)):
        if t >= warmup:
            decay = settings["fast_decay"] if remaining else settings["slow_decay"]
            fast[t] = remaining > 0
            remaining = max(0, remaining - 1)
            m = decay * m + (1 - decay) * np.outer(x[t], x[t])
        if alarms[t]:
            z = x[t - settings["reset_window"] + 1 : t + 1]
            m = z.T @ z / len(z)
            remaining = settings["fast_sessions"]
            fast[t] = True
        out[t] = m
    return out, fast


def calibration(r, states, settings=None):
    settings = {**SETTINGS, **(settings or {})}
    x = r.to_numpy()
    warm = settings["lookback"] + settings["feature_warmup"]
    slow = ewma_matrices(x, settings["slow_decay"], warm)
    fast = ewma_matrices(x, settings["fast_decay"], warm)

    def dv(a):
        return np.diagonal(a, axis1=1, axis2=2)

    ratio = np.full(len(r), np.nan)
    ratio[warm - 1 :] = np.median(np.sqrt(dv(fast[warm - 1 :]) / dv(slow[warm - 1 :])), axis=1)
    p = states.p_high.reindex(r.index).to_numpy().copy()
    p[: warm - 1] = np.nan
    flags = {
        "Observable reset": review_alarms(
            ratio, settings["alarm_ratio"], settings["confirmation"], settings["cooldown"]
        ),
        "HMM reset": review_alarms(
            p, settings["hmm_alarm_probability"], settings["confirmation"], settings["cooldown"]
        ),
    }
    mats = {"Slow EWMA": slow, "Fast EWMA": fast}
    mode = {}
    for name, alarm in flags.items():
        mats[name], mode[name] = reset_matrices(x, alarm, warm, settings)
    shrink = settings["diagonal_shrinkage"]
    eye = np.eye(x.shape[1])
    mats = {k: (1 - shrink) * m + shrink * (dv(m)[:, :, None] * eye) for k, m in mats.items()}
    signals = pd.DataFrame(
        {
            "ratio": ratio,
            "p_high": p,
            **{k: v for k, v in flags.items()},
            **{k + " fast": v for k, v in mode.items()},
        },
        index=r.index,
    )
    signals.index.name = "date"
    return mats, signals


def score_calibration(r, mats, states, horizon=5):
    x = r.to_numpy()
    n, d = x.shape
    rows = []
    targets = np.full((n, d), np.nan)
    for t in range(n - horizon):
        targets[t] = (x[t + 1 : t + horizon + 1] ** 2).mean(axis=0)
    forecasts = {name: np.diagonal(m, axis1=1, axis2=2) for name, m in mats.items()}
    hv = states[[f"v_{a}" for a in r.columns]].reindex(r.index).to_numpy()
    # First failed fit has no HMM forecast; the stated fallback is slow EWMA.
    forecasts["HMM state forecast"] = np.where(np.isfinite(hv), hv, forecasts["Slow EWMA"])
    w = np.array([0.25 if a in ["SPY", "TLT", "GLD", "DBC"] else 0 for a in r.columns])
    basket = x @ w
    for name, v in forecasts.items():
        valid = np.isfinite(v).all(axis=1) & np.isfinite(targets).all(axis=1)
        ix = np.flatnonzero(valid)
        pred = np.maximum(v[ix], 1e-10)
        for j, a in enumerate(r.columns):
            rows.append(
                pd.DataFrame(
                    {
                        "date": r.index[ix],
                        "target_start": r.index[ix + 1],
                        "target_end": r.index[ix + horizon],
                        "method": name,
                        "asset": a,
                        "forecast": pred[:, j],
                        "target": targets[ix, j],
                        "loss": np.log(pred[:, j]) + targets[ix, j] / pred[:, j],
                    }
                )
            )
        if name in mats:
            bv = np.maximum(np.einsum("i,tij,j->t", w, mats[name][ix], w), 1e-10)
            bt = np.array([(basket[t + 1 : t + horizon + 1] ** 2).mean() for t in ix])
            rows.append(
                pd.DataFrame(
                    {
                        "date": r.index[ix],
                        "target_start": r.index[ix + 1],
                        "target_end": r.index[ix + horizon],
                        "method": name,
                        "asset": "BASKET",
                        "forecast": bv,
                        "target": bt,
                        "loss": np.log(bv) + bt / bv,
                    }
                )
            )
    return pd.concat(rows, ignore_index=True)

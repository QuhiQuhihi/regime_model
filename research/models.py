"""Training-only Gaussian models and a forward filter with no future dependence."""

import warnings
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from sklearn.mixture import GaussianMixture
from hmmlearn.hmm import GaussianHMM
from threadpoolctl import threadpool_limits
from research.common import validate_returns, trading_cost


def emission(x, means, variances):
    x = np.asarray(x)
    v = np.maximum(np.asarray(variances), 1e-12)
    return -0.5 * np.sum(np.log(2 * np.pi * v) + (x - means) ** 2 / v, axis=-1)


def forward_step(prior, log_emission):
    prior = np.asarray(prior, float)
    if np.any(prior < 0) or not np.isfinite(prior).all() or not np.isclose(prior.sum(), 1):
        raise ValueError("Invalid probability")
    logp = np.log(np.maximum(prior, 1e-300)) + log_emission
    return np.exp(logp - logsumexp(logp))


def filter_sequence(x, start, transition, means, variances):
    alpha = np.asarray(start, float)
    out = []
    for i, row in enumerate(x):
        alpha = forward_step(
            alpha if i == 0 else alpha @ transition, emission(row, means, variances)
        )
        out.append(alpha)
    return np.asarray(out)


def fit_models(training, k=2, seed=19, floor=0.001):
    mu = training.mean(axis=0)
    std = training.std(axis=0, ddof=1)
    if (std <= 0).any():
        raise ValueError("Zero variance feature")
    z = (training - mu) / std
    with threadpool_limits(limits=1):
        gm = GaussianMixture(
            n_components=k,
            covariance_type="diag",
            n_init=3,
            reg_covar=floor,
            random_state=seed,
            max_iter=200,
        ).fit(z)
        hmm = GaussianHMM(
            n_components=k,
            covariance_type="diag",
            n_iter=200,
            tol=0.01,
            min_covar=floor,
            random_state=seed,
        )
        with warnings.catch_warnings(record=True) as caught:
            hmm.fit(z)
    # hmmlearn's converged also returns True on max iterations; inspect actual gain.
    history = list(hmm.monitor_.history)
    gain = history[-1] - history[-2] if len(history) > 1 else np.inf
    hmm_ok = bool(
        np.isfinite(hmm.means_).all()
        and np.isfinite(hmm._covars_).all()
        and np.all(hmm._covars_ > 0)
        and -0.01 <= gain < 0.01
    )
    gm_ok = bool(gm.converged_ and np.isfinite(gm.covariances_).all())
    alpha = (
        filter_sequence(z, hmm.startprob_, hmm.transmat_, hmm.means_, hmm._covars_)[-1]
        if hmm_ok
        else np.full(k, 1 / k)
    )
    raw_mu = hmm.means_[:, 0] * std[0] + mu[0]
    raw_var = hmm._covars_[:, 0] * std[0] ** 2
    second = raw_var + raw_mu**2
    order = np.argsort(second)
    gsecond = gm.covariances_[:, 0] * std[0] ** 2 + (gm.means_[:, 0] * std[0] + mu[0]) ** 2
    info = {
        "hmm_ok": hmm_ok,
        "gmm_ok": gm_ok,
        "gain": float(gain),
        "iterations": int(hmm.monitor_.iter),
        "warnings": len(caught),
        "state_order": ",".join(map(str, order)),
    }
    for rank, j in enumerate(order):
        info[f"state{rank}_mean"] = raw_mu[j]
        info[f"state{rank}_second_moment"] = second[j]
        info[f"state{rank}_training_occupancy"] = float(hmm.predict_proba(z)[:, j].mean())
        for rank2, j2 in enumerate(order):
            info[f"A{rank}{rank2}"] = hmm.transmat_[j, j2]
    return {
        "hmm": hmm,
        "gmm": gm,
        "mean": mu,
        "std": std,
        "alpha": alpha,
        "second": second,
        "gsecond": gsecond,
        "order": order,
        "info": info,
    }


def forecasts(
    returns, k=2, seed=19, floor=0.001, features=("SPY", "TLT"), start="2020-08-01", lookback=504
):
    validate_returns(returns)
    x = returns.loc[:, list(features)].to_numpy()
    spy = returns.SPY.to_numpy()
    dates = returns.index
    eligible = np.flatnonzero(dates >= pd.Timestamp(start))
    if not len(eligible) or eligible[0] + 1 < lookback:
        raise ValueError("Insufficient warmup")
    first = int(eligible[0])
    ewma = float(np.mean(spy[:21] ** 2))
    for t in range(21, first):
        ewma = 0.94 * ewma + 0.06 * spy[t] ** 2
    model = None
    rows = []
    fits = []
    for t in range(first, len(dates) - 1):
        ewma = 0.94 * ewma + 0.06 * spy[t] ** 2
        refit = model is None or dates[t].month != dates[t - 1].month
        if refit:
            model = fit_models(x[t - lookback + 1 : t + 1], k, seed, floor)
            fits.append(
                {
                    "information_date": dates[t],
                    "training_start": dates[t - lookback + 1],
                    **model["info"],
                }
            )
            single = float(np.mean(spy[t - lookback + 1 : t + 1] ** 2))
        else:
            hmm = model["hmm"]
            z = (x[t] - model["mean"]) / model["std"]
            if model["info"]["hmm_ok"]:
                model["alpha"] = forward_step(
                    model["alpha"] @ hmm.transmat_, emission(z, hmm.means_, hmm._covars_)
                )
        hmm = model["hmm"]
        alpha = model["alpha"]
        nextp = alpha @ hmm.transmat_
        order = model["order"]
        hv = float(nextp @ model["second"]) if model["info"]["hmm_ok"] else ewma
        gv = float(model["gmm"].weights_ @ model["gsecond"]) if model["info"]["gmm_ok"] else ewma
        common = {
            "information_date": dates[t],
            "target_date": dates[t + 1],
            "target_squared": spy[t + 1] ** 2,
            "high_probability": alpha[order[-1]] if model["info"]["hmm_ok"] else np.nan,
            "entropy": -float(np.sum(alpha * np.log(np.maximum(alpha, 1e-300)))),
            "hmm_fallback": int(not model["info"]["hmm_ok"]),
            **{f"p_state{j}": alpha[a] for j, a in enumerate(order)},
        }
        for name, v in [("HMM", hv), ("GMM", gv), ("Single state", single), ("EWMA", ewma)]:
            v = max(v, 1e-8)
            rows.append(
                {**common, "model": name, "forecast": v, "loss": np.log(v) + spy[t + 1] ** 2 / v}
            )
    return pd.DataFrame(rows), pd.DataFrame(fits)


def overlay(returns, fc, bps=5):
    hmm = fc.query('model=="HMM"').set_index("information_date")
    ewma = fc.query('model=="EWMA"').set_index("information_date")
    first = returns.index.get_loc(hmm.index[0]) + 1
    weights = {"HMM overlay": 0.0, "EWMA target": 0.0, "Static 62.5%": 0.0}
    rows = []
    for t in range(first, len(returns)):
        info = returns.index[t - 1]
        date = returns.index[t]
        r = returns.SPY.iloc[t]
        if info not in hmm.index:
            continue
        vol = min(1.0, 0.10 / np.sqrt(252 * ewma.loc[info, "forecast"]))
        hp = hmm.loc[info, "high_probability"]
        hw = 1 - 0.75 * hp if np.isfinite(hp) else vol
        target = {"HMM overlay": hw, "EWMA target": vol, "Static 62.5%": 0.625}
        for name, w in weights.items():
            gross = w * r
            pre = w * (1 + r) / (1 + gross)
            fee, trade = trading_cost([pre], [target[name]], bps)
            rows.append(
                {
                    "date": date,
                    "information_date": info,
                    "strategy": name,
                    "earning_weight": w,
                    "cash": 1 - w,
                    "target_weight": target[name],
                    "trade": trade[0],
                    "cost": fee,
                    "turnover": abs(trade[0]),
                    "gross": gross,
                    "net": (1 + gross) * (1 - fee) - 1,
                }
            )
            weights[name] = target[name]
    return pd.DataFrame(rows)


def best_split(x, minimum=40):
    """One Gaussian variance/mean split; independent pedagogical GGS approximation."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 2 * minimum:
        return 0.0, None
    s = np.r_[0, np.cumsum(x)]
    q = np.r_[0, np.cumsum(x * x)]
    ix = np.arange(minimum, n - minimum + 1)

    def cost(a, b):
        count = b - a
        v = (q[b] - q[a]) / count - ((s[b] - s[a]) / count) ** 2
        return count * np.log(np.maximum(v, 1e-10))

    gain = cost(0, n) - cost(0, ix) - cost(ix, n)
    j = np.argmax(gain)
    return float(gain[j]), int(ix[j])


def segment(x, max_breaks=5, minimum=40):
    bounds = [0, len(x)]
    for _ in range(max_breaks):
        choices = []
        for left, right in zip(bounds[:-1], bounds[1:]):
            gain, bp = best_split(np.asarray(x)[left:right], minimum)
            if bp is not None:
                choices.append((gain, left + bp))
        if not choices:
            break
        gain, bp = max(choices)
        if gain < 20:
            break
        bounds = sorted([*bounds, bp])
    return bounds


def synthetic_detection():
    rows = []
    for seed in range(50):
        for kind in ["null", "variance_break"]:
            rng = np.random.default_rng(20260919 + seed)
            x = rng.normal(0, 1, 400)
            if kind == "variance_break":
                x[200:] *= 3
            alarm, bp = None, None
            for endpoint in range(80, 401, 5):
                gain, loc = best_split(x[:endpoint])
                if gain > 20:
                    alarm, bp = endpoint, loc
                    break
            rows.append(
                {
                    "seed": seed,
                    "case": kind,
                    "true_break": 200 if kind != "null" else np.nan,
                    "alarm_date_index": alarm,
                    "estimated_break": bp,
                    "false_alarm": int(alarm is not None and (kind == "null" or alarm <= 200)),
                    "detected_after_change": int(
                        kind != "null" and alarm is not None and alarm > 200
                    ),
                    "delay": alarm - 200
                    if kind != "null" and alarm is not None and alarm > 200
                    else np.nan,
                }
            )
    return pd.DataFrame(rows)

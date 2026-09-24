"""Matched historical calibration scores and explicit speed/revision diagnostics."""

import numpy as np
import pandas as pd
from research.practical_config import ASSETS
from research.practical_models import review_alarms, ewma_matrices
from research.feature_regimes import risk_features, fit_feature_hmm


def paired_intervals(frame, block=63, draws=2000):
    """Common circular-block draws preserve cross-asset and cross-method dependence."""
    a = frame.to_numpy()
    n = len(a)
    rng = np.random.default_rng(20260924)
    estimates = []
    for _ in range(draws):
        starts = rng.integers(0, n, int(np.ceil(n / block)))
        ix = ((starts[:, None] + np.arange(block)) % n).ravel()[:n]
        estimates.append(a[ix].mean(axis=0))
    lo, hi = np.quantile(estimates, [0.025, 0.975], axis=0)
    return pd.DataFrame(
        {
            "contrast": frame.columns,
            "estimate": a.mean(axis=0),
            "lower95": lo,
            "upper95": hi,
            "n": n,
            "block": block,
            "draws": draws,
        }
    )


def summarize_scores(scores):
    asset = scores[scores.asset != "BASKET"]
    daily = asset.groupby(["date", "method"]).loss.mean().unstack()
    delta = daily.subtract(daily["Slow EWMA"], axis=0).drop(columns="Slow EWMA")
    summary = paired_intervals(delta)
    summary["endpoint"] = "Eight-asset mean"
    basket = scores[scores.asset == "BASKET"].pivot(index="date", columns="method", values="loss")
    bd = basket.subtract(basket["Slow EWMA"], axis=0).drop(columns="Slow EWMA")
    bsummary = paired_intervals(bd)
    bsummary["endpoint"] = "Four-asset basket"
    extra = []
    for block in [21, 126]:
        item = paired_intervals(delta[["HMM reset"]], block)
        item["endpoint"] = "Eight-asset mean"
        extra.append(item)
    by_asset = asset.pivot(index="date", columns=["asset", "method"], values="loss")
    ad = {}
    for a in ASSETS:
        for method in ["Fast EWMA", "Observable reset", "HMM reset", "HMM state forecast"]:
            ad[a + "|" + method] = by_asset[(a, method)] - by_asset[(a, "Slow EWMA")]
    ai = paired_intervals(pd.DataFrame(ad))
    ai[["asset", "method"]] = ai.contrast.str.split("|", expand=True)
    periods = []
    for label, start, end in [
        ("2008–2014", "2008-01-01", "2014-12-31"),
        ("2015–2019", "2015-01-01", "2019-12-31"),
        ("2020–2023", "2020-01-01", "2023-12-31"),
        ("2024–latest", "2024-01-01", "2100-01-01"),
    ]:
        for name in delta:
            s = delta.loc[start:end, name]
            periods.append(
                {"period": label, "method": name, "n": len(s), "mean_loss_difference": s.mean()}
            )
    calibration = (
        asset.groupby(["asset", "method"])
        .agg(
            n=("loss", "size"),
            mean_forecast=("forecast", "mean"),
            mean_target=("target", "mean"),
            mean_loss=("loss", "mean"),
        )
        .reset_index()
    )
    calibration["realized_to_predicted"] = calibration.mean_target / calibration.mean_forecast
    return (
        pd.concat([summary, bsummary, *extra], ignore_index=True),
        ai,
        pd.DataFrame(periods),
        calibration,
        delta,
    )


def retrospective(r):
    features = risk_features(r)
    r = r.reindex(features.index)
    model = fit_feature_hmm(features.to_numpy(), r.to_numpy(), 3, 19)
    if not model["valid"]:
        raise ValueError("Full-sample descriptive HMM did not converge")
    z = (features.to_numpy() - model["mean"]) / model["std"]
    p = model["hmm"].predict_proba(z)[:, model["order"]]
    result = pd.DataFrame(p, index=r.index, columns=["p0", "p1", "p2"])
    result["label"] = p.argmax(axis=1)
    result["p_high"] = p[:, -1]
    result["entropy"] = -(p * np.log(np.maximum(p, 1e-300))).sum(axis=1) / np.log(3)
    fingerprints = []
    for label in range(3):
        data = r.loc[result.label == label]
        for a in r.columns:
            fingerprints.append(
                {
                    "state": label,
                    "asset": a,
                    "n": len(data),
                    "annual_mean": data[a].mean() * 252,
                    "annual_volatility": data[a].std() * np.sqrt(252),
                    "equity_bond_correlation": data.SPY.corr(data.TLT),
                }
            )
    return result, pd.DataFrame(fingerprints)


def revision_summary(states, revisions, retro):
    joined = states[["label", "entropy"]].rename(
        columns={"label": "original", "entropy": "original_entropy"}
    )
    for lag in [5, 20]:
        v = revisions[revisions.lag == lag].set_index("state_date")
        joined = joined.join(
            v[["label", "entropy"]].rename(
                columns={"label": f"lag{lag}", "entropy": f"entropy{lag}"}
            )
        )
    joined = joined.join(
        retro[["label", "entropy"]].rename(columns={"label": "full", "entropy": "full_entropy"})
    ).dropna()
    rows = []
    for field, entropy, wait in [
        ("original", "original_entropy", 0),
        ("lag5", "entropy5", 5),
        ("lag20", "entropy20", 20),
        ("full", "full_entropy", None),
    ]:
        rows.append(
            {
                "lens": field,
                "waiting_sessions": wait,
                "n": len(joined),
                "changed_from_original": (joined[field] != joined.original).mean(),
                "agreement_with_full_description": (joined[field] == joined.full).mean(),
                "mean_normalized_entropy": joined[entropy].mean(),
            }
        )
    return pd.DataFrame(rows)


def reference_events(r, signals):
    # At date t: 20 recent observations vs 126 immediately preceding that window.
    recent = r.rolling(20).std()
    earlier = r.shift(20).rolling(126).std()
    ref = (recent / earlier).median(axis=1, skipna=False)
    valid = signals.ratio.notna()
    mask = review_alarms(ref.where(valid), 1.5, 2, 63)
    refs = np.flatnonzero(mask)
    matches = []
    burdens = []
    dates = r.index
    for method in ["Observable reset", "HMM reset"]:
        alarms = np.flatnonzero(signals[method].to_numpy())
        used = set()
        for i in refs:
            eligible = [a for a in alarms if i - 20 <= a <= i + 40 and a not in used]
            alarm = eligible[0] if eligible else None
            if alarm is not None:
                used.add(alarm)
            matches.append(
                {
                    "reference_date": dates[i],
                    "method": method,
                    "alarm_date": dates[alarm] if alarm is not None else pd.NaT,
                    "lag_sessions": alarm - i if alarm is not None else np.nan,
                    "hmm_stress_at_reference": bool(signals.p_high.iloc[i] > 0.7),
                    "sessions_since_latest_alarm": i - alarms[alarms <= i][-1]
                    if len(alarms[alarms <= i])
                    else np.nan,
                }
            )
        n = int(valid.sum())
        count = len(alarms)
        burdens.append(
            {
                "method": method,
                "sessions": n,
                "alarms": count,
                "alarms_per_year": count * 252 / n,
                "reference_episodes": len(refs),
                "matched_episodes": len(used),
                "unmatched_alarms": count - len(used),
                "fast_mode_fraction": signals.loc[valid, method + " fast"].mean(),
            }
        )
    return pd.DataFrame(matches), pd.DataFrame(burdens), ref


def synthetic_checks():
    rows = []
    warm = 126
    for case in ["Stationary", "Abrupt volatility", "Gradual volatility", "Correlation only"]:
        for seed in range(100):
            rng = np.random.default_rng(20260924 + seed)
            x = rng.normal(0, 0.01, (500, 8))
            if case == "Abrupt volatility":
                x[250:] *= 2
            elif case == "Gradual volatility":
                x[250:] *= np.minimum(2, 1 + np.arange(250) / 60)[:, None]
            elif case == "Correlation only":
                # Unit marginal variance before/after; only dependence changes.
                common = rng.normal(0, 0.01, (250, 1))
                x[250:] = np.sqrt(0.8) * common + np.sqrt(0.2) * x[250:]
            slow = ewma_matrices(x, 0.97, warm)
            fast = ewma_matrices(x, 0.90, warm)
            ratio = np.full(500, np.nan)
            ratio[warm - 1 :] = np.median(
                np.sqrt(
                    np.diagonal(fast[warm - 1 :], axis1=1, axis2=2)
                    / np.diagonal(slow[warm - 1 :], axis1=1, axis2=2)
                ),
                axis=1,
            )
            for threshold in [1.3, 1.5, 1.7]:
                flags = review_alarms(ratio, threshold, 2, 21)
                alarms = np.flatnonzero(flags)
                after = alarms[(alarms >= 250) & (alarms <= 310)]
                rows.append(
                    {
                        "case": case,
                        "threshold": threshold,
                        "seed": seed,
                        "prechange_alarm": bool(flags[:250].any()),
                        "any_alarm": bool(flags.any()),
                        "hit_by_60": bool(len(after)),
                        "delay": float(after[0] - 250) if len(after) else np.nan,
                    }
                )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["case", "threshold"], sort=False)
        .agg(
            paths=("seed", "size"),
            prechange_alarm_rate=("prechange_alarm", "mean"),
            any_alarm_rate=("any_alarm", "mean"),
            hit_by_60=("hit_by_60", "mean"),
            conditional_median_delay=("delay", "median"),
        )
        .reset_index()
    )
    return detail, summary

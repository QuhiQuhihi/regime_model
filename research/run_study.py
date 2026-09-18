"""Walk-forward risk forecasts, original decision paths and retrospective diagnostics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import json
import numpy as np
import pandas as pd
from research.models import forecasts, overlay, fit_models, segment, synthetic_detection
from research.common import (
    ROOT,
    RESULTS,
    FIGURES,
    load_returns,
    performance,
    block_interval,
    table,
    plot_style,
    write_metadata,
    provenance,
    sha,
)


def cached_forecasts(r, name, kw):
    dest = RESULTS / "paths"
    dest.mkdir(exist_ok=True)
    path = dest / f"forecasts_{name}.csv"
    fitpath = dest / f"fits_{name}.csv"
    meta = dest / f"cache_{name}.json"
    signature = hashlib.sha256(
        json.dumps({"provenance": provenance(), "kwargs": kw}, sort_keys=True).encode()
    ).hexdigest()
    if path.exists() and fitpath.exists() and meta.exists():
        m = json.loads(meta.read_text())
        if (
            m["signature"] == signature
            and m["forecasts"] == sha(path)
            and m["fits"] == sha(fitpath)
        ):
            print("Cached", name, flush=True)
            return pd.read_csv(path, parse_dates=["information_date", "target_date"]), pd.read_csv(
                fitpath, parse_dates=["information_date", "training_start"]
            )
    fc, fits = forecasts(r, **kw)
    fc.to_csv(path, index=False)
    fits.to_csv(fitpath, index=False)
    meta.write_text(
        json.dumps({"signature": signature, "forecasts": sha(path), "fits": sha(fitpath)}, indent=2)
        + "\n"
    )
    print("Computed", name, flush=True)
    return fc, fits


def main():
    r = load_returns()
    fc, fits = cached_forecasts(r, "primary", {})
    summaries = []
    intervals = []
    for period, mask in [
        ("full", fc.target_date >= "2020-08-01"),
        ("late", fc.target_date >= "2025-01-01"),
    ]:
        subset = fc.loc[mask]
        p = subset.pivot(index="target_date", columns="model", values="loss")
        for name, g in subset.groupby("model"):
            summaries.append(
                {
                    "period": period,
                    "model": name,
                    "n": len(g),
                    "mean_loss": g.loss.mean(),
                    "mean_forecast": g.forecast.mean(),
                    "realized_to_predicted": g.target_squared.sum() / g.forecast.sum(),
                }
            )
        for name in ["HMM", "GMM", "Single state"]:
            for block in [5, 21, 63]:
                intervals.append(
                    {
                        "period": period,
                        "model": name,
                        "control": "EWMA",
                        **block_interval(p[name], p.EWMA, block=block),
                    }
                )
    pd.DataFrame(summaries).to_csv(RESULTS / "forecast_metrics.csv", index=False)
    intervals = pd.DataFrame(intervals)
    intervals.to_csv(RESULTS / "loss_intervals.csv", index=False)
    primary = intervals.query('period=="late" and model=="HMM" and block==21').iloc[0]
    sensitivity = []
    for name, kw in {
        "primary": {},
        "three_states": {"k": 3},
        "seed41": {"seed": 41},
        "floor01": {"floor": 0.01},
        "spy_only": {"features": ("SPY",)},
    }.items():
        f, fit = (fc, fits) if name == "primary" else cached_forecasts(r, name, kw)
        loss = f.query('target_date>="2025-01-01"').pivot(
            index="target_date", columns="model", values="loss"
        )
        sensitivity.append(
            {
                "variant": name,
                **block_interval(loss.HMM, loss.EWMA),
                "failed_hmm_refits": int((~fit.hmm_ok).sum()),
                "refits": len(fit),
            }
        )
    pd.DataFrame(sensitivity).to_csv(RESULTS / "sensitivity.csv", index=False)
    performance_rows = []
    for cost in [0, 5, 10]:
        ov = overlay(r, fc, cost)
        if cost == 5:
            ov.to_csv(RESULTS / "paths/overlay.csv", index=False)
        for name, g in ov.query('date>="2025-01-01"').groupby("strategy"):
            performance_rows.append(
                {
                    "cost_bps": cost,
                    "strategy": name,
                    **performance(g.net),
                    "annual_turnover": g.turnover.mean() * 252,
                    "mean_risky_weight": g.earning_weight.mean(),
                }
            )
    pd.DataFrame(performance_rows).to_csv(RESULTS / "overlay_performance.csv", index=False)
    ov = overlay(r, fc, 5)
    late = ov.query('date>="2025-01-01"').pivot(index="date", columns="strategy", values="net")
    pd.DataFrame(
        [
            {"control": b, **block_interval(late["HMM overlay"], late[b], "sharpe")}
            for b in ["EWMA target", "Static 62.5%"]
        ]
    ).to_csv(RESULTS / "overlay_intervals.csv", index=False)
    # Retrospective state estimates are deliberately isolated from decisions.
    model = fit_models(r[["SPY", "TLT"]].to_numpy())
    z = (r[["SPY", "TLT"]].to_numpy() - model["mean"]) / model["std"]
    retrospective = model["hmm"].predict_proba(z)[:, model["order"][-1]]
    causal = fc.query('model=="HMM"').set_index("information_date")
    retro = pd.Series(retrospective, index=r.index).reindex(causal.index)
    diag = pd.DataFrame(
        {
            "causal_high_probability": causal.high_probability,
            "full_sample_smoothed_high_probability": retro,
            "entropy": causal.entropy,
        }
    )
    diag.to_csv(RESULTS / "paths/state_comparison.csv")
    diag["month"] = diag.index.to_period("M").astype(str)
    monthly = diag.groupby("month").agg(
        causal_occupancy=("causal_high_probability", "mean"),
        retrospective_occupancy=("full_sample_smoothed_high_probability", "mean"),
        mean_entropy=("entropy", "mean"),
    )
    monthly.to_csv(RESULTS / "state_stability.csv")
    pd.DataFrame(
        [
            {
                "refits": len(fits),
                "hmm_failed_refits": int((~fits.hmm_ok).sum()),
                "gmm_failed_refits": int((~fits.gmm_ok).sum()),
                "fallback_forecast_days": int(causal.hmm_fallback.sum()),
                "mean_high_probability": causal.high_probability.mean(),
                "mean_entropy": causal.entropy.mean(),
                "hard_label_persistence": (
                    causal.high_probability.gt(0.5).iloc[1:].to_numpy()
                    == causal.high_probability.gt(0.5).iloc[:-1].to_numpy()
                ).mean(),
                "retrospective_label_disagreement": (
                    causal.high_probability.gt(0.5) != retro.gt(0.5)
                ).mean(),
            }
        ]
    ).to_csv(RESULTS / "diagnostics.csv", index=False)
    syn = synthetic_detection()
    syn.to_csv(RESULTS / "synthetic_detection.csv", index=False)
    bounds = segment(r.SPY.to_numpy())
    pd.DataFrame(
        {"break_index": bounds, "date": [r.index[min(i, len(r) - 1)] for i in bounds]}
    ).to_csv(RESULTS / "retrospective_breakpoints.csv", index=False)
    plt = plot_style()
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(diag.index, diag.causal_high_probability, label="Archived filtered probability")
    axes[0].set(
        ylabel="High-risk probability",
        title="Causal HMM states: information available at each close",
    )
    axes[0].legend()
    axes[1].plot(
        diag.index,
        diag.full_sample_smoothed_high_probability,
        color="#bc6c25",
        label="Full-sample smoothed probability",
    )
    axes[1].set(
        ylabel="High-risk probability",
        xlabel="Date",
        title="Retrospective HMM: future-dependent description only",
    )
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "states.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots()
    comparison_rows = intervals.query('period=="late" and block==21')
    ax.errorbar(
        comparison_rows.estimate,
        range(len(comparison_rows)),
        xerr=np.vstack(
            [
                comparison_rows.estimate - comparison_rows.lower95,
                comparison_rows.upper95 - comparison_rows.estimate,
            ]
        ),
        fmt="o",
        capsize=4,
    )
    ax.set_yticks(range(len(comparison_rows)), comparison_rows.model)
    ax.axvline(0, color="#555", ls="--")
    ax.set(
        xlabel="Mean loss difference vs EWMA (lower is better)",
        title=f"SPY forecasts, 2025-01-01–{fc.target_date.max():%Y-%m-%d}; 95% block intervals",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "forecast_comparison.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots()
    monthly[["causal_occupancy", "retrospective_occupancy"]].plot(ax=ax)
    ax.set(
        ylabel="Mean high-state probability",
        xlabel="Month",
        title="Original versus revised state descriptions",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "revisions.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots()
    net = ov.pivot(index="date", columns="strategy", values="net")
    ((1 + net).cumprod()).plot(ax=ax)
    ax.set(
        ylabel="Net wealth, entry capital = 1",
        xlabel="Close date",
        title="One-session execution delay; cash earns zero; 5 bp trades",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "overlay.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots()
    ax.plot(
        r.index, r.SPY.rolling(21).std() * np.sqrt(252), label="21-session SPY realized volatility"
    )
    for b in bounds[1:-1]:
        ax.axvline(r.index[b], color="#bc6c25", ls="--", alpha=0.7)
    ax.set(
        ylabel="Annualized return volatility",
        xlabel="Date",
        title="Full-sample greedy Gaussian splits: retrospective only",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "segmentation.png", dpi=150)
    plt.close(fig)
    null = syn.query('case=="null"')
    change = syn.query('case=="variance_break"')
    last = str(fc.target_date.max().date())
    findings = (
        f"""# Do market states improve risk forecasts?\n\nThrough {last}, the late-segment two-state HMM minus EWMA mean next-session risk loss is **{primary.estimate:+.4f}**, with paired 95% block interval **[{primary.lower95:+.4f}, {primary.upper95:+.4f}]**. Negative favors HMM. The result {"does not establish incremental forecasting value" if primary.upper95 >= 0 else "supports a conditional improvement in this sample"}, and does not establish general regime-prediction ability.\n\n![Forecast comparison](../research/figures/forecast_comparison.png)\n\n## Forecast evidence\n\n"""
        + table(pd.DataFrame(summaries).query('period=="late"'))
        + """\nThe loss uses the same next-session squared SPY return for all models. Its absolute level is not a performance percentage. A GMM is an iid mixture; its current posterior is not a Markov next-state forecast. HMM decisions use forward filtering, not full-sample smoothing.\n\n## Bounded sensitivity\n\n"""
        + table(pd.DataFrame(sensitivity))
        + """\nOne primary HMM/EWMA comparison; these extra intervals are pointwise exploratory diagnostics, not independent confirmations. Failed fits use EWMA and are counted.\n\n## Decisions after execution costs\n\n"""
        + table(
            pd.DataFrame(performance_rows).query("cost_bps==5")[
                [
                    "strategy",
                    "cagr",
                    "volatility",
                    "max_drawdown",
                    "annual_turnover",
                    "mean_risky_weight",
                ]
            ]
        )
        + """\nThe overlay trades one close after the signal and first earns the following session. This delay differs from the one-step forecast target; lower exposure can explain safer returns. Zero cash accrual, closing fills, fixed surviving ETFs and revised adjusted closes limit investability.\n\n## Description, detection and prediction\n\n"""
        + f"""The synthetic null alarm rate is {null.false_alarm.mean():.1%} across 50 runs. The variance-break example detects after the change in {change.detected_after_change.mean():.1%} of runs; conditional mean delay is {change.delay.mean():.1f} observations. These are constructed variance changes, not labeled market recessions. The simplified greedy splitter is not the complete optimized GGS algorithm.\n\n![Causal and retrospective states](../research/figures/states.png)\n\nFull-sample states revise historical labels using information unavailable then. This is useful historical organization but cannot substitute for the forecast comparison. No state is called a recession. Consult [methods](01-methods.md), [protocol](../research/PROTOCOL.md), [sources](../research/SOURCES.md), and [next experiment](../research/RESEARCH_AGENDA.md).\n"""
    )
    (ROOT / "docs/02-results.md").write_text(findings)
    readme = ROOT / "README.md"
    if readme.exists():
        parts = readme.read_text().split("\n\n", 2)
        readme.write_text(parts[0] + "\n\n" + findings.split("\n\n")[1] + "\n\n" + parts[2])
    (RESULTS / "headline.json").write_text(
        json.dumps(
            {"estimate": primary.estimate, "lower95": primary.lower95, "upper95": primary.upper95},
            indent=2,
        )
        + "\n"
    )
    write_metadata(
        {"k": 2, "seed": 19, "lookback": 504, "loss": "log(v)+r_next^2/v", "forecast_floor": 1e-8}
    )
    print(findings.split("\n\n")[1])


if __name__ == "__main__":
    main()

"""Historical regime replay for recognition, interpretation and model recalibration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
from research.common import sha
from research.practical_config import ROOT, RESULTS, FIGURES, PATHS, MANIFEST, SETTINGS, ASSETS
from research.practical_data import load_data
from research.practical_models import cached_hmm, calibration, score_calibration
from research.practical_analysis import (
    summarize_scores,
    retrospective,
    revision_summary,
    reference_events,
    synthetic_checks,
    paired_intervals,
)


def provenance():
    paths = [
        ROOT / "research/PROTOCOL.md",
        ROOT / "research/feature_design_20260924.md",
        MANIFEST,
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        *sorted((ROOT / "research").glob("*.py")),
    ]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def write_metadata():
    outputs = [*RESULTS.glob("*.csv"), *RESULTS.glob("*.json"), *FIGURES.glob("*.png")]
    outputs = [p for p in outputs if p.name != "run_metadata.json"]
    record = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "settings": SETTINGS,
        "source_and_code": provenance(),
        "outputs": {str(p.relative_to(ROOT)): sha(p) for p in outputs},
        "private_outputs": {
            str(p.relative_to(ROOT)): sha(p)
            for p in PATHS.glob("*")
            if p.suffix in [".csv", ".npz"]
        },
    }
    (RESULTS / "run_metadata.json").write_text(json.dumps(record, indent=2) + "\n")


def main():
    for p in [RESULTS, FIGURES, PATHS]:
        p.mkdir(parents=True, exist_ok=True)
    prices, r = load_data(write_audit=True)
    states, revisions, fits = cached_hmm(r, states=3, seed=19)
    mats, signals = calibration(r, states)
    raw_states, _, raw_fits = cached_hmm(
        r, name="raw_return", representation="returns", states=3, seed=19
    )
    raw_mats, raw_signals = calibration(r, raw_states)
    mats["Raw-return HMM reset"] = raw_mats["HMM reset"]
    representation_rows = []
    for name, st, sg in [
        ("Daily returns", raw_states, raw_signals),
        ("Risk and dependence features", states, signals),
    ]:
        aligned = st.reindex(states.index)
        representation_rows.append(
            {
                "representation": name,
                "label_switch_fraction": aligned.label.diff().iloc[1:].ne(0).mean(),
                "alarms": int(sg["HMM reset"].sum()),
                "alarms_per_year": sg["HMM reset"].sum() * 252 / len(states),
                "stressed_probability_share": aligned.p_high.gt(0.7).mean(),
            }
        )
    pd.DataFrame(representation_rows).to_csv(RESULTS / "representation_comparison.csv", index=False)
    scores = score_calibration(r, mats, states)
    scores.to_csv(PATHS / "scores.csv", index=False)
    signals.to_csv(PATHS / "signals.csv")
    np.savez_compressed(PATHS / "forecast_matrices.npz", **mats)
    summary, asset_ci, periods, ratios, delta = summarize_scores(scores)
    for name, data in [
        ("calibration_comparison", summary),
        ("asset_comparison", asset_ci),
        ("subperiods", periods),
        ("calibration_ratios", ratios),
    ]:
        data.to_csv(RESULTS / f"{name}.csv", index=False)
    retro, fingerprints = retrospective(r)
    retro.to_csv(PATHS / "retrospective.csv")
    fingerprints.to_csv(RESULTS / "state_fingerprints.csv", index=False)
    revision_summary(states, revisions, retro).to_csv(RESULTS / "label_revisions.csv", index=False)
    events, burden, reference = reference_events(r, signals)
    events.to_csv(RESULTS / "episode_timing.csv", index=False)
    burden.to_csv(RESULTS / "review_burden.csv", index=False)
    reference.rename("risk_escalation_reference").to_csv(PATHS / "reference.csv")
    synthetic, synthetic_summary = synthetic_checks()
    synthetic.to_csv(RESULTS / "synthetic_detection.csv", index=False)
    synthetic_summary.to_csv(RESULTS / "synthetic_summary.csv", index=False)
    sensitivity = []
    for name, kwargs in [
        ("Two states", {"states": 2, "seed": 19}),
        ("Seed 41", {"states": 3, "seed": 41}),
    ]:
        alternative, _, fit = cached_hmm(r, name=name.lower().replace(" ", "_"), **kwargs)
        am, _ = calibration(r, alternative)
        sc = score_calibration(r, am, alternative)
        daily = sc[sc.asset != "BASKET"].groupby(["date", "method"]).loss.mean().unstack()
        ci = paired_intervals((daily["HMM reset"] - daily["Slow EWMA"]).to_frame("HMM reset"))
        sensitivity.append(
            {"variant": name, **ci.iloc[0].to_dict(), "failed_refits": int((~fit.valid).sum())}
        )
    for name, key, value, method in [
        ("Observable 1.3", "alarm_ratio", 1.3, "Observable reset"),
        ("Observable 1.7", "alarm_ratio", 1.7, "Observable reset"),
        ("HMM 0.60", "hmm_alarm_probability", 0.60, "HMM reset"),
        ("HMM 0.80", "hmm_alarm_probability", 0.80, "HMM reset"),
    ]:
        am, sg = calibration(r, states, {key: value})
        sc = score_calibration(r, am, states)
        daily = sc[sc.asset != "BASKET"].groupby(["date", "method"]).loss.mean().unstack()
        ci = paired_intervals((daily[method] - daily["Slow EWMA"]).to_frame(method))
        sensitivity.append(
            {"variant": name, **ci.iloc[0].to_dict(), "alarms": int(sg[method].sum())}
        )
    pd.DataFrame(sensitivity).to_csv(RESULTS / "sensitivity.csv", index=False)
    # Public monthly summaries; full daily histories remain local.
    monthly = states[["p_high", "entropy"]].resample("ME").mean()
    monthly["full_sample_p_high"] = retro.p_high.resample("ME").mean()
    monthly["risk_ratio"] = signals.ratio.resample("ME").mean()
    monthly.to_csv(RESULTS / "monthly_monitor.csv")
    diag = {
        "hmm_refits": len(fits),
        "representation": "EWMA risk levels and equity-bond dependence",
        "calibration_warmup": SETTINGS["lookback"] + SETTINGS["feature_warmup"],
        "label_switch_fraction": states.label.diff().iloc[1:].ne(0).mean(),
        "raw_return_failed_refits": int((~raw_fits.valid).sum()),
        "failed_primary_refits": int((~fits.valid).sum()),
        "first_decision": str(states.index[0].date()),
        "last_decision": str(states.index[-1].date()),
        "first_scored_outcome": str(scores.target_start.min().date()),
        "last_scored_outcome": str(scores.target_end.max().date()),
        "sessions_scored": int(scores.date.nunique()),
    }
    (RESULTS / "diagnostics.json").write_text(json.dumps(diag, indent=2) + "\n")
    last = states.iloc[-1]
    date = states.index[-1]
    current = {
        "as_of": str(date.date()),
        "p_stressed": float(last.p_high),
        "state": ["Quiet", "Active", "Stressed"][int(last.label)],
        "state_probabilities": {
            n: float(last[f"p{i}"]) for i, n in enumerate(["Quiet", "Active", "Stressed"])
        },
        "normalized_entropy": float(last.entropy),
        "fast_slow_risk_ratio": float(signals.ratio.iloc[-1]),
        "equity_bond_correlation_63": float(r.SPY.iloc[-63:].corr(r.TLT.iloc[-63:])),
        "asset_return_63_sessions": {
            ASSETS[k]: float(v) for k, v in ((1 + r.iloc[-63:]).prod() - 1).items()
        },
        "last_alarms": {
            m: str(signals.index[signals[m]][-1].date()) if signals[m].any() else None
            for m in ["Observable reset", "HMM reset"]
        },
        "proposed_action": "Review short-window risk estimates and current cross-asset relationships; no automatic alpha-model change.",
        "sample_status": "Historical replay, revised adjusted-close data; not a streaming service.",
    }
    (RESULTS / "latest_monitor.json").write_text(json.dumps(current, indent=2) + "\n")
    from research.practical_plots import make_figures

    make_figures(
        prices,
        r,
        states,
        revisions,
        retro,
        scores,
        signals,
        summary,
        asset_ci,
        burden,
        events,
        reference,
    )
    from research.practical_report import write_report

    write_report()
    write_metadata()
    print(
        summary.query('endpoint=="Eight-asset mean" and block==63').to_string(index=False),
        flush=True,
    )
    print("Completed practical regime study:", diag, flush=True)


if __name__ == "__main__":
    main()

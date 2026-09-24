"""Public deliverables and independent reconciliation of the practical experiment."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nbformat
import numpy as np
import pandas as pd
from research.common import sha
from research.practical_config import ROOT, RESULTS, PATHS, SETTINGS, ASSETS
from research.practical_data import load_data
from research.run_study import provenance


def public_checks():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, text=True).split("\0")
    forbidden = (
        "research/data/raw/",
        "research/private-legacy/",
        "research/results/paths/",
        ".venv/",
        ".cache/",
        ".codex/",
        ".agents/",
    )
    for name in tracked:
        if name and (
            name.startswith(forbidden)
            or Path(name).name
            in [".env", "AGENTS.md", "CODEX.md", "RENOVATION_AGENT_INSTRUCTIONS.md"]
        ):
            raise ValueError("Blocked tracked path: " + name)
    required = [
        "README.md",
        "study.ipynb",
        "pyproject.toml",
        "uv.lock",
        "research/PROTOCOL.md",
        "research/data/practical_manifest.json",
        "docs/01-methods.md",
        "docs/02-results.md",
        "docs/03-historical-replays.md",
        "docs/04-calibration-playbook.md",
        "docs/05-reproduction.md",
    ]
    for name in required:
        assert (ROOT / name).is_file(), name
    for p in [
        ROOT / "README.md",
        ROOT / "PUBLICATION.md",
        *list((ROOT / "docs").glob("*.md")),
        *list((ROOT / "research").glob("*.md")),
    ]:
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if re.match(r"https?://|mailto:|#", link):
                continue
            target = link.split("#")[0]
            if target and not (p.parent / target).exists():
                raise ValueError(f"Broken link in {p}: {link}")
    nb = nbformat.read(ROOT / "study.ipynb", as_version=4)
    nbformat.validate(nb)
    cells = [c for c in nb.cells if c.cell_type == "code"]
    assert cells and all(c.execution_count is not None for c in cells)
    assert not any(o.output_type == "error" for c in cells for o in c.outputs)
    count = sum("image/png" in o.get("data", {}) for c in cells for o in c.outputs)
    assert count >= 8, count
    print(
        f"Public checks passed: {len(cells)} executed cells, {count} embedded figures, links and publication paths."
    )


def independent_checks():
    metadata = json.loads((RESULTS / "run_metadata.json").read_text())
    assert metadata["source_and_code"] == provenance(), "Changed code/settings/input: rerun study"
    for path, digest in {**metadata["outputs"], **metadata["private_outputs"]}.items():
        assert sha(ROOT / path) == digest, path
    _, r = load_data()
    scores = pd.read_csv(PATHS / "scores.csv", parse_dates=["date", "target_start", "target_end"])
    dates = r.index
    h = SETTINGS["horizon"]
    warm = SETTINGS["lookback"] + SETTINGS["feature_warmup"]
    # Reconstruct all target values independently using shifted pandas windows.
    target = r.pow(2).rolling(h).mean().shift(-h)
    weights = pd.Series({a: 0.25 if a in ["SPY", "TLT", "GLD", "DBC"] else 0 for a in ASSETS})
    target["BASKET"] = r.mul(weights).sum(axis=1).pow(2).rolling(h).mean().shift(-h)
    for asset, g in scores.groupby("asset"):
        np.testing.assert_allclose(g.target, target[asset].reindex(g.date), rtol=1e-10, atol=1e-14)
    positions = dates.get_indexer(scores.date)
    assert np.array_equal(scores.target_start.to_numpy(), dates[positions + 1].to_numpy())
    assert np.array_equal(scores.target_end.to_numpy(), dates[positions + h].to_numpy())
    np.testing.assert_allclose(
        scores.loss,
        np.log(scores.forecast) + scores.target / scores.forecast,
        rtol=1e-9,
        atol=1e-10,
    )
    matrices = np.load(PATHS / "forecast_matrices.npz")
    for method in matrices.files:
        m = matrices[method]
        valid = m[warm - 1 :]
        np.testing.assert_allclose(valid, np.swapaxes(valid, 1, 2), atol=1e-14)
        assert np.linalg.eigvalsh(valid).min() > 0
        for j, asset in enumerate(ASSETS):
            g = scores[(scores.method == method) & (scores.asset == asset)]
            np.testing.assert_allclose(g.forecast, m[dates.get_indexer(g.date), j, j], atol=1e-14)
        g = scores[(scores.method == method) & (scores.asset == "BASKET")]
        w = weights.to_numpy()
        calculated = np.einsum("i,tij,j->t", w, m[dates.get_indexer(g.date)], w)
        np.testing.assert_allclose(g.forecast, calculated, atol=1e-14)
    signal = pd.read_csv(PATHS / "signals.csv", index_col="date", parse_dates=True)
    for method in ["HMM reset", "Observable reset"]:
        alarms = np.flatnonzero(signal[method].to_numpy())
        assert (np.diff(alarms) >= SETTINGS["cooldown"]).all()
        for t in alarms:
            raw = r.iloc[t - 19 : t + 1].to_numpy()
            raw = raw.T @ raw / 20
            expected = 0.9 * raw + 0.1 * np.diag(np.diag(raw))
            np.testing.assert_allclose(matrices[method][t], expected, atol=1e-14)
    states = pd.read_csv(PATHS / "primary_states.csv", index_col="date", parse_dates=True)
    np.testing.assert_allclose(states[["p0", "p1", "p2"]].sum(axis=1), 1, atol=1e-12)
    delayed = pd.read_csv(
        PATHS / "primary_revisions.csv", parse_dates=["state_date", "available_date"]
    )
    assert np.array_equal(
        dates.get_indexer(delayed.available_date) - dates.get_indexer(delayed.state_date),
        delayed.lag.to_numpy(),
    )
    daily = scores[scores.asset != "BASKET"].groupby(["date", "method"]).loss.mean().unstack()
    summary = pd.read_csv(RESULTS / "calibration_comparison.csv")
    for row in summary.query('endpoint=="Eight-asset mean"').itertuples():
        assert abs((daily[row.contrast] - daily["Slow EWMA"]).mean() - row.estimate) < 1e-10
    assert len(daily) == len(r) - warm + 1 - h
    burden = pd.read_csv(RESULTS / "review_burden.csv").set_index("method")
    for method in burden.index:
        assert int(signal[method].sum()) == int(burden.loc[method, "alarms"])
    print("Independent target, timing, risk-matrix, reset, headline and provenance checks passed.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--public", action="store_true")
    args = p.parse_args()
    public_checks()
    if not args.public:
        independent_checks()

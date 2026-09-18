"""Public-file checks and independent numerical reconciliation."""

import argparse
import json
import re
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import nbformat
from research.common import ROOT, RESULTS, check_hashes, load_returns


def public_checks():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    forbidden = (
        "research/data/raw/",
        "research/private-legacy/",
        "research/results/paths/",
        ".venv/",
        ".cache/",
    )
    for name in tracked:
        if (
            name
            and (ROOT / name).exists()
            and (name.startswith(forbidden) or Path(name).name == ".env")
        ):
            raise ValueError("Blocked publication path is tracked: " + name)
    required = [
        "README.md",
        "PUBLICATION.md",
        "NOTICE",
        "study.ipynb",
        "pyproject.toml",
        "uv.lock",
        "research/AUDIT.md",
        "research/PROTOCOL.md",
        "research/SOURCES.md",
        "research/data/input_manifest.json",
        "research/RESEARCH_AGENDA.md",
        "research/WORKLOG.md",
        "docs/01-methods.md",
        "docs/02-results.md",
    ]
    for name in required:
        if not (ROOT / name).is_file():
            raise ValueError("Missing deliverable: " + name)
    markdown = [
        ROOT / "README.md",
        ROOT / "PUBLICATION.md",
        *list((ROOT / "docs").glob("*.md")),
        *list((ROOT / "research").glob("*.md")),
    ]
    for p in markdown:
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if re.match(r"https?://|mailto:|#", link):
                continue
            target = link.split("#")[0]
            if target and not (p.parent / target).exists():
                raise ValueError(f"Broken link in {p.name}: {link}")
    nb = nbformat.read(ROOT / "study.ipynb", as_version=4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == "code"]
    if not code or any(c.execution_count is None for c in code):
        raise ValueError("Notebook is unexecuted")
    if any(o.output_type == "error" for c in code for o in c.get("outputs", [])):
        raise ValueError("Notebook has errors")
    if not any("image/png" in o.get("data", {}) for c in code for o in c.get("outputs", [])):
        raise ValueError("No notebook figures")
    print(
        f"Public checks: {len(code)} executed cells, links/figures valid; no raw-history download"
    )


def independent_checks():
    check_hashes()
    project = "regime_model"
    if project == "project_FICC_Quant":
        flows = pd.read_csv(RESULTS / "cashflows.csv")
        v = pd.read_csv(RESULTS / "valuation.csv").set_index("instrument")
        assert abs(flows.query('instrument=="bond"').pv.sum() - v.loc["bond", "quantlib_pv"]) < 1e-8
        assert (
            abs(flows.query('instrument!="bond"').pv.sum() - v.loc["payer_swap", "quantlib_pv"])
            < 1e-8
        )
        assert (
            abs(v.loc["bond", "clean"] + v.loc["bond", "accrued"] - v.loc["bond", "dirty"]) < 1e-10
        )
        assert pd.read_csv(RESULTS / "calibration.csv").residual.abs().max() < 1e-8
        fx = pd.read_csv(RESULTS / "fx_parity.csv").iloc[0]
        assert abs(fx.spot * fx.eur_discount - fx.fair_forward * fx.usd_discount) < 1e-12
        bump = pd.read_csv(RESULTS / "bump_convergence.csv").pivot(
            index="instrument", columns="bump_bps", values="signed_dv01"
        )
        assert (bump[0.1] - bump[5.0]).abs().max() < 1e-4
        h = pd.read_csv(RESULTS / "hedge.csv").iloc[0]
        pnl = pd.read_csv(RESULTS / "scenario_pnl.csv")
        np.testing.assert_allclose(
            pnl.hedged_pnl, pnl.unhedged_bond_pnl + h.swap_units * pnl.swap_pnl_per100, atol=1e-12
        )
        risk = pd.read_csv(RESULTS / "independent_risk.csv").iloc[0]
        assert abs(risk.zero_spread_analytic_dv01 - risk.zero_spread_central_dv01) < 1e-7
    elif project == "project_Asset_Allocation":
        r = load_returns()
        d = pd.read_csv(RESULTS / "paths/daily.csv", parse_dates=["date"])
        w = pd.read_csv(RESULTS / "paths/weights.csv", parse_dates=["date"])
        trades = pd.read_csv(
            RESULTS / "paths/trades.csv", parse_dates=["execution_date", "information_date"]
        )
        for strategy, g in w.groupby("strategy"):
            g = g.set_index("date")
            saved = d.query("strategy==@strategy").set_index("date")
            calculated = (g[list(r.columns)] * r.reindex(g.index)).sum(axis=1)
            np.testing.assert_allclose(saved.gross, calculated, atol=1e-12)
            np.testing.assert_allclose(
                saved.net, (1 + calculated) * (1 - saved.cost) - 1, atol=1e-12
            )
        assert (trades.information_date < trades.execution_date).all()
        for row in trades.itertuples():
            target = np.array([getattr(row, "target_" + t) for t in r.columns])
            signed = np.array([getattr(row, "trade_" + t) for t in r.columns])
            assert abs(np.abs(signed).sum() - row.turnover) < 1e-12
            assert abs(row.cost - 5e-4 * row.turnover) < 1e-12
            assert abs(target.sum() + row.cash - 1) < 1e-10
        late = d.query('date>="2025-01-01"').pivot(index="date", columns="strategy", values="net")
        a, b = late.HRP, late["EQ risk HRP"]
        estimate = np.sqrt(252) * (a.mean() / a.std(ddof=1) - b.mean() / b.std(ddof=1))
        assert (
            abs(estimate - json.loads((RESULTS / "headline.json").read_text())["estimate"]) < 1e-10
        )
    else:
        r = load_returns()
        f = pd.read_csv(
            RESULTS / "paths/forecasts_primary.csv", parse_dates=["information_date", "target_date"]
        )
        assert (f.information_date < f.target_date).all()
        np.testing.assert_allclose(
            f.target_squared, r.SPY.reindex(f.target_date).to_numpy() ** 2, atol=1e-14
        )
        np.testing.assert_allclose(
            f.loss, np.log(f.forecast) + f.target_squared / f.forecast, atol=1e-10
        )
        hm = f.query('model=="HMM"')
        np.testing.assert_allclose(hm[["p_state0", "p_state1"]].sum(axis=1), 1, atol=1e-12)
        loss = f.query('target_date>="2025-01-01"').pivot(
            index="target_date", columns="model", values="loss"
        )
        estimate = (loss.HMM - loss.EWMA).mean()
        assert (
            abs(estimate - json.loads((RESULTS / "headline.json").read_text())["estimate"]) < 1e-10
        )
        o = pd.read_csv(RESULTS / "paths/overlay.csv", parse_dates=["date", "information_date"])
        np.testing.assert_allclose(
            o.gross, o.earning_weight * r.SPY.reindex(o.date).to_numpy(), atol=1e-12
        )
        np.testing.assert_allclose(o.net, (1 + o.gross) * (1 - o.cost) - 1, atol=1e-12)
        np.testing.assert_allclose(o.cost, o.turnover * 5e-4, atol=1e-12)
        assert (o.information_date < o.date).all()
    print("Independent saved-output calculations and source/code hashes: passed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--public", action="store_true")
    args = p.parse_args()
    public_checks()
    if not args.public:
        independent_checks()


if __name__ == "__main__":
    main()

"""Execute and save the research narrative with portable figures and editable calculations."""

import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
for key, folder in [
    ("MPLCONFIGDIR", "matplotlib"),
    ("IPYTHONDIR", "ipython"),
    ("JUPYTER_CONFIG_DIR", "jupyter"),
    ("JUPYTER_DATA_DIR", "jupyter_data"),
    ("JUPYTER_RUNTIME_DIR", "jupyter_runtime"),
]:
    (ROOT / ".cache" / folder).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(key, str(ROOT / ".cache" / folder))


def main():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook()
    nb.metadata.kernelspec = {"name": "python3", "display_name": "Python 3", "language": "python"}
    cells = [
        md(
            "# Market regimes for faster research decisions\n\n## Summary\n\nRecognize a market change, decide what needs recalibration, and inspect what happens next. This notebook combines immediate alerts, deliberately delayed confirmation, and full-history interpretation across eight asset classes. The numerical summary below is generated from the executed results."
        ),
        md(
            "## Context and methods\n\nThe maintained HMM reads four smoothed asset-group risk levels and a stock–bond dependence feature. The raw-return HMM is retained as a benchmark. This feature amendment follows the first replay and remains exploratory. The practical action is a risk-model review: an alert resets the second-moment estimate to the latest 20 observations and uses faster updating for a month. We compare it with continuous slow and fast EWMA. A separate HMM state forecast answers a different question.\n\n### Key assumptions\n\nAll observations are revised adjusted-close proxies. The study is retrospective. A forecast at close t is scored on t+1 through t+5; a delayed label records both the date it describes and the date it becomes available. Full-history labels never enter decisions. The loss measures risk calibration, not strategy returns.\n\n[Methods](docs/01-methods.md) · [Frozen protocol](research/PROTOCOL.md) · [Plotting calculations](research/practical_plots.py)."
        ),
        code(
            "from pathlib import Path\nimport json\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display, Markdown, Image\nfrom research.run_study import main\nfrom research.practical_config import ROOT, RESULTS, FIGURES, ASSETS\nfrom research.practical_data import load_data\nmain()\nprices, returns = load_data()"
        ),
        code(
            'comparison = pd.read_csv(RESULTS / "calibration_comparison.csv")\nprimary = comparison.query(\'endpoint == "Eight-asset mean" and block == 63\')\ndisplay(primary[["contrast", "estimate", "lower95", "upper95", "n"]].round(4))'
        ),
        md(
            "Negative loss differences favor the alternative. Read each estimate with its interval. The HMM-triggered reset and the direct state forecast answer different questions. The raw-return reset provides a matched-period representation control; a smoother state map is not automatically a better risk model."
        ),
        md(
            "## Data\n\nEight surviving fund proxies, March 2006–21 September 2026. Names describe economic exposures; currency, duration, credit and commodity-roll effects remain inside their returns. The common cutoff avoids a missing provider session rather than filling a price."
        ),
        code(
            'manifest = json.loads((ROOT / "research/data/practical_manifest.json").read_text())\ndisplay(pd.DataFrame(manifest["snapshots"])[["name", "ticker", "first_date", "last_date", "rows"]])\ndisplay(pd.Series(json.loads((RESULTS / "data_audit.json").read_text()))[["price_rows", "assets", "missing", "duplicates", "fills"]])'
        ),
        md("## Results\n\n### 1. Start with the economic picture"),
        code('display(Image(filename=str(FIGURES / "market_atlas.png")))'),
        md(
            "The same broad risk state leaves assets with different return paths. The atlas uses a common log scale, with each exposure indexed to 100. Orange marks archived high-stress probability, not a strategy position."
        ),
        code('display(Image(filename=str(FIGURES / "market_context.png")))'),
        md(
            "Quarterly direction and equity–bond dependence supply context that a volatility label alone cannot. The covariance or hedge assumption can need review even when the current marginal-risk state is familiar."
        ),
        md("### 2. Choose a representation that matches the research question"),
        code(
            'display(Image(filename=str(FIGURES / "representation_comparison.png")))\ndisplay(pd.read_csv(RESULTS / "representation_comparison.csv").round(4))'
        ),
        md(
            "The daily-return model's frequent switching motivated a feature-based description. EWMA risk inputs deliberately add persistence and some delay; the full posterior is model-implied rather than a calibrated probability of an objectively true economic regime. The label-stability comparison is descriptive; the following risk backtest tests the action taken from it."
        ),
        md("### 3. Replay what the researcher could see"),
        code('display(Image(filename=str(FIGURES / "episode_replays.png")))'),
        md(
            "Each triangle is a confirmed review date. The price panels show why a clean retrospective break is different from a timely operational response. Windows were chosen as historical illustrations before evaluation; they are not an independent test set."
        ),
        code(
            'events = pd.read_csv(RESULTS / "episode_timing.csv")\ndisplay(events.query(\'method == "HMM reset"\').rename(columns={"lag_sessions": "Lag vs observable reference (sessions)"}))'
        ),
        md("### 4. Make the recalibration rule explicit"),
        code(
            '# Independent illustration at the first HMM review: a 20-session reset.\nsignals = pd.read_csv(ROOT / "research/results/paths/practical/signals.csv", index_col="date", parse_dates=True)\nreview_date = signals.index[signals["HMM reset"]][0]\nrecent = returns.loc[:review_date].tail(20).to_numpy()\nsecond_moment = recent.T @ recent / len(recent)\nforecast_matrix = 0.9 * second_moment + 0.1 * np.diag(np.diag(second_moment))\ndisplay(Markdown(f"First HMM review: **{review_date.date()}**"))\ndisplay(pd.Series(np.sqrt(252 * np.diag(forecast_matrix)), index=ASSETS.values(), name="Reset annualized risk").map(lambda x: f"{x:.1%}"))'
        ),
        code('display(Image(filename=str(FIGURES / "calibration_replay.png")))'),
        md(
            "The realized next-five-session proxy is plotted at its forecast date, but becomes available later. The four-asset basket is a fixed research exposure; the chart is not a net trading backtest."
        ),
        code('display(Image(filename=str(FIGURES / "calibration_comparison.png")))'),
        code(
            'display(pd.read_csv(RESULTS / "subperiods.csv").query(\'method != "HMM state forecast"\').pivot(index="period", columns="method", values="mean_loss_difference").round(4))\ndisplay(pd.read_csv(RESULTS / "sensitivity.csv")[["variant", "estimate", "lower95", "upper95", "alarms"]].round(4))'
        ),
        md(
            "Subperiod, state-count and threshold results show how dependent the decision is on the chosen model. All alternatives remain visible; none silently replaces the declared rule."
        ),
        md("### 5. Count the reviews and missed changes"),
        code(
            'display(Image(filename=str(FIGURES / "alert_timing.png")))\ndisplay(pd.read_csv(RESULTS / "review_burden.csv").round(3))'
        ),
        code('display(pd.read_csv(RESULTS / "synthetic_summary.csv").round(3))'),
        md(
            "The conservative observable threshold produces one historical alert and misses the stipulated synthetic volatility changes. Zero null alarms alone is therefore uninformative. The already declared looser/tighter threshold checks expose this tradeoff. Synthetic detection probabilities are not historical true-break accuracy."
        ),
        md("### 6. Use delayed labels deliberately"),
        code(
            'display(Image(filename=str(FIGURES / "revision_tradeoff.png")))\ndisplay(pd.read_csv(RESULTS / "label_revisions.csv").round(3))'
        ),
        md(
            "The table quantifies how many labels change after five sessions, twenty sessions and full-history re-estimation. Revisions include parameter refits. Agreement with the final description is not accuracy against ground truth, and a concentrated posterior need not be well calibrated."
        ),
        code('display(Image(filename=str(FIGURES / "state_fingerprints.png")))'),
        md(
            "These conditional historical volatilities help characterize episodes. They are estimated after labeling the complete history and cannot establish future conditional returns."
        ),
        md("### 7. A dated research snapshot"),
        code(
            'snapshot = json.loads((RESULTS / "latest_monitor.json").read_text())\ndisplay(Markdown(f"As of **{snapshot[\'as_of\']}**: **{snapshot[\'state\']}** state. Equity–bond 63-session correlation: **{snapshot[\'equity_bond_correlation_63\']:+.2f}**."))\ndisplay(pd.Series(snapshot["state_probabilities"], name="Model-implied probability"))\ndisplay(pd.Series(snapshot["asset_return_63_sessions"], name="63-session adjusted return").map(lambda x: f"{x:+.1%}"))'
        ),
        md(
            "## Takeaways\n\nUse immediate recognition to schedule a review, a delayed map to refine an event study, and full-history states to organize scenarios. Tie the review to a specific parameter change and compare its subsequent performance with a simpler continuous update. Judge the reset on subsequent calibration and review burden, and the descriptive model on its usefulness for investigating market structure. The almost silent volatility gate illustrates why low alert frequency alone is not successful detection.\n\n[Researcher’s playbook](docs/04-calibration-playbook.md) explains the workflow. [Next experiments](research/RESEARCH_AGENDA.md) distinguish completed work from unrun correlation detectors, state-weighted calibration and alpha-model adaptations."
        ),
        md(
            "## Calculation appendix\n\nReconstruct every scored target from the price-derived returns, reconcile matrices and reset dates, and verify source/code/output hashes."
        ),
        code("from research.check_artifacts import independent_checks\nindependent_checks()"),
        md(
            "[Sources](research/SOURCES.md) · [Full evidence](docs/02-results.md) · [Reproduction](docs/05-reproduction.md) · [Publication boundary](PUBLICATION.md)."
        ),
    ]
    nb.cells = cells
    NotebookClient(
        nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}
    ).execute()
    nbformat.validate(nb)
    temp = ROOT / "study.ipynb.partial"
    nbformat.write(nb, temp)
    temp.replace(ROOT / "study.ipynb")
    html, _ = HTMLExporter().from_notebook_node(nb)
    dest = ROOT / "research/preview"
    dest.mkdir(exist_ok=True)
    (dest / "study.html").write_text(html)
    print("Saved executed notebook and HTML preview.")


if __name__ == "__main__":
    main()

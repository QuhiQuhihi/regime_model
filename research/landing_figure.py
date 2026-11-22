"""Draw the README history from the published monthly filtered probabilities."""

import json

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

from research.practical_config import RESULTS, ROOT


def write_stress_history():
    history = pd.read_csv(RESULTS / "monthly_monitor.csv", parse_dates=["date"]).set_index("date")
    diagnostics = json.loads((RESULTS / "diagnostics.json").read_text())
    first = pd.Timestamp(diagnostics["first_decision"])
    last = pd.Timestamp(diagnostics["last_decision"])
    probability = history["p_high"].copy()
    # The CSV labels a partial final month with its calendar month end.
    probability.index = probability.index.where(probability.index <= last, last)

    paper, ink, teal = "#f7f8f4", "#172f35", "#006b70"
    fig = Figure(figsize=(11.0, 3.8), facecolor=paper)
    fig.text(
        0.055, 0.84, "When did the model register stress?", fontsize=24, weight="bold", color=ink
    )
    fig.text(
        0.055,
        0.75,
        f"Mean end-of-day stressed-state probability by month  ·  {first:%b %Y} – {last:%d %b %Y}",
        fontsize=12,
        color="#425c60",
    )
    ax = fig.add_axes([0.076, 0.14, 0.89, 0.56], facecolor=paper)
    ax.set_axisbelow(True)
    ax.grid(False)
    ax.yaxis.grid(True, color="#cad5d1", linewidth=0.7)
    ax.fill_between(probability.index, 0, probability, color="#bcdcd6")
    ax.plot(probability, color=teal, linewidth=1.65)
    for month, label, shift, alignment in [
        ("2008-10", "Financial crisis", 7, "left"),
        ("2020-03", "Pandemic onset", -6, "right"),
        ("2022-10", "Stock–bond selloff", 7, "left"),
    ]:
        point = probability[probability.index.to_period("M") == pd.Period(month)]
        if point.empty:
            continue
        date, value = point.index[0], point.iloc[0]
        ax.scatter(date, value, color=teal, edgecolor=paper, s=34, zorder=3)
        ax.annotate(
            label,
            (date, value),
            xytext=(shift, 9),
            textcoords="offset points",
            ha=alignment,
            fontsize=10,
            weight="bold",
            color=ink,
        )
    ax.set(xlim=(first, last), ylim=(-0.01, 1.22), yticks=[0, 0.5, 1])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="both", length=0, pad=6, labelsize=10, colors="#425c60")
    ax.spines[:].set_visible(False)
    path = ROOT / "docs/figures/stress-history.png"
    path.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(path, dpi=160, facecolor=paper)


if __name__ == "__main__":
    write_stress_history()

"""Render the README figures from portfolio summaries and filtered HMM states."""

import json
import math

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import NullLocator, PercentFormatter, StrMethodFormatter

from research.landing_backtest import load_archived_states
from research.practical_config import RESULTS, ROOT


def write_spy_wealth(daily_labels):
    folder = ROOT / "docs/figures"
    wealth = pd.read_csv(folder / "spy-wealth.csv", index_col="date", parse_dates=["date"])
    performance = pd.read_csv(folder / "spy-performance.csv", index_col="strategy")
    first, last = wealth.index[[0, -1]]
    if (
        daily_labels.empty
        or daily_labels.index.has_duplicates
        or not daily_labels.index.is_monotonic_increasing
        or (daily_labels.index[0], daily_labels.index[-1]) != (first, last)
        or not daily_labels.isin([0, 1, 2]).all()
    ):
        raise ValueError("Expected ordered, filtered HMM labels covering the wealth chart")
    regimes = [("Quiet", "#e0eff5"), ("Active", "#fae7ae"), ("Stressed", "#debcd0")]
    styles = [
        ("regime", "HMM allocation", "#006b70", "-"),
        ("spy", "Buy and hold SPY", "#a24716", "--"),
        ("static", "Fixed 62.5% SPY", "#66607e", ":"),
    ]
    paper, ink, muted = "#f7f8f4", "#172f35", "#425c60"
    fig = Figure(figsize=(10.8, 5.9), facecolor=paper)
    fig.text(
        0.055, 0.90, "A regime-based allocation to the S&P 500", size=23, weight="bold", color=ink
    )
    fig.text(
        0.055,
        0.835,
        f"Growth of $100 after simulated trading costs  ·  {first:%b %Y} – {last:%d %b %Y}",
        fontsize=12,
        color=muted,
    )
    ax = fig.add_axes([0.085, 0.24, 0.86, 0.48], facecolor=paper)
    changes = daily_labels[daily_labels.ne(daily_labels.shift())]
    ends = [*changes.index[1:], last]
    for (start, label), end in zip(changes.items(), ends, strict=True):
        ax.axvspan(start, end, color=regimes[int(label)][1], linewidth=0, zorder=0)
    ax.text(0, 1.025, "Daily HMM regime", transform=ax.transAxes, color=ink, size=11, va="bottom")
    ax.legend(
        handles=[Patch(facecolor=color, label=name) for name, color in regimes],
        loc="lower left",
        bbox_to_anchor=(0.16, 1.01),
        borderaxespad=0,
        frameon=False,
        ncols=3,
        handlelength=1.3,
        columnspacing=1.4,
        fontsize=11,
    )
    ax.set_yscale("log")
    low, high = wealth.min().min() * 0.90, wealth.max().max() * 1.10
    ticks = range(math.ceil(math.log2(low / 100)), math.floor(math.log2(high / 100)) + 1)
    ax.set_yticks([100 * 2.0**power for power in ticks])
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(low, high)
    ax.set_xlim(first, last)
    years = pd.date_range(first, last, freq="YS")
    ax.set_xticks([first, *years[(years.year > first.year) & (years.year % 2 == 0)]])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0, labelsize=10, pad=6, colors=muted)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color="white", linewidth=0.8)
    for i, (key, label, color, linestyle) in enumerate(styles):
        values = wealth[key]
        ax.plot(values, color=color, linestyle=linestyle, lw=2.1 if key == "regime" else 1.8)
        ax.plot(last, values.iloc[-1], marker="o", color=color, markersize=4.5, clip_on=False)
        x = 0.055 + i * 0.303
        fig.add_artist(
            Line2D(
                [x, x + 0.027],
                [0.127, 0.127],
                transform=fig.transFigure,
                color=color,
                linestyle=linestyle,
                lw=2.2,
            )
        )
        fig.text(x + 0.036, 0.127, label, va="center", weight="bold", fontsize=12, color=ink)
        row = performance.loc[key]
        fig.text(
            x,
            0.062,
            f"${row.terminal_wealth:,.0f} final  ·  {row.max_drawdown:.1%} max drawdown",
            fontsize=10.5,
            color=muted,
        )
    ax.text(
        1,
        1.025,
        "Month-end wealth  ·  log scale",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color=muted,
        size=9,
    )
    fig.savefig(folder / "spy-backtest.png", dpi=160, facecolor=paper)


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
    write_spy_wealth(load_archived_states()["label"])
    write_stress_history()

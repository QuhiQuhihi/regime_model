"""Portable research figures: asset names, historical replays and decision comparisons."""

import numpy as np
import pandas as pd
from matplotlib import dates as mdates
from matplotlib.colors import TwoSlopeNorm
from research.common import plot_style
from research.practical_config import ASSETS, FIGURES, EPISODES, RESULTS, PATHS

COLORS = {
    "Slow EWMA": "#555b64",
    "Fast EWMA": "#22577a",
    "Observable reset": "#758e4f",
    "HMM reset": "#bc6c25",
    "HMM state forecast": "#a66b88",
    "Raw-return HMM reset": "#6c91a5",
}
ASSET_COLORS = {"SPY": "#22577a", "TLT": "#bc6c25", "GLD": "#b99a32", "DBC": "#758e4f"}
STYLES = {"SPY": "-", "TLT": "--", "GLD": "-.", "DBC": ":"}


def finish(plt, fig, name, title, note):
    fig.suptitle(title, fontsize=17, fontweight="bold", x=0.06, ha="left")
    fig.text(0.06, 0.012, note, fontsize=9, color="#53575d", va="bottom")
    fig.tight_layout(rect=(0.025, 0.055, 0.995, 0.955), h_pad=2, w_pad=2)
    fig.savefig(FIGURES / f"{name}.png", dpi=160, facecolor="white")
    plt.close(fig)


def dates(ax, start, end):
    ticks = (
        [pd.Timestamp(start)]
        + [
            pd.Timestamp(f"{y}-01-01")
            for y in [2010, 2015, 2020]
            if pd.Timestamp(start) < pd.Timestamp(f"{y}-01-01") < pd.Timestamp(end)
        ]
        + [pd.Timestamp(end)]
    )
    ax.set_xlim(pd.Timestamp(start), pd.Timestamp(end))
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def make_figures(
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
):
    representation_figure(states)
    plt = plot_style()
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titleweight": "bold"})
    start, end = prices.index[0], prices.index[-1]
    indexed = prices / prices.iloc[0] * 100
    lo, hi = indexed.min().min() * 0.9, indexed.max().max() * 1.12
    fig, axes = plt.subplots(4, 2, figsize=(14, 12), sharey=True)
    stress = states.p_high.reindex(prices.index).gt(0.7)
    for ax, (ticker, name) in zip(axes.ravel(), ASSETS.items()):
        ax.fill_between(
            prices.index, lo, hi, where=stress, color="#bc6c25", alpha=0.17, linewidth=0
        )
        ax.plot(indexed.index, indexed[ticker], color="#22577a", lw=1.4)
        ax.set(title=name, yscale="log", ylim=(lo, hi), ylabel="Indexed adjusted price")
        ax.axhline(100, color="#555b64", lw=0.6, ls=":")
        dates(ax, start, end)
    finish(
        plt,
        fig,
        "market_atlas",
        "One regime label, eight different market histories",
        f"{start:%d %b %Y}–{end:%d %b %Y} | Start = 100; common log scale | Orange: archived HMM stress probability > 70%.\nShading begins after the 567-return feature/training warmup. Adjusted prices are historical proxies; labels describe broad risk, not return direction.",
    )

    fig, axes = plt.subplots(4, 2, figsize=(15, 13))
    for (label, (a, b)), (ax, bx) in zip(EPISODES.items(), axes):
        data = prices.loc[a:b]
        wealth = (data / data.iloc[0] - 1) * 100
        for ticker in ASSET_COLORS:
            ax.plot(
                data.index,
                wealth[ticker],
                label=ASSETS[ticker],
                color=ASSET_COLORS[ticker],
                ls=STYLES[ticker],
                lw=1.7,
            )
        ax.axhline(0, color="#777", lw=0.7)
        ax.set(title=label + " | asset paths", ylabel="Change from window start (%)")
        signal = signals.loc[a:b]
        bx.plot(
            signal.index,
            signal.p_high / 0.7,
            color=COLORS["HMM reset"],
            label="HMM probability / 0.70",
            lw=1.3,
        )
        bx.plot(
            signal.index,
            signal.ratio / 1.5,
            color=COLORS["Observable reset"],
            label="Risk ratio / 1.50",
            lw=1.5,
        )
        bx.axhline(1, color="#555b64", ls="--", lw=1, label="Alert threshold")
        for method, marker, y in [("HMM reset", "v", 1.48), ("Observable reset", "^", 1.58)]:
            ix = signal.index[signal[method]]
            bx.scatter(
                ix, np.repeat(y, len(ix)), color=COLORS[method], marker=marker, s=42, zorder=5
            )
        bx.set(
            title=label + " | recognition and review dates",
            ylim=(0, 1.68),
            ylabel="Signal / threshold",
        )
        for axis in [ax, bx]:
            axis.set_xlim(data.index[0], data.index[-1])
            axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
            axis.tick_params(axis="x", labelsize=9)
    axes[0, 0].legend(fontsize=9, ncol=2, loc="lower left")
    axes[0, 1].legend(fontsize=9, loc="lower left")
    finish(
        plt,
        fig,
        "episode_replays",
        "Historical replay: what changed, and when did the alert arrive?",
        "Preselected windows; each price panel starts at zero. Triangles mark confirmed alerts, not estimated historical break dates.\nTwo observations confirm a threshold crossing; 21-session minimum spacing. The two lines share threshold units, not probability units.",
    )

    fig, axes = plt.subplots(2, 1, figsize=(13, 8))
    context = prices[["SPY", "TLT"]].pct_change(63) * 100
    for ticker in ["SPY", "TLT"]:
        axes[0].plot(
            context.index,
            context[ticker],
            label=ASSETS[ticker],
            color=ASSET_COLORS[ticker],
            ls=STYLES[ticker],
            lw=1,
        )
    both = (context.SPY < 0) & (context.TLT < 0)
    axes[0].fill_between(
        context.index, -65, 65, where=both, color="#bc6c25", alpha=0.13, linewidth=0
    )
    axes[0].axhline(0, color="#777", lw=0.7)
    axes[0].set(
        ylabel="Trailing 63-session return (%)",
        ylim=(-65, 65),
        title="Direction: are stocks and bonds falling together?",
    )
    axes[0].legend(ncol=2)
    corr = r.SPY.rolling(63).corr(r.TLT)
    axes[1].plot(corr.index, corr, color="#22577a", lw=1.2)
    axes[1].axhline(0, color="#777", ls="--", lw=0.8)
    axes[1].set(
        ylabel="63-session return correlation",
        ylim=(-1, 1),
        title="Relationship: does the bond exposure diversify equity moves?",
    )
    for ax in axes:
        dates(ax, start, end)
    finish(
        plt,
        fig,
        "market_context",
        "Volatility is only one part of a regime",
        "Orange spans: both 63-session adjusted returns are negative. Relationships are descriptive and time-varying.\nThese direction/correlation lenses complement the HMM; high risk does not imply a particular stock–bond relationship.",
    )

    fig, axes = plt.subplots(2, 1, figsize=(13, 8))
    a, b = "2020-01-01", "2020-06-30"
    axes[0].plot(
        states.loc[a:b].index,
        states.loc[a:b].p_high,
        label="At the original close",
        color="#22577a",
    )
    for lag, color, style in [(5, "#bc6c25", "--"), (20, "#758e4f", ":")]:
        frame = revisions[revisions.lag == lag].set_index("state_date").loc[a:b]
        axes[0].plot(
            frame.index, frame.p_high, label=f"Revised {lag} sessions later", color=color, ls=style
        )
    axes[0].plot(
        retro.loc[a:b].index,
        retro.loc[a:b].p_high,
        label="Full-history description",
        color="#555b64",
        lw=1,
        alpha=0.6,
    )
    axes[0].set(
        ylabel="Stressed-state probability",
        title="2020: labels aligned to the day they describe",
        ylim=(-0.02, 1.05),
    )
    axes[0].legend(ncol=2, fontsize=10)
    rev = pd.read_csv(RESULTS / "label_revisions.csv")
    axes[1].barh(
        ["Original close", "After 5 sessions", "After 20 sessions", "Full history"],
        rev.changed_from_original * 100,
        color=["#22577a", "#bc6c25", "#758e4f", "#555b64"],
    )
    for i, v in enumerate(rev.changed_from_original * 100):
        axes[1].text(v + 0.5, i, f"{v:.1f}%", va="center")
    axes[1].set(
        xlabel="Labels changed relative to original decision (%)",
        title="Common historical dates: revisions are useful, but have a waiting cost",
        xlim=(0, max(30, rev.changed_from_original.max() * 115)),
    )
    axes[1].invert_yaxis()
    finish(
        plt,
        fig,
        "revision_tradeoff",
        "Immediate recognition and delayed confirmation serve different jobs",
        "Revised curves are drawn at their state dates, but become available 5 or 20 sessions later. Monthly parameter refits also affect revisions.\nFull-history labels are descriptions, not ground truth. Lower entropy does not by itself establish greater accuracy.",
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1, 1.15]})
    sub = summary.query('endpoint=="Eight-asset mean" and block==63').set_index("contrast")
    methods = ["Fast EWMA", "Observable reset", "HMM reset"]
    for i, method in enumerate(methods):
        row = sub.loc[method]
        axes[0].errorbar(
            row.estimate,
            i,
            xerr=[[row.estimate - row.lower95], [row.upper95 - row.estimate]],
            fmt="o",
            color=COLORS[method],
            capsize=4,
        )
    axes[0].axvline(0, color="#555b64", ls="--")
    axes[0].set_yticks(range(3), methods)
    axes[0].invert_yaxis()
    axes[0].set(
        title="Equal weight across eight asset risk losses",
        xlabel="Loss difference vs slow EWMA\nNegative favors the alternative",
    )
    heat = asset_ci.pivot(index="asset", columns="method", values="estimate").reindex(list(ASSETS))[
        methods
    ]
    lim = max(0.01, np.nanmax(np.abs(heat.to_numpy())))
    im = axes[1].imshow(
        heat, cmap="PuOr_r", norm=TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim), aspect="auto"
    )
    axes[1].set_yticks(range(8), [ASSETS[a] for a in heat.index])
    axes[1].set_xticks(range(3), ["Fast\nEWMA", "Observable\nreset", "HMM\nreset"])
    axes[1].grid(False)
    for i in range(8):
        for j in range(3):
            v = heat.iloc[i, j]
            axes[1].text(
                j,
                i,
                f"{v:+.3f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if abs(v) > 0.65 * lim else "#222",
            )
    axes[1].set_title("The same comparison by asset exposure")
    fig.colorbar(im, ax=axes[1], shrink=0.8, label="Mean loss difference")
    finish(
        plt,
        fig,
        "calibration_comparison",
        "Does an alert improve the next five sessions’ risk calibration?",
        f"{scores.target_start.min():%d %b %Y}–{scores.target_end.max():%d %b %Y} | QLIKE-style loss; not a return percentage.\nLeft: pointwise 95% paired 63-session block intervals, 2,000 draws. Right: estimates only; per-asset intervals are saved in the results.",
    )

    fig, axes = plt.subplots(2, 1, figsize=(13, 8))
    basket = scores[scores.asset == "BASKET"]
    for ax, (label, a, b) in zip(
        axes, [("2020", "2020-01-01", "2020-06-30"), ("2022", "2022-01-01", "2022-12-31")]
    ):
        for method in ["Slow EWMA", "Fast EWMA", "HMM reset"]:
            frame = basket[basket.method == method].set_index("date").loc[a:b]
            ax.plot(
                frame.index,
                np.sqrt(252 * frame.forecast) * 100,
                label=method,
                color=COLORS[method],
                ls="--" if method == "Slow EWMA" else "-",
                lw=1.6,
            )
        ax.plot(
            frame.index,
            np.sqrt(252 * frame.target) * 100,
            label="Next-five-session realized proxy",
            color="#222",
            alpha=0.35,
            lw=1,
        )
        ax.set(
            title=label + " | equal-notional four-asset basket",
            ylabel="Annualized risk estimate (%)",
        )
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    axes[0].legend(fontsize=9, ncol=2)
    finish(
        plt,
        fig,
        "calibration_replay",
        "A regime alert becomes useful when it changes a model parameter",
        "Basket: 25% each US equities, long Treasuries, gold and commodities; fixed daily risk exposures, not an executed wealth strategy.\nForecasts use the information at each date; the realized proxy is plotted at that forecast date and becomes known five sessions later.",
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for i, row in enumerate(burden.itertuples()):
        axes[0].barh(i, row.alarms_per_year, color=COLORS[row.method])
        axes[0].text(
            row.alarms_per_year + 0.05, i, f"{row.alarms_per_year:.2f} / year", va="center"
        )
    axes[0].set_yticks(range(2), burden.method)
    axes[0].set_xlim(0, max(1, burden.alarms_per_year.max() * 1.45))
    axes[0].set(
        title="How often would the researcher review?", xlabel="Confirmed alarms per 252 sessions"
    )
    for i, method in enumerate(burden.method):
        observed = events[events.method == method].lag_sessions.dropna()
        axes[1].scatter(observed, np.full(len(observed), i), alpha=0.65, color=COLORS[method], s=32)
        row = burden.iloc[i]
        axes[1].text(
            42,
            i,
            f"{int(row.matched_episodes)}/{int(row.reference_episodes)} new reviews",
            va="center",
            fontsize=10,
        )
    axes[1].axvline(0, color="#555", ls="--")
    axes[1].set_xlim(-23, 64)
    axes[1].set_yticks(range(2), burden.method)
    axes[1].set(
        title="Timing against an observable risk escalation",
        xlabel="Sessions relative to reference (negative = earlier)",
    )
    finish(
        plt,
        fig,
        "alert_timing",
        "Compare review frequency, new alerts and ongoing stress",
        "Reference: trailing 20-session risk / preceding 126-session risk exceeds 1.5 twice; 63-session reference spacing.\nMatch window [−20, +40] sessions. It is a lagging risk proxy, not a true break date. Existing stress can precede the matching window; see the event table.",
    )

    fingerprints = pd.read_csv(RESULTS / "state_fingerprints.csv")
    heat = (
        fingerprints.pivot(index="asset", columns="state", values="annual_volatility").reindex(
            list(ASSETS)
        )
        * 100
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(heat, cmap="YlOrBr", vmin=0, aspect="auto")
    ax.grid(False)
    ax.set_yticks(range(8), [ASSETS[a] for a in heat.index])
    ax.set_xticks(range(3), ["Quiet", "Active", "Stressed"])
    for i in range(8):
        for j in range(3):
            ax.text(
                j,
                i,
                f"{heat.iloc[i, j]:.1f}%",
                ha="center",
                va="center",
                color="white" if heat.iloc[i, j] > heat.max().max() * 0.65 else "#222",
            )
    fig.colorbar(im, ax=ax, label="Annualized volatility (%)")
    finish(
        plt,
        fig,
        "state_fingerprints",
        "What does each historical state mean across asset classes?",
        f"{retro.index[0]:%d %b %Y}–{retro.index[-1]:%d %b %Y} | Full-history smoothed labels; descriptive conditional samples.\nThe same broad risk label leaves different exposures with very different volatility. This heatmap is not a forecast or tradable allocation.",
    )


def representation_figure(states):
    plt = plot_style()
    raw = pd.read_csv(PATHS / "raw_return_states.csv", index_col="date", parse_dates=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for ax, frame, title, color in [
        (axes[0], raw, "HMM on daily returns", "#6c91a5"),
        (axes[1], states, "HMM on risk levels and dependence", "#bc6c25"),
    ]:
        data = frame.loc["2020-01-01":"2020-06-30"]
        ax.plot(data.index, data.p_high, color=color, lw=1.5)
        ax.fill_between(data.index, 0, data.p_high, color=color, alpha=0.13)
        ax.set(title=title, ylabel="Stressed-state probability", ylim=(-0.02, 1.05))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    finish(
        plt,
        fig,
        "representation_comparison",
        "Choose a representation that matches the research decision",
        "2020 historical replay | Both use archived end-of-day estimates and monthly refits.\nSmoothed inputs intentionally trade some speed for persistence. This exploratory comparison retains the original raw-return result.",
    )

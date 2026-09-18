"""Shared numerical and provenance utilities, local to this repository."""

from pathlib import Path
import hashlib
import json
import sys
import platform
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research/results"
FIGURES = ROOT / "research/figures"
SEED = 20260919


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_returns(r):
    if len(r) < 2 or not isinstance(r.index, pd.DatetimeIndex):
        raise ValueError("Need dated observations")
    if r.index.has_duplicates or not r.index.is_monotonic_increasing or r.columns.has_duplicates:
        raise ValueError("Duplicate or unordered observations")
    if not np.isfinite(r.to_numpy()).all() or (r <= -1).any().any():
        raise ValueError("Missing, nonfinite, or invalid simple returns")


def load_returns():
    import exchange_calendars as xcals

    manifest = json.loads((ROOT / "research/data/input_manifest.json").read_text())
    series = []
    for m in manifest["snapshots"]:
        path = ROOT / "research/data/raw" / m["filename"]
        if not path.exists():
            raise FileNotFoundError(
                "Run uv run python research/acquire.py --download (or --from-cache PATH)"
            )
        if sha(path) != m["sha256"]:
            raise ValueError(f"Changed source snapshot: {path.name}")
        df = pd.read_csv(path, index_col="Date", parse_dates=True)
        if list(df.columns) != [m["ticker"]] or len(df) != m["rows"]:
            raise ValueError("Source schema/row mismatch")
        series.append(df)
    prices = pd.concat(series, axis=1)
    expected = xcals.get_calendar(
        "XNYS", start=manifest["start"], end=pd.Timestamp(manifest["end"]) - pd.Timedelta(days=1)
    ).sessions.tz_localize(None)
    if (
        not prices.index.equals(expected)
        or not np.isfinite(prices.to_numpy()).all()
        or (prices <= 0).any().any()
    ):
        raise ValueError("Missing sessions or invalid prices; filling is forbidden")
    r = prices.pct_change(fill_method=None).iloc[1:]
    validate_returns(r)
    audit = {
        "price_rows": len(prices),
        "return_rows": len(r),
        "first_price": str(prices.index[0].date()),
        "last_price": str(prices.index[-1].date()),
        "missing": int(prices.isna().sum().sum()),
        "duplicates": int(prices.index.duplicated().sum()),
        "max_abs_return": r.abs().max().to_dict(),
        "returns_over_25pct": int((r.abs() > 0.25).sum().sum()),
        "unchanged_price_fraction": (r == 0).mean().to_dict(),
        "calendar": "XNYS",
        "exclusions": "Only first undefined return; no missing observations filled or excluded.",
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "data_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return r


def trading_cost(pretrade, target, bps):
    u, w = np.asarray(pretrade, float), np.asarray(target, float)
    if (
        u.ndim != 1
        or u.shape != w.shape
        or len(u) == 0
        or not np.isfinite(u).all()
        or not np.isfinite(w).all()
    ):
        raise ValueError("Invalid weights")
    if min(u.min(), w.min()) < -1e-10 or max(u.sum(), w.sum()) > 1 + 1e-8 or not 0 <= bps < 10000:
        raise ValueError("Invalid budget or cost")
    a = bps / 10000
    fee = brentq(lambda c: c - a * np.abs((1 - c) * w - u).sum(), 0, 1, xtol=1e-14) if a else 0.0
    trades = (1 - fee) * w - u
    return fee, trades


def performance(r):
    a = np.asarray(r, float)
    wealth = np.cumprod(1 + a)
    vol = np.std(a, ddof=1) * np.sqrt(252)
    return {
        "n": len(a),
        "annual_mean": float(a.mean() * 252),
        "cagr": float(wealth[-1] ** (252 / len(a)) - 1),
        "volatility": float(vol),
        "mean_over_vol_rf0": float(a.mean() * 252 / vol) if vol > 0 else 0.0,
        "max_drawdown": float(np.min(wealth / np.maximum.accumulate(np.r_[1.0, wealth])[1:] - 1)),
        "terminal_wealth": float(wealth[-1]),
    }


def block_interval(a, b, measure="mean", block=21, draws=2000, seed=SEED):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape or a.ndim != 1 or len(a) < 2 * block or not np.isfinite(a + b).all():
        raise ValueError("Invalid paired sample")

    def stat(x, y):
        if measure == "mean":
            return (x - y).mean(axis=-1)
        if measure == "vol":
            return (x.std(axis=-1, ddof=1) - y.std(axis=-1, ddof=1)) * np.sqrt(252)
        if measure == "sharpe":
            return np.sqrt(252) * (
                x.mean(axis=-1) / x.std(axis=-1, ddof=1) - y.mean(axis=-1) / y.std(axis=-1, ddof=1)
            )
        raise ValueError(measure)

    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        starts = rng.integers(0, len(a), int(np.ceil(len(a) / block)))
        ix = ((starts[:, None] + np.arange(block)) % len(a)).ravel()[: len(a)]
        values.append(stat(a[ix], b[ix]))
    lo, hi = np.quantile(values, [0.025, 0.975])
    return {
        "estimate": float(stat(a, b)),
        "lower95": float(lo),
        "upper95": float(hi),
        "block": block,
        "draws": draws,
        "n": len(a),
    }


def table(frame):
    cols = list(frame.columns)
    rows = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        rows.append(
            "| "
            + " | ".join(
                "—" if pd.isna(v) else f"{v:.6g}" if isinstance(v, (float, np.floating)) else str(v)
                for v in row
            )
            + " |"
        )
    return "\n".join(rows) + "\n"


def provenance():
    paths = [
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        ROOT / "research/PROTOCOL.md",
        ROOT / "research/data/input_manifest.json",
        *sorted((ROOT / "research").glob("*.py")),
    ]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.exists()}


def write_metadata(settings):
    files = [*RESULTS.glob("*.csv"), *RESULTS.glob("*.json"), *FIGURES.glob("*.png")]
    files = [p for p in files if p.name != "run_metadata.json"]
    metadata = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.system(),
        "settings": settings,
        "source_and_code": provenance(),
        "artifacts": {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)},
        "private_artifacts": {
            str(p.relative_to(ROOT)): sha(p) for p in sorted((RESULTS / "paths").glob("*.csv"))
        },
    }
    (RESULTS / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


def check_hashes():
    m = json.loads((RESULTS / "run_metadata.json").read_text())
    if m["source_and_code"] != provenance():
        raise ValueError("Code/input/protocol changed: rerun study")
    for path, h in {**m["artifacts"], **m.get("private_artifacts", {})}.items():
        if sha(ROOT / path) != h:
            raise ValueError("Stale artifact: " + path)


def plot_style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler

    plt.rcParams.update(
        {
            "figure.figsize": (10, 5),
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "axes.prop_cycle": cycler(
                color=[
                    "#22577a",
                    "#bc6c25",
                    "#758e4f",
                    "#a66b88",
                    "#d0a648",
                    "#555555",
                    "#6c91a5",
                    "#9e7860",
                ]
            ),
        }
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    return plt

"""Acquire/check the explicit multi-asset vintage, without altering baseline snapshots."""

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from research.common import sha, validate_returns
from research.practical_config import ASSETS, START, END, ROOT, RESULTS, MANIFEST


def calendar():
    return xcals.get_calendar(
        "XNYS", start=START, end=pd.Timestamp(END) - pd.Timedelta(days=1)
    ).sessions.tz_localize(None)


def validate_prices(frame):
    if not frame.index.equals(calendar()) or frame.columns.has_duplicates:
        raise ValueError(
            "Calendar mismatch; missing="
            + str(calendar().difference(frame.index).strftime("%Y-%m-%d").tolist())
            + "; extra="
            + str(frame.index.difference(calendar()).strftime("%Y-%m-%d").tolist())
            + "; duplicates="
            + str(frame.index.duplicated().sum())
        )
    if not np.isfinite(frame.to_numpy()).all() or (frame <= 0).any().any():
        raise ValueError("Nonfinite or nonpositive adjusted prices")


def acquire(download=False):
    import yfinance as yf

    raw = ROOT / "research/data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(ROOT / ".cache/yfinance"))
    pinned = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None
    snapshots = []
    for ticker, name in ASSETS.items():
        path = raw / f"{ticker}_{START}_{END}.csv"
        meta = path.with_suffix(".json")
        expected = (
            next((s for s in pinned["snapshots"] if s["ticker"] == ticker), None)
            if pinned
            else None
        )
        if path.exists() and meta.exists():
            entry = json.loads(meta.read_text())
            if sha(path) != entry["sha256"] or (expected and entry["sha256"] != expected["sha256"]):
                raise ValueError("Snapshot hash mismatch: " + ticker)
            validate_prices(pd.read_csv(path, index_col="Date", parse_dates=True))
            print("Verified", ticker, flush=True)
        elif download:
            h = yf.Ticker(ticker).history(
                start=START, end=END, auto_adjust=False, actions=True, raise_errors=True
            )
            s = h["Adj Close"].rename(ticker)
            s.index = s.index.tz_localize(None).normalize().rename("Date")
            supplemental = []
            missing = calendar().difference(s.index)
            if len(missing) and len(missing) <= 5:
                repair = yf.Ticker(ticker).history(
                    start=str(missing.min().date()),
                    end=END,
                    auto_adjust=False,
                    actions=True,
                    raise_errors=True,
                )["Adj Close"]
                repair.index = repair.index.tz_localize(None).normalize().rename("Date")
                overlap = s.index.intersection(repair.index)
                if len(overlap) and not np.allclose(
                    s.loc[overlap], repair.loc[overlap], rtol=1e-6, atol=1e-6
                ):
                    raise ValueError("Supplemental request has conflicting adjusted prices")
                recovered = missing.intersection(repair.index)
                supplemental = [str(d.date()) for d in recovered]
                s = pd.concat([s, repair.reindex(recovered).rename(ticker)]).sort_index()
                print("Supplemental observed records", ticker, supplemental, flush=True)
            validate_prices(s.to_frame())
            temp = path.with_suffix(".partial")
            s.to_csv(temp, float_format="%.17g")
            if expected and sha(temp) != expected["sha256"]:
                raise ValueError("Vendor vintage changed; restore pinned cache: " + ticker)
            temp.replace(path)
            entry = {
                "ticker": ticker,
                "name": name,
                "filename": path.name,
                "sha256": sha(path),
                "source_url": f"https://finance.yahoo.com/quote/{ticker}/history/",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "yfinance_version": yf.__version__,
                "rows": len(s),
                "first_date": str(s.index[0].date()),
                "last_date": str(s.index[-1].date()),
                "supplemental_observed_dates": supplemental,
                "field": "Adj Close",
                "units": "USD adjusted price; simple decimal returns",
                "restrictions": "Provider terms apply; raw snapshots are not redistributed.",
            }
            meta.write_text(json.dumps(entry, indent=2) + "\n")
            print("Downloaded", ticker, len(s), entry["last_date"], flush=True)
        else:
            raise FileNotFoundError(
                f"{path.name}: use --download or restore matching permitted cache"
            )
        snapshots.append(entry)
    if not pinned:
        MANIFEST.write_text(
            json.dumps(
                {
                    "start": START,
                    "end_exclusive": END,
                    "kind": "Observed adjusted-close snapshots",
                    "caveat": "Revised vendor history, not point-in-time; no fills; fixed surviving ETF universe.",
                    "snapshots": snapshots,
                },
                indent=2,
            )
            + "\n"
        )
    load_data(write_audit=True)


def load_data(write_audit=False):
    manifest = json.loads(MANIFEST.read_text())
    if manifest["start"] != START or manifest["end_exclusive"] != END:
        raise ValueError("Manifest and declared sample differ")
    series = []
    for entry in manifest["snapshots"]:
        path = ROOT / "research/data/raw" / entry["filename"]
        if sha(path) != entry["sha256"]:
            raise ValueError("Source changed: " + entry["ticker"])
        f = pd.read_csv(path, index_col="Date", parse_dates=True)
        if list(f.columns) != [entry["ticker"]] or len(f) != entry["rows"]:
            raise ValueError("Schema/row-count mismatch")
        series.append(f)
    prices = pd.concat(series, axis=1)
    validate_prices(prices)
    if list(prices.columns) != list(ASSETS):
        raise ValueError("Universe order changed")
    r = prices.pct_change(fill_method=None).iloc[1:]
    validate_returns(r)
    if write_audit:
        RESULTS.mkdir(parents=True, exist_ok=True)
        audit = {
            "first_price": str(prices.index[0].date()),
            "last_price": str(prices.index[-1].date()),
            "price_rows": len(prices),
            "return_rows": len(r),
            "assets": len(ASSETS),
            "missing": 0,
            "duplicates": 0,
            "calendar": "XNYS",
            "fills": 0,
            "max_absolute_daily_return": r.abs().max().to_dict(),
            "unchanged_price_fraction": r.eq(0).mean().to_dict(),
            "returns_over_25pct": int((r.abs() > 0.25).sum().sum()),
        }
        (RESULTS / "data_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return prices, r


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--download", action="store_true")
    acquire(p.parse_args().download)

"""Explicit new-vintage acquisition; original manifest and snapshots remain recoverable."""

import argparse
from datetime import datetime, timezone
import json
import shutil
import pandas as pd
import numpy as np
import yfinance as yf
import exchange_calendars as xcals
from common import ROOT, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--end", required=True, help="Exclusive last date, after last completed US session"
    )
    args = parser.parse_args()
    mf = ROOT / "research/data/input_manifest.json"
    old = json.loads(mf.read_text())
    archive = mf.with_name("input_manifest_initial.json")
    if not archive.exists():
        shutil.copyfile(mf, archive)
    expected = xcals.get_calendar(
        "XNYS", start=old["start"], end=pd.Timestamp(args.end) - pd.Timedelta(days=1)
    ).sessions.tz_localize(None)
    dest = ROOT / "research/data/raw"
    dest.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(ROOT / ".cache/yfinance"))
    snapshots = []
    changes = []
    for previous in old["snapshots"]:
        ticker = previous["ticker"]
        filename = f"{ticker}_{old['start']}_{args.end}.csv"
        path = dest / filename
        meta = path.with_suffix(".json")
        if path.exists() and meta.exists():
            m = json.loads(meta.read_text())
            if sha(path) != m["sha256"]:
                raise ValueError("Checkpoint changed")
            print("Resumed", ticker, flush=True)
        else:
            h = yf.Ticker(ticker).history(
                start=old["start"], end=args.end, auto_adjust=False, actions=True, raise_errors=True
            )
            s = h["Adj Close"].rename(ticker)
            s.index = s.index.tz_localize(None).normalize().rename("Date")
            if not s.index.equals(expected) or not np.isfinite(s).all() or (s <= 0).any():
                raise ValueError("Incomplete or invalid refreshed history: " + ticker)
            temp = path.with_suffix(".partial")
            s.to_csv(temp, float_format="%.17g")
            temp.replace(path)
            m = {
                **previous,
                "filename": filename,
                "start_inclusive": old["start"],
                "end_exclusive": args.end,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "yfinance_version": yf.__version__,
                "rows": len(s),
                "first_date": str(s.index[0].date()),
                "last_date": str(s.index[-1].date()),
                "sha256": sha(path),
            }
            meta.write_text(json.dumps(m, indent=2) + "\n")
            print("Downloaded", ticker, len(s), m["last_date"], flush=True)
        before = pd.read_csv(dest / previous["filename"], index_col=0, parse_dates=True).iloc[:, 0]
        after = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        ix = before.index.intersection(after.index)
        relative = (after.loc[ix] / before.loc[ix] - 1).abs()
        changes.append(
            {
                "ticker": ticker,
                "old_last": str(before.index[-1].date()),
                "new_last": str(after.index[-1].date()),
                "added_rows": len(after) - len(before),
                "overlap_price_max_relative_revision": float(relative.max()),
                "overlap_revised_rows_gt_1e_10": int((relative > 1e-10).sum()),
            }
        )
        snapshots.append(m)
    candidate = {
        **old,
        "end": args.end,
        "origin": "Explicit user-authorized Yahoo Finance refresh; initial manifest and snapshots retained.",
        "snapshots": snapshots,
        "refresh_utc": datetime.now(timezone.utc).isoformat(),
    }
    tmp = mf.with_suffix(".partial")
    tmp.write_text(json.dumps(candidate, indent=2) + "\n")
    tmp.replace(mf)
    pd.DataFrame(changes).to_csv(ROOT / "research/results/source_refresh.csv", index=False)


if __name__ == "__main__":
    main()

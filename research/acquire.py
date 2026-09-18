"""Restore exact pinned snapshots; never silently accept a revised vendor history."""

import argparse
import json
import shutil
from pathlib import Path
from common import ROOT, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-cache", type=Path)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "research/data/input_manifest.json").read_text())
    dest = ROOT / "research/data/raw"
    dest.mkdir(parents=True, exist_ok=True)
    for m in manifest["snapshots"]:
        path = dest / m["filename"]
        if path.exists():
            if sha(path) != m["sha256"]:
                raise ValueError("Existing snapshot changed: " + path.name)
            print("Verified", path.name)
            continue
        partial = path.with_suffix(".partial")
        if args.from_cache:
            shutil.copyfile(args.from_cache / path.name, partial)
        elif args.download:
            import yfinance as yf

            yf.set_tz_cache_location(str(ROOT / ".cache/yfinance"))
            h = yf.Ticker(m["ticker"]).history(
                start=manifest["start"],
                end=manifest["end"],
                interval="1d",
                auto_adjust=False,
                actions=True,
                raise_errors=True,
            )
            s = h["Adj Close"].rename(m["ticker"])
            s.index = s.index.tz_localize(None).normalize().rename("Date")
            s.to_csv(partial, float_format="%.17g")
        else:
            raise FileNotFoundError(
                "Missing " + path.name + "; use --from-cache PATH or --download"
            )
        if sha(partial) != m["sha256"]:
            raise ValueError(
                "Source vintage changed: "
                + path.name
                + ". Partial retained for inspection; restore pinned cache or document a new research vintage. Do not edit hashes to bypass this check."
            )
        partial.replace(path)
        print("Restored", path.name)


if __name__ == "__main__":
    main()

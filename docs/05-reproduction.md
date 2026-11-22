# Reproduce the historical study

The main reading path is [the executed notebook](../study.ipynb). The project uses
Python 3.12, `pyproject.toml` and the committed `uv.lock`. Run from this repository:

```bash
uv sync --locked
uv run python research/practical_data.py --download
uv run python research/run_study.py
uv run python research/build_notebook.py
uv run python -m pytest -q
uv run python research/check_artifacts.py
uv run python -m ruff check research tests
uv run python -m ruff format --check research tests
```

The source manifest pins the exact vendor snapshots. A later download may contain
revised adjustments and will fail its hash check; restore a matching permitted cache
or deliberately create and document a new vintage. Do not edit hashes to conceal a
source change. For an already populated cache, omit `--download`; the study itself
has no network requirement.

Acquisition checkpoints per asset. HMM fits checkpoint by model settings, input hashes
and numerical code. The study reuses matching checkpoints and recomputes when they
change. Public summaries and figures are under `research/results/practical/` and
`research/figures/practical/`; full daily paths and price snapshots are local and ignored.
The notebook is saved only after fresh-kernel execution, alongside a local HTML preview
in `research/preview/study.html`.

## Reproduce the S&P 500 portfolio chart

The study runner also applies the portfolio rule to its daily filtered states. To
replay just that calculation from a matching local archive, run the two commands
below. The first verifies the pinned SPY prices and daily state file against the
study manifests, then writes the two summary CSVs in `docs/figures/`. The second
redraws the portfolio chart from those summaries and the archived daily labels.
Each background band begins at the close when the filtered label changes and ends
at the next change or the final observation. The rendered chart is included in a
fresh checkout.

```bash
uv run python -m research.landing_backtest
uv run python -m research.landing_figure
```

All three portfolios begin with $100 in cash at the first signal close on 2 June
2008. Their first trades occur at the 3 June close and first earn the return to the
4 June close. Entry and subsequent trades cost 5 basis points per dollar traded.
Cash earns zero interest and terminal wealth is marked at the last close.
The wealth CSV retains the starting balance, the last observed close of each month,
and the partial final month through 21 September 2026. The performance CSV uses all
4,604 daily returns. CAGR compounds at 252 sessions per year and maximum drawdown
uses the running peak of daily wealth including the starting balance.

## Earlier SPY forecast study

The previous SPY forecast study remains in the Git revision
`4c0164ea5a114d865b45bd4b48f40ce72954a7c4`. Original source/result artifacts at the top
level of `research/results/` and `research/figures/` are retained as that dated baseline;
the maintained main entry point executes the broader practical study.

CI runs offline model/accounting checks and validates public notebook outputs. It does
not download market data or certify a complete numerical rerun from licensed inputs.
[Sources and data terms](../research/SOURCES.md) · [Publication review](../PUBLICATION.md).

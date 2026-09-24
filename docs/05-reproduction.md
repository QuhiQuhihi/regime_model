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

The previous SPY forecast study remains in the Git revision
`4c0164ea5a114d865b45bd4b48f40ce72954a7c4`. Original source/result artifacts at the top
level of `research/results/` and `research/figures/` are retained as that dated baseline;
the maintained main entry point executes the broader practical study.

CI runs offline model/accounting checks and validates public notebook outputs. It does
not download market data or certify a complete numerical rerun from licensed inputs.
[Sources and data terms](../research/SOURCES.md) · [Publication review](../PUBLICATION.md).

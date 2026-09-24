# Renovation work log

Started 2026-09-19 in WSL as daham. Original commit `ef792c69a68de078cd94fcb99558aaedb12511b9` is preserved on `old`; active branch `renovation`. No remote operations.

Reference inspected: corporate-bond project at `1f565f6d7010274ff8feb333b9c05be11ba1dcfa`, README, protocol, sources, evaluation, agenda, publication review.

Initial phase: audit and protocol, before primary evaluation. Outputs: `research/results/`, `research/figures/`, `study.ipynb`; raw snapshots stay ignored in `research/data/raw/`. Reruns overwrite only generated artifacts. Notebook replaced atomically after successful clean-kernel execution.

Recovery: `uv sync --locked`; `uv run python research/acquire.py` (data projects); `uv run python research/run_study.py`; `uv run python research/build_notebook.py`; `uv run pytest -q`; `uv run python research/check_artifacts.py`. Acquisition reuses valid per-ticker hashes and stops on changed sources.

User authorized fresh data. Refreshing through last completed US close, 2026-09-17 (retrieval begins 2026-09-18 16:25 UTC; Sep 18 session still open). Initial protocol/manifest preserved, initial performance not evaluated. New primary end will be documented before evaluation.

## Completed verification — 19 September 2026 KST

- `uv sync --locked --offline`: succeeded using the installed Linux Python 3.12 environment and cached dependencies.
- The Allocation refresh command acquired fresh Yahoo snapshots through 17 September; Regime imported the identical refreshed SPY/TLT snapshots with retrieval metadata and 12 added sessions. `uv run python research/acquire.py` in this project verified all pinned hashes from local cache. Original vintages retained.
- `uv run python research/run_study.py`: completed numerical study; the notebook build also reran its maintained entry point.
- `uv run python research/build_notebook.py`: successful fresh-kernel execution, 12 code cells, 5 embedded quantitative figures, zero cell errors. Notebook headline matches generated results. HTML preview has embedded figures and tables.
- `uv run python -m pytest -q`: **4 passed**.
- `uv run python -m ruff check research tests` and `uv run python -m ruff format --check research tests`: passed.
- `uv run python research/check_artifacts.py`: public links/notebook checks, current source/code/output hashes and independent saved-output calculations passed.
- All 5 generated PNGs inspected; exact sample/convention labels checked. HTML structure inspected programmatically; no full browser/site layout certification.

The exact final numerical conclusions are in [generated results](../docs/02-results.md).
[Acceptance evidence](ACCEPTANCE.md) records coverage and boundaries. Local checks exercise the
committed CI commands; no remote GitHub workflow, push, deployment or live blog publication was run.
The maintained Git tree omits raw vendor histories, ignored recovery material, environments and
caches. Historical credential/rights boundaries remain in [publication review](../PUBLICATION.md).

Final Git review: original `old` reference verified; maintained Markdown links resolve within the staged tree. Tracked evidence hashes match staged bytes, and raw/recovery/environment paths are absent. `.gitattributes` preserves Linux source line endings and exact hashed CSV serializer bytes. Staged whitespace checks pass.

## Practical research redesign — 24 September 2026

User requested fast regime recognition for model recalibration, useful retrospective
views, historical backtests beyond US equities, and stronger visual storytelling.
Starting clean main: 4c0164e. Preserved as before-practical-regimes-20260924; old remains
ef792c6. Active branch practical-regimes-20260924. Prior forecast result remains a
baseline, not the definition of usefulness for every regime application.

Outputs: research/results/practical/, research/figures/practical/, study.ipynb.
Private downloaded prices and daily paths remain ignored. Per-asset acquisition and
model configurations checkpoint with input/code/settings hashes. Restart acquisition
with uv run python research/practical_data.py --download, study with uv run python
research/run_study.py, notebook with uv run python research/build_notebook.py.
Expected numerical work: a few minutes for monthly HMM fits and bounded sensitivities;
notebook uses verified cached fits, and is replaced only after successful execution.

## Completed practical study — 24 September 2026

- Eight Yahoo adjusted-close series acquired from March 2006. EFA lacks 22 September
  in both broad and targeted requests; before evaluation the common cutoff moved to
  21 September. All eight final snapshots have 5,172 prices and complete XNYS sessions.
- The initial raw-return HMM changes labels on 55.5% of adjacent dates. The dated
  feature amendment introduces smoothed asset-group risk levels and stock–bond
  dependence for a more useful research description. Initial tables remain under
  `initial_raw_return_*.csv`, and the raw-return reset is retained on matched dates.
- Feature model: 220 monthly fits, zero failures; 4,600 scored forecast dates.
  Matched-date label switching is 3.2% versus 55.3% for raw returns; 26 review alarms.
  HMM-reset mean loss difference versus slow EWMA is -0.000457, pointwise paired
  95% interval [-0.024880, +0.016732]. Descriptive stability is not forecast superiority.
- The 2008 event check distinguishes an existing stressed state from a new alert.
  This avoids interpreting a missing fresh review as failure to recognize existing risk.
- Locked environment sync, nine tests, lint and formatting pass. Notebook executes
  in a fresh kernel: 18 code cells, nine embedded original figures, no errors.
  Independent checks reconcile every forward target, forecast matrix diagonal,
  basket risk, reset date and reported headline, alongside provenance hashes.
- Browser inspection at 1440 px and 390 px: all nine figures load, no JavaScript or
  math errors, mobile document width 390 px. Screenshots and browser evidence are in
  `/tmp/regime-practical-review`; the local HTML is `research/preview/study.html`.

Current main reading path: README → research chapters → study.ipynb. Reproduction
instructions moved to docs/05-reproduction.md so the introduction leads with research.
The final notebook reruns the maintained pipeline with verified HMM checkpoints. Raw
prices and daily panels remain local and ignored; public summaries retain sensitivity,
revision and synthetic-detection findings including poor or inconclusive outcomes.

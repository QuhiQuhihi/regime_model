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

# Local publication preparation

The maintained tree contains research code, narrative, executed study, generated aggregate
results and original figures. Original notebooks, helper code and data are recoverable from
`old` and ignored `research/private-legacy/`; these historical copies are not release-cleared.
No Git history rewrite, remote push, visibility change or live blog publication was performed.

## Current-file review

Run `uv run python research/check_artifacts.py --public` to check maintained links, notebook
outputs and blocked data paths. Full `uv run python research/check_artifacts.py` additionally
verifies provenance and independently reconstructs consequential saved numerical results.
Review `git diff --stat old` and explicit files; avoid printing full historical diffs that may
contain old credential values. The audit records credential findings by category/path only.

Raw vendor snapshots and private legacy data are excluded by `.gitignore`; no unrestricted
data redistribution or commercial-use rights are asserted. Reproduction requires permitted
access to the pinned cache; a later vendor download may differ and must not silently replace
it. Numerical fixtures in the FICC project are explicitly original illustrative assumptions.
Keep original attribution in `NOTICE` and the source register. No blanket license is inferred.

## History and release boundary

A clean maintained branch does not clean the `old` branch, earlier commits, remote copies or
local archives. Legacy vendor inputs and preserved material have unestablished redistribution rights.
Do not publish ignored recovery folders. No full-history rights or secret clearance is claimed.

CI installs the locked Linux environment, runs focused synthetic/known-answer tests and public
artifact checks. It does not download licensed histories, certify provider data quality or
validate live execution. Local complete reproduction commands are in the README. Review the
rendered notebook and figures before any separately authorized publication.

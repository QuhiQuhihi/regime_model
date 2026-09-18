# Audit — 19 September 2026

Starting commit: `ef792c69a68de078cd94fcb99558aaedb12511b9` (branch `old`). Clean status verified before edits. All root notebooks inspected as JSON without execution; README, helper modules, data inventory and source schemas inspected. Saved outputs are not validation.

Original: automated historical state charts with a multivariate Gaussian mixture and greedy segmentation. README refers to hidden Markov methods and possible regime-shift usefulness. Audience: quantitative Python readers.

Verified defects:
- `00_Gausian_Mixture_Model(GMM).ipynb`, cell 2 changes to an unrelated absolute checkout; cell 4 fills missing returns with zero; cell 7 includes a cumulative index level among mixed-scale return features.
- Cell 8 calls sklearn GaussianMixture.fit/predict on the complete X, with no transition model. The HMM captions and SPY title are unsupported by this MSCI feature design. This is descriptive full-sample clustering, not causal forecasting.
- `01_Greedy_Gausian_Segmentation(GSS).ipynb`, cells 7–11 estimate full-sample breakpoints and paint the same history. Breakpoint dates are not detection dates; no detection-delay evidence is supplied.
- Utilities and index exports have no retrieval-vintage or redistribution contract sufficient for new point-in-time market claims.

Disposition: replace causal model/evaluation logic; retain GMM as a mixture baseline and add an explicitly filtered HMM. Full-sample smoothed HMM and greedy Gaussian segmentation supply retrospective diagnostics; the original GMM chart remains archived. GGS upstream attribution to Hallac, Nystrup and Boyd is retained; bundled upstream examples/data/PDFs are preserved on old and in local recovery, excluded from public maintained inputs. No unvalidated upstream execution is asserted. Full per-file disposition: `legacy_inventory.json`.

Primary question: does a two-state filtered HMM improve next-session SPY squared-return forecasts relative to EWMA? GMM and one-state moments are baselines; one probability overlay is supporting. Revised scope uses sourced SPY/TLT ETF returns rather than unverifiable vendor index exports. A synthetic variance-break diagnostic tests algorithm behavior only. Returns are revised historical snapshots, not an untouched holdout or independent recession labels.

Recovery: `git show old:<path>` or ignored `research/private-legacy/<path>`. Original history is intentionally preserved, not publication-cleared.

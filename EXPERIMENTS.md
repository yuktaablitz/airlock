# Experiment log

Every trial is kept: raw outputs `runs/eval_raw_<tag>.jsonl`, metrics `runs/results_<tag>.{md,json}`,
thresholds `runs/thresholds_<tag>.json`, chart `runs/pareto_<tag>.png`. Reproduce a trial with
`AIRLOCK_CRITERIA=<tag> python -m eval.run && AIRLOCK_CRITERIA=<tag> python -m eval.report` (cached calls are free).

## Dataset v2 (current): disjoint sentences, carriers and holdout

A code review found that dataset v1 leaked, so it was rebuilt:
- **Carriers** are split by document (20% dev / 80% test, seed 1337) as before.
- **Injected sentences are now split as well.** BIPIA attacker goals come from BIPIA's own train file (dev) and test
  file (test). Hand-written attacks and benign look-alikes are split 20/80 into disjoint pools. In v1, the same sentence
  could appear in dev and test.
- **The holdout** (100 rows, 20 benign sentences written after v2) uses 100 BIPIA tables that are in neither dev nor test.
  In v1, holdout rows reused dev/test carriers.
- Verified: zero shared sentences or carriers across dev, test and holdout.

Test n=498, holdout n=100. Columns read Drex only / Airlock cascade / LLM guard.

| Criteria | What changed | F1 | Recall (Drex / Airlock) | FPR test hard negatives | FPR holdout | Thresholds (dev) |
|---|---|---|---|---|---|---|
| v1 | Criteria from the build brief | 0.960 / 0.960 / 0.898 | 99.5% / 99.0% | 18.8% / 17.6% / 54.1% | 14% / 18% / 83% | τ=0.4; band 0.3–0.6 |
| v2 | Names benign look-alikes, **quoting phrases that occur in the eval** | 0.981 / 0.972 / 0.898 | 99.5% / 99.5% | 8.2% / 12.9% / 54.1% | 7% / 14% / 83% | τ=0.5; band 0.3–0.5 |
| **v3 (default)** | v2's categories with **no quoted sentences** | 0.971 / 0.972 / 0.898 | 95.7% / **100%** | **3.5%** / 14.1% / 54.1% | **3%** / 16% / 83% | τ=0.8; band 0.3–0.5 |

Latency (v3): p50 279 / 281 / 854 ms, p95 416 / 477 / 2668 ms. Escalated chunks (v3): 0.8%.

**Why v3 is the default, not v2:** v2 quotes phrases ("ignore the previous email", "forward this to your manager", …)
that also occur in test rows, so its test numbers are not clean. v3 says the same thing as categories only. v1 also quotes two
phrases from the build brief ("please log in", "reply by Friday") that occur in eval sentences; we keep it as the baseline trial.

**Finding: the LLM is where false positives come from.** Drex alone (precision mode) flags 3% of unseen benign
look-alikes. Escalating Drex's uncertain band to Qwen recovers the last attacks (recall 95.7% → 100%, mostly BIPIA's
bare tasks and role-tag attacks), but Qwen also flags benign chunks in that band, as it does as a standalone guard (83%).
Both operating points are shipped (`AIRLOCK_MODE=precision|recall`). Recall mode is the default because a false positive
costs one redacted sentence, not the whole document.

## Leakage notes

- Thresholds are grid-searched on dev only (`eval/report.py: tune`) and applied unchanged to test and holdout.
- Criteria versions were changed after looking at errors on dataset v1's test split. Dataset v2 regenerated every row
  and the holdout was never inspected before reporting. v3's wording quotes nothing from any split.
- Eval runs disable the reviewer allow-list (`AIRLOCK_USE_ALLOWLIST=0`), so dashboard clicks cannot change eval prompts.
- Model errors count as "not flagged" for every system (Intern hooks fail open). All runs had 0 errors.

## Archived: dataset v1 (leaky)

`runs/archive_leaky/` holds the first two trials on dataset v1. They reported Airlock F1 0.930 → 0.966 and test hard-negative
FPR 27.1% → 7.1%. Those numbers are superseded: the test hard-negative sentences were shared with dev and quoted by the v2 criteria.

## Not in the eval (demo only)

- **Hidden-text manipulation** (`system1.py`, `_hidden_manipulation`). This question is asked only for chunks that NDI's
  rendering shows are invisible to a human. No eval row is a rendered document, so the numbers above don't exercise it. On
  `demo/subtle/invoice.pdf`, without NDI's visibility check (text layer only), Drex scores the hidden "bank changed" notice 0.015 and it passes. With it, the hidden-text
  question scores it ≥0.998.

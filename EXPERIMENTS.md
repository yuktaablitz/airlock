# Experiment log

Every trial is kept: raw outputs `runs/eval_raw_<tag>.jsonl`, metrics `runs/results_<tag>.{md,json}`,
thresholds `runs/thresholds_<tag>.json`, chart `runs/pareto_<tag>.png`. Reproduce any trial with
`AIRLOCK_CRITERIA=<tag> python -m eval.run && AIRLOCK_CRITERIA=<tag> python -m eval.report` (cached calls are free).

| Trial | What changed | Test F1 (Drex-only / Airlock / LLM guard) | FPR hard negatives, test (Airlock) | FPR held-out hard negatives (Drex-only / Airlock / LLM guard) |
|---|---|---|---|---|
| v1 | Noul criteria from the build brief | 0.915 / 0.930 / 0.861 | 27.1% | 38% / 35% / 77% |
| v2 | Criteria name benign look-alikes: commands to the human recipient, corrections of earlier messages, a product's own chatbot | 0.950 / 0.966 / 0.861 | 7.1% | 30% / 15% / 77% |

## Leakage notes

- **Splits are by carrier document** (20% dev / 80% test, seed 1337): one email/table/page never appears in two splits.
- **Thresholds** are grid-searched on dev only (`eval/report.py: tune`) and applied unchanged to test and holdout.
- **v2's criteria were written after reading v1's errors on test hard negatives.** That is test leakage for the
  `hard_negative` family, so v2's test FPR there (7.1%) is optimistic. To measure v2 honestly we wrote a **new holdout**
  (`HARD_NEGATIVES_HOLDOUT`, 20 new sentences × 100 rows, own RNG, split `holdout`) *after* v2 and never tuned on it.
  The holdout column is the number to trust: 35% → 15% for Airlock.
- The LLM guard has no tunable threshold and the same prompt in both trials, so its numbers are identical.

## Not in the eval (demo only)

- **Hidden-text manipulation** (`system1.py`, `_hidden_manipulation` question). It is only asked for chunks that NDI's rendering
  shows are invisible to a human. No eval row has a rendered document, so this check is untouched by the numbers above;
  it is shown on `demo/subtle/invoice.pdf`, where the injection-only criteria scored the hidden "bank changed" notice
  p=0.24 (passed) and the hidden-text question scores it p=0.999 (blocked).

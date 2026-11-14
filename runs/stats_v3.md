# Uncertainty and calibration (test n=498, holdout n=100; criteria v3)

95% bootstrap intervals, 2,000 resamples.

| System | F1 | FPR test hard negatives | FPR held-out hard negatives |
|---|---|---|---|
| LLM guard | 0.898 [0.866–0.925] | 54.1% [43.5%–64.7%] | 83.0% [75.0%–90.0%] |
| Drex only | 0.971 [0.952–0.986] | 3.5% [0.0%–8.2%] | 3.0% [0.0%–7.0%] |
| Airlock recall | 0.972 [0.954–0.986] | 14.1% [7.1%–22.4%] | 16.0% [9.0%–23.0%] |

## Paired McNemar tests (per-row correctness, exact)

| Comparison | A right, B wrong | A wrong, B right | p |
|---|---|---|---|
| drex vs llm guard | 43 | 8 | 6.9e-07 |
| airlock vs llm guard | 35 | 0 | 5.8e-11 |
| airlock vs drex | 9 | 9 | 1 |

## Calibration of Drex chunk probabilities (1968 chunks, 284 injected)

Expected calibration error **0.008**, Brier score 0.0212.

| p bin | chunks | mean p | fraction injected |
|---|---|---|---|
| 0.0–0.1 | 1648 | 0.016 | 0.015 |
| 0.1–0.2 | 40 | 0.139 | 0.100 |
| 0.2–0.3 | 13 | 0.244 | 0.462 |
| 0.3–0.4 | 7 | 0.361 | 0.286 |
| 0.4–0.5 | 9 | 0.456 | 0.556 |
| 0.5–0.6 | 10 | 0.546 | 0.700 |
| 0.6–0.7 | 5 | 0.651 | 1.000 |
| 0.7–0.8 | 9 | 0.738 | 0.778 |
| 0.8–0.9 | 24 | 0.851 | 0.875 |
| 0.9–1.0 | 203 | 0.985 | 1.000 |

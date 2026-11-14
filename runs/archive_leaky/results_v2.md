# Airlock results (test split, n=498; thresholds fixed on dev, n=102)

Thresholds from dev: Drex-only τ=0.2; Airlock τ_low=0.3, τ_high=0.5.
Prices ($/1M tokens): Drex in 0.1 / out 0.1; Qwen3.8-27B in 0.2 / out 2.5 (DeepInfra).

| System | Precision | Recall | F1 | FPR hard negatives | FPR clean | p50 ms | p95 ms | $ / 1k results | Span coverage | Benign text kept | Escalated chunks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 77.1% | 97.6% | 0.861 | 70.6% | 0.0% | 879 | 2765 | $0.178 | n/a | n/a | n/a |
| Drex only (System 1) | 93.5% | 96.6% | 0.950 | 16.5% | 0.0% | 275 | 446 | $0.165 | 93.7% | 92.2% | 0.0% |
| Airlock (Drex → Qwen on band) | 97.1% | 96.1% | 0.966 | 7.1% | 0.0% | 277 | 481 | $0.167 | 92.3% | 92.7% | 0.5% |

## Recall by attack family (test)

| Family | LLM guard (Qwen3.8-27B, whole doc) | Drex only (System 1) | Airlock (Drex → Qwen on band) |
|---|---|---|---|
| addressed | 100.0% | 100.0% | 100.0% |
| covert | 100.0% | 100.0% | 100.0% |
| hand | 100.0% | 100.0% | 100.0% |
| override | 100.0% | 100.0% | 100.0% |
| polite | 100.0% | 100.0% | 100.0% |
| raw | 83.9% | 77.4% | 74.2% |
| roletag | 100.0% | 100.0% | 100.0% |

## Held-out hard negatives (n=100; new benign sentences, never used for tuning)

| System | False-positive rate |
|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 77.0% |
| Drex only (System 1) | 30.0% |
| Airlock (Drex → Qwen on band) | 15.0% |

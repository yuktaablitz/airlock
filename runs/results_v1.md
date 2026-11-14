# Airlock results (test split, n=498; thresholds fixed on dev, n=102)

Thresholds from dev: Drex-only τ=0.2; Airlock τ_low=0.15, τ_high=0.5.
Prices ($/1M tokens): Drex in 0.1 / out 0.1; Qwen3.8-27B in 0.2 / out 2.5 (DeepInfra).

| System | Precision | Recall | F1 | FPR hard negatives | FPR clean | p50 ms | p95 ms | $ / 1k results | Span coverage | Benign text kept | Escalated chunks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 77.1% | 97.6% | 0.861 | 70.6% | 0.0% | 879 | 2765 | $0.178 | n/a | n/a | n/a |
| Drex only (System 1) | 87.0% | 96.6% | 0.915 | 35.3% | 0.0% | 273 | 408 | $0.137 | 93.7% | 91.2% | 0.0% |
| Airlock (Drex → Qwen on band) | 89.7% | 96.6% | 0.930 | 27.1% | 0.0% | 277 | 1502 | $0.143 | 94.2% | 91.7% | 1.4% |

## Recall by attack family (test)

| Family | LLM guard (Qwen3.8-27B, whole doc) | Drex only (System 1) | Airlock (Drex → Qwen on band) |
|---|---|---|---|
| addressed | 100.0% | 100.0% | 100.0% |
| covert | 100.0% | 100.0% | 100.0% |
| hand | 100.0% | 100.0% | 100.0% |
| override | 100.0% | 100.0% | 100.0% |
| polite | 100.0% | 100.0% | 100.0% |
| raw | 83.9% | 77.4% | 77.4% |
| roletag | 100.0% | 100.0% | 100.0% |

## Held-out hard negatives (n=100; new benign sentences, never used for tuning)

| System | False-positive rate |
|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 77.0% |
| Drex only (System 1) | 38.0% |
| Airlock (Drex → Qwen on band) | 35.0% |

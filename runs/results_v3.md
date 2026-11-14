# Airlock results (test split, n=498; thresholds fixed on dev, n=102)

Thresholds from dev: Drex-only τ=0.8; Airlock τ_low=0.3, τ_high=0.5.
Prices ($/1M tokens): Drex in 0.1 / out 0.1; Qwen3.8-27B in 0.2 / out 2.5 (DeepInfra).

| System | Precision | Recall | F1 | FPR hard negatives | FPR clean | p50 ms | p95 ms | $ / 1k results | Span coverage | Benign text kept | Escalated chunks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 81.7% | 99.5% | 0.898 | 54.1% | 0.0% | 855 | 2669 | $0.176 | n/a | n/a | n/a |
| Drex only (System 1) | 98.5% | 95.7% | 0.971 | 3.5% | 0.0% | 280 | 416 | $0.153 | 85.5% | 92.9% | 0.0% |
| Airlock (Drex → Qwen on band) | 94.5% | 100.0% | 0.972 | 14.1% | 0.0% | 282 | 478 | $0.160 | 96.6% | 91.7% | 0.8% |

## Recall by attack family (test)

| Family | LLM guard (Qwen3.8-27B, whole doc) | Drex only (System 1) | Airlock (Drex → Qwen on band) |
|---|---|---|---|
| addressed | 100.0% | 95.7% | 100.0% |
| covert | 100.0% | 100.0% | 100.0% |
| hand:behavior_change | 100.0% | 100.0% | 100.0% |
| hand:deception | 100.0% | 100.0% | 100.0% |
| hand:exfiltration | 100.0% | 100.0% | 100.0% |
| hand:tool_misuse | 100.0% | 100.0% | 100.0% |
| override | 100.0% | 100.0% | 100.0% |
| polite | 100.0% | 100.0% | 100.0% |
| raw | 100.0% | 76.2% | 100.0% |
| roletag | 96.0% | 88.0% | 100.0% |

## Held-out hard negatives (n=100; new benign sentences, never used for tuning)

| System | False-positive rate |
|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 83.0% |
| Drex only (System 1) | 3.0% |
| Airlock (Drex → Qwen on band) | 16.0% |

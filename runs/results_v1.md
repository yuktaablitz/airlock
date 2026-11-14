# Airlock results (test split, n=498; thresholds fixed on dev, n=102)

Thresholds from dev: Drex-only τ=0.4; Airlock τ_low=0.3, τ_high=0.6.
Prices ($/1M tokens): Drex in 0.1 / out 0.1; Qwen3.8-27B in 0.2 / out 2.5 (DeepInfra).

| System | Precision | Recall | F1 | FPR hard negatives | FPR clean | p50 ms | p95 ms | $ / 1k results | Span coverage | Benign text kept | Escalated chunks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 81.7% | 99.5% | 0.898 | 54.1% | 0.0% | 855 | 2669 | $0.176 | n/a | n/a | n/a |
| Drex only (System 1) | 92.8% | 99.5% | 0.960 | 18.8% | 0.0% | 274 | 604 | $0.137 | 94.2% | 91.6% | 0.0% |
| Airlock (Drex → Qwen on band) | 93.2% | 99.0% | 0.960 | 17.6% | 0.0% | 277 | 855 | $0.146 | 92.8% | 91.9% | 1.1% |

## Recall by attack family (test)

| Family | LLM guard (Qwen3.8-27B, whole doc) | Drex only (System 1) | Airlock (Drex → Qwen on band) |
|---|---|---|---|
| addressed | 100.0% | 100.0% | 100.0% |
| covert | 100.0% | 100.0% | 100.0% |
| hand:behavior_change | 100.0% | 100.0% | 100.0% |
| hand:deception | 100.0% | 100.0% | 100.0% |
| hand:exfiltration | 100.0% | 100.0% | 100.0% |
| hand:tool_misuse | 100.0% | 100.0% | 100.0% |
| override | 100.0% | 100.0% | 100.0% |
| polite | 100.0% | 100.0% | 100.0% |
| raw | 100.0% | 95.2% | 95.2% |
| roletag | 96.0% | 100.0% | 96.0% |

## Held-out hard negatives (n=100; new benign sentences, never used for tuning)

| System | False-positive rate |
|---|---|
| LLM guard (Qwen3.8-27B, whole doc) | 83.0% |
| Drex only (System 1) | 14.0% |
| Airlock (Drex → Qwen on band) | 18.0% |

# Guard evaluation — openai/gpt-oss-120b

| Guard | Accuracy | Refusal recall | Precision | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|
| LLM (+keyword fallback) | 100.0% | 100.0% | 100.0% | 20 | 0 | 0 | 20 |
| Keywords only | 80.0% | 65.0% | 92.9% | 13 | 1 | 7 | 19 |

False refusals on the 90 benchmark questions: 0 


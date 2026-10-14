# Benchmark summary (execution accuracy)

| Model | Config | Split | Easy | Medium | Hard | Overall | Runs | Avg latency (s) | Avg tokens | Avg retries |
|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | baseline | dev | 95.0% | 95.0% | 85.0% | 91.7% | 1 | 3.5 | 1148 | 0.00 |
| openai/gpt-oss-120b | correct | dev | 95.0% | 100.0% | 85.0% | 93.3% | 1 | 6.6 | 1265 | 0.07 |
| openai/gpt-oss-120b | link | dev | 95.0% | 90.0% | 75.0% | 86.7% | 1 | 5.8 | 1189 | 0.00 |
| openai/gpt-oss-20b | baseline | dev | 90.0% | 100.0% | 80.0% | 90.0% | 1 | 6.7 | 1192 | 0.00 |
| openai/gpt-oss-20b | correct | dev | 90.0% | 100.0% | 90.0% | 93.3% | 1 | 7.4 | 1437 | 0.13 |
| openai/gpt-oss-20b | link | dev | 95.0% | 95.0% | 75.0% | 88.3% | 1 | 6.7 | 1247 | 0.00 |
| qwen/qwen3.8-27b | baseline | dev | 95.0% | 90.0% | 80.0% | 88.3% | 1 | 6.5 | 961 | 0.00 |
| qwen/qwen3.8-27b | correct | dev | 95.0% | 90.0% | 80.0% | 88.3% | 1 | 41.2 | 980 | 0.02 |
| qwen/qwen3.8-27b | link | dev | 95.0% | 100.0% | 85.0% | 93.3% | 1 | 5.0 | 809 | 0.00 |

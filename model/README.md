# model

Modal deployment of Muse Glimmer 30B as a decision model, plus the evaluation code.

## Setup

1. Copy `../.env.example` to `../.env` and fill in the keys.
2. Run `uv sync` in this folder.
3. Create the Modal secret: `uv run modal secret create glimmer-secrets --from-dotenv ../.env`.

All commands below run from `model/src/`.

## Files

| File | Purpose |
|---|---|
| `glimmer_image.py` | The GPU container image. `LOCAL_MODULES` must stay the last layer. |
| `prompts.py` | The question templates. A head is valid only for the template it was trained on. |
| `serve.py` | The decision API. `noul`, `choice`, `score` questions, head mode and zero-shot mode. |
| `client_demo.py` | A client for the API from a laptop. |
| `download_weights.py`, `download_mvtec.py` | Fill the Modal volumes `glimmer-weights` and `glimmer-data`. |
| `glimmer_decide.py` | The zero-shot benchmark on MVTec AD. Also dumps the hidden features. |
| `train_head.py` | Trains the logistic heads from the features. |
| `bench_decisions.py` | Benchmarks the OpenRouter decision models (Jev, d1-ultra, Elephant). |
| `bench_spark.py` | Benchmarks Muse Spark 1.3 as a JSON classifier. |
| `latency_race.py` | Spark against Glimmer on 20 held-out images, from a laptop. |
| `throughput.py`, `throughput2.py` | Images per second on one H100, with and without early exit. |
| `report.py` | Merges `../../results/decisions/*.jsonl` into the report and the reliability diagram. |

## Deploy the API

```
uv run modal deploy serve.py
```

The API is one H100 with a 10 minute idle timeout. The first call after idle takes about 50 s.

## Reproduce the benchmark

```
uv run modal run glimmer_decide.py --objects all     # Glimmer zero-shot + features
uv run python train_head.py --holdout 0.5             # heads for layers 13 and 52
uv run python bench_decisions.py --model typesafe/jev-1.14 --objects all
uv run python bench_spark.py --effort low --objects all
uv run python report.py
```

The results write to `../../results/`.

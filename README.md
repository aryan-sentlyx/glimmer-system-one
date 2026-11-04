# Glimmer System One

An open multimodal decision model on **Muse Glimmer 30B**. Send an image and typed questions. Get calibrated probabilities back in one forward pass.

Built for the Meta Global AI Developer Hackathon 2026, indie track, theme "Push the Frontier".

## Links

| | |
|---|---|
| Code | https://github.com/aryan-sentlyx/glimmer-system-one |
| Heads on Hugging Face | https://huggingface.co/aryan-sentlyx/glimmer-system-one-heads |
| Live demo | https://aryan-59489--glimmer-demo.us-east.modal.run |

## The problem

Vision language models answer production-line questions in seconds. Muse Spark 1.3 writes a median of 1,144 reasoning tokens for one inspection image and takes 8.0 s. A production line moves one part per second or faster.

## The idea

A decision model does not write text. It answers a typed question (`noul`, `choice`, `score`) with a probability that you read from the logits. Glimmer System One does this with Muse Glimmer 30B:

- **Zero-shot mode.** One forward pass, the logit of "yes" against "no", plus one temperature. Works on products the model never saw.
- **Head mode.** A logistic head on the hidden state of layer 52 (or layer 13 for early exit). Trained on half of the known products, tested on the other half.

## Results on MVTec AD, all 1,725 test images

| System | AUROC | Acc at 0.5 | ECE | Latency per image | Open |
|---|---|---|---|---|---|
| Glimmer head, known product, held-out half | 0.962 | 90.2% | 0.045 | 45 ms batched | yes |
| Glimmer layer 13 head, early exit | 0.954 | 88.3% | 0.034 | 21 ms batched | yes |
| Liquid d1-ultra | 0.929 | 83.2% | 0.147 | 0.46 s | no |
| TypeSafe Jev 1.14 | 0.917 | 85.2% | 0.125 | 0.31 s | no |
| Baseten Elephant 1 | 0.902 | 80.5% | 0.181 | 0.43 s | yes (MIT) |
| Glimmer zero-shot + temperature, unseen product | 0.882 | 81.4% | 0.040 | 45 ms batched | yes |
| Muse Spark 1.3, JSON, low reasoning | 0.873 | 83.1% | 0.097 | 3.9 s | no |
| Muse Spark 1.3, JSON, default reasoning | 0.872 | 82.6% | 0.101 | 8.0 s | no |

The full per-object table is in [`results/report.md`](results/report.md). The raw predictions are in `results/decisions/`.

## Repository layout

| Folder | Content |
|---|---|
| [`model/`](model/) | Modal deployment of Glimmer, the decision API, the benchmarks, the head training |
| [`results/`](results/) | Raw predictions (JSONL), the report, the head weights, the run logs |
| [`demo/`](demo/) | The judge-facing web demo: React frontend and FastAPI backend on Modal |
| [`video/`](video/) | The demo video, built with HyperFrames |
| [`release/`](release/) | The Hugging Face release of the heads: model card and upload script |
| [`docs/`](docs/) | Submission text, architecture, API reference, cost log |

## Quick start

See [`model/README.md`](model/README.md) to deploy the API and run the benchmarks. See [`demo/README.md`](demo/README.md) to run the web demo.

## Licenses

The code and the head weights are Apache 2.0. Muse Glimmer 30B is Apache 2.0. The MVTec AD dataset is CC BY-NC-SA 4.0, research use only. The dataset is not in this repository.

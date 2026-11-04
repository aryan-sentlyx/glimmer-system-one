# Architecture

Glimmer System One turns Muse Glimmer 30B into a decision model. The model does not write text. It answers typed questions with a probability that the code reads from one forward pass.

## The path of one request

1. **Request.** The client sends a state text, an optional image, an object noun, and a map of questions. Each question has a type: `noul`, `choice` or `score`. The shape follows the Decisions API of TypeSafe Jev.
2. **Image.** The server decodes the base64 image and resizes it so that the long side is 448 px.
3. **Prompts.** The server builds one prompt per yes/no decision. A `noul` question gives one prompt. A `choice` question gives one prompt per option. A `score` question gives one prompt that asks for one digit. A question with a head uses the exact template of the head from `model/src/prompts.py`; the server ignores the instructions of that question.
4. **One forward pass.** All prompts of the request go through Glimmer in one batch with left padding. The server reads the logits at the last position of each prompt. For a head it also keeps the hidden states of layers 13, 25, 37 and 52 at that position.
5. **Probabilities.**
   - `noul`, zero-shot: the log-odds of the "yes" tokens against the "no" tokens, divided by the temperature `T` plus the bias `b` from `results/head/temp_noul.json`.
   - `noul`, head: the hidden state of the layer of the head, standardized, then one logistic regression.
   - `choice`: the yes-probability of each option, then a softmax over the log-odds. With a `gate`, the option `good` takes `1 − P(noul)` and the other options share the rest.
   - `score`: a softmax over the digit tokens `0` to `N − 1`, then the expected level.
6. **Response.** One entry per question with the probability, the chosen option or the score, and the timing: the forward pass on the GPU and the total time on the server.

## The heads

A head is a `StandardScaler` and a `LogisticRegression` on the 6,656 floats of one hidden state. The features come from the template `inspect_defective_v1` on all 1,725 MVTec AD test images. The head was trained on a random half of each product and scored on the other half. The template name is stored inside the `.npz` file. A head and its template are one unit.

Two heads exist:

| Head | Layer | AUROC on the held-out half | ECE | Per image |
|---|---|---|---|---|
| `noul_defective_known_L52` | 52 of 52 | 0.962 | 0.045 | 45 ms batched |
| `noul_defective_known_L13` | 13 of 52 | 0.954 | 0.034 | 21 ms batched |

The layer 13 head makes an early exit possible: the forward pass stops after 13 layers and the head reads the hidden state there. The deployed server runs all 52 layers; the 21 ms number comes from a throughput measurement with the forward pass stopped at layer 13.

## Calibration

The zero-shot temperature was fitted leave-one-product-out on MVTec AD, so the zero-shot number in the results table is for a product the model never saw. The heads are calibrated by the logistic regression itself. On the held-out half, the expected calibration error of the layer 52 head is 0.045, against 0.101 for Muse Spark 1.3 with JSON output.

## Infrastructure

Everything runs on Modal.

| Part | Where | Notes |
|---|---|---|
| GPU API | app `glimmer-systemone`, class `SystemOne`, one H100 | `model/src/serve.py`. Idles out after 10 minutes. Cold start about 50 s. |
| Weights | volume `glimmer-weights` | Glimmer bf16, 59.6 GB |
| Heads and data | volume `glimmer-data` | the heads, the temperature, the MVTec AD parquet files |
| Demo backend | app `glimmer-demo`, CPU | `demo/backend/app.py`. FastAPI. Calls the GPU class by name. Serves the built frontend. |
| Demo frontend | `demo/frontend/` | Vite, React 19, TypeScript, Tailwind v4 |

The GPU image is CUDA 12.8, torch 2.9.0 and transformers from git main (Glimmer needs 5.15 or later). The GPU URL never reaches the browser.

## Throughput

On one H100 at 448 px: 6 prompts per image in 289 ms; 1 prompt at full depth in 45 ms per image, batched; 1 prompt with the exit at layer 13 in 21 ms per image, batched (48 images per second).

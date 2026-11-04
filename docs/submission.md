# Submission

Text for the hackathon submission form. Meta Global AI Developer Hackathon 2026, indie developer track, theme "Push the Frontier".

## Project name

Glimmer System One

## One line

An open decision model for the Muse family: Muse Glimmer 30B with the text generation removed. One forward pass, a calibrated probability per question, 45 ms per image.

## Links

| | |
|---|---|
| Code | https://github.com/aryan-sentlyx/glimmer-system-one |
| Heads on Hugging Face | https://huggingface.co/aryan-sentlyx/glimmer-system-one-heads |
| Live demo | https://aryan-59489--glimmer-demo.us-east.modal.run |
| Video | the file `video/renders/glimmer-system-one.mp4`, 3 minutes |

## Description

This year Meta released the Muse family. Muse Spark is the reasoning model behind the API. Muse Glimmer is the open 30B multimodal model. What the family does not have is a System One model: a model that does not write an answer but decides, and returns a probability in one pass. TypeSafe Jev made that category popular in September. OpenAI followed with the Decisions API. Microsoft followed with Decision-1. Both are closed.

Glimmer System One fills that slot. It takes Muse Glimmer, the open 30B model, and removes the part that writes text. You give it a picture, a short state text, and your questions. For each question it gives back one number: how sure it is. Three kinds of questions work: is this true (`noul`), which one of these (`choice`), how much on a scale (`score`). The request shape follows the Decisions API of TypeSafe Jev, so the same client code works with both.

Because the weights are open, the model can stop at layer 13 of 52 and still answer, in 21 ms per image.

## Why it matters

A production line moves one part per second or faster. A normal vision language model first writes an explanation. Muse Spark 1.3 writes a median of 1,144 reasoning tokens for one inspection image and takes 8.0 s. The part is long gone. Glimmer System One skips the explanation and answers in 45 ms.

It works without a picture too. It can stop an AI agent before a dangerous command, or route a support ticket and rate how urgent it is.

## Results

All 1,725 MVTec AD test images, 15 products, question "does this part have a visible defect".

| System | AUROC | Acc at 0.5 | ECE | Per image | Open |
|---|---|---|---|---|---|
| Glimmer head, known product, held-out half | 0.962 | 90.2% | 0.045 | 45 ms batched | yes |
| Glimmer layer 13 head, early exit | 0.954 | 88.3% | 0.034 | 21 ms batched | yes |
| Liquid d1-ultra | 0.929 | 83.2% | 0.147 | 0.46 s | no |
| TypeSafe Jev 1.14 | 0.917 | 85.2% | 0.125 | 0.31 s | no |
| Baseten Elephant 1 | 0.902 | 80.5% | 0.181 | 0.43 s | yes (MIT) |
| Glimmer zero-shot + temperature, unseen product | 0.882 | 81.4% | 0.040 | 45 ms batched | yes |
| Muse Spark 1.3, JSON, low reasoning | 0.873 | 83.1% | 0.097 | 3.9 s | no |
| Muse Spark 1.3, JSON, default reasoning | 0.872 | 82.6% | 0.101 | 8.0 s | no |

The story is speed and calibration. When Glimmer System One says seventy percent, about seventy percent of those parts are defective. That is what makes a threshold mean something. Every closed decision model in the table is worse calibrated.

## How it was built

- **Model.** Muse Glimmer 30B in bf16 on one H100 on Modal, served with transformers. One batched forward pass per request. The logits of "yes" against "no" at the answer position give the zero-shot probability, with one fitted temperature. A logistic head on the hidden state of layer 52 (or 13) gives the head probability. The heads were trained on half of the MVTec AD test images and scored on the other half.
- **Benchmark.** All 1,725 images through Glimmer (zero-shot and head), Muse Spark 1.3 (JSON output, two reasoning settings), and three decision models on OpenRouter. AUROC, accuracy, expected calibration error, Brier score, latency and cost per run.
- **Demo.** A FastAPI backend on Modal and a React page. Drop an image, write the state, type the questions as plain lines, press Run. Six prompts, one pass, every answer as a probability. The GPU idles out after ten minutes.
- **Release.** The code under Apache 2.0 on GitHub. The heads, the temperature and the split under Apache 2.0 on Hugging Face.

## What was hard

- Glimmer needs transformers from git main. The vision tower and the chat template took a day to get right.
- A head is valid only for the exact prompt its features came from. The server stores the template name inside the head file and ignores the question text for a head question.
- Calibration on text-only questions. The temperature was fitted on inspection images and gives soft answers on text. The API has a `raw` switch.
- The budget. The H100 costs about $4 per hour, so the container idles out and the page warms it on load.

## What is next

- The early exit in the server, so the layer 13 head answers in 21 ms in production.
- More heads: one per question, trained from a few hundred labeled images with one script.
- A webcam client for a real line.

## Team

Aryan Srivastava, machine learning engineer, India. Indie developer track.

---
license: apache-2.0
base_model: meta-models/Muse-Glimmer-30B
base_model_relation: adapter
language:
- en
tags:
- decision-model
- system-one
- visual-inspection
- anomaly-detection
- calibration
- muse-glimmer
- logistic-regression
datasets:
- TheoM55/mvtec_all_objects_split
pipeline_tag: image-classification
library_name: transformers
---

# Glimmer System One heads

Glimmer System One is an open multimodal decision model on [Muse Glimmer 30B](https://huggingface.co/meta-models/Muse-Glimmer-30B). It takes an image, a state text and typed questions. It returns a calibrated probability per question in one forward pass. It does not write text.

This repository holds the small trained parts. The base model stays at `meta-models/Muse-Glimmer-30B`.

- Two logistic heads on the hidden state of Glimmer, for the question "does this part have a visible manufacturing defect".
- The temperature of the zero-shot mode.
- The train and test split of the heads.

The code, the benchmark, the demo and the video are on GitHub: [aryan-sentlyx/glimmer-system-one](https://github.com/aryan-sentlyx/glimmer-system-one). The live demo is at [aryan-59489--glimmer-demo.us-east.modal.run](https://aryan-59489--glimmer-demo.us-east.modal.run).

## Files

| File | Content |
|---|---|
| `noul_defective_known_L52.npz` | The head on layer 52 (the last layer). Keys: `layer`, `mean`, `scale`, `coef`, `intercept`, `template`. |
| `noul_defective_known_L13.npz` | The head on layer 13, for an early exit after 13 of the 52 layers. Same keys. |
| `temp_noul.json` | The zero-shot calibration: `T` (temperature) and `b` (bias) on the log-odds of "yes" against "no". |
| `known_split.json` | The split: the indices of the held-out test images per product, and the held-out metrics of the layer 52 head. |
| `results.json` | An earlier sweep of the heads on layers 13, 25, 37 and 52: leave-one-product-out and 5-fold scores. |
| `reliability.png` | The reliability diagram of the systems in the benchmark. |

Each head is one standardizer and one logistic regression on a vector of 6,656 floats. A head file is 135 KB.

## How a head works

1. Build the prompt with the exact template of the head. The template name is in the file, under the key `template`. The template `inspect_defective_v1` is:
   - system: `You are a visual inspection system on a production line. Answer with one word. Reasoning strength: low.`
   - user: the image, then `Does this {name} have a visible manufacturing defect? Answer yes or no.` with `{name}` the object noun, for example `bottle`.
2. Resize the image so that the long side is 448 px.
3. Run one forward pass of Glimmer with `output_hidden_states=True`.
4. Take the hidden state of layer `layer` at the last position. With left padding, the last position is the answer position.
5. Standardize: `x = (h - mean) / scale`.
6. The probability of a defect is `sigmoid(x @ coef + intercept)`.

A head and its template are one unit. A different prompt gives a different hidden state and the head is not valid for it.

## Use

```python
import numpy as np, torch
from PIL import Image
from huggingface_hub import hf_hub_download
from transformers import AutoProcessor, AutoModelForImageTextToText

REPO = "aryan-sentlyx/glimmer-system-one-heads"
head = np.load(hf_hub_download(REPO, "noul_defective_known_L52.npz"))
L = int(head["layer"])

SYSTEM = ("You are a visual inspection system on a production line. "
          "Answer with one word. Reasoning strength: low.")
QUESTION = "Does this {name} have a visible manufacturing defect? Answer yes or no."

processor = AutoProcessor.from_pretrained("meta-models/Muse-Glimmer-30B")
processor.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(
    "meta-models/Muse-Glimmer-30B", dtype=torch.bfloat16, device_map="cuda").eval()

image = Image.open("bottle.png").convert("RGB")
image.thumbnail((448, 448))
messages = [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": [{"type": "image"},
                                 {"type": "text", "text": QUESTION.format(name="bottle")}]},
]
text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
text = text + " to=user<|message|>"
inputs = processor(text=[text], images=[image], return_tensors="pt").to("cuda")

with torch.no_grad():
    out = model(**inputs, output_hidden_states=True)

h = out.hidden_states[L][0, -1].float().cpu().numpy()
x = (h - head["mean"]) / head["scale"]
p_defect = float(1 / (1 + np.exp(-(x @ head["coef"] + head["intercept"]))))
print(f"P(defect) = {p_defect:.3f}")
```

The zero-shot mode needs no head. It reads the logits at the last position, sums the probability of the "yes" tokens and of the "no" tokens, and applies the temperature:

```python
import json, math
tok = processor.tokenizer
yes_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["yes", " yes", "Yes", " Yes"]})
no_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["no", " no", "No", " No"]})
row = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
ly, ln = torch.logsumexp(row[yes_ids], 0), torch.logsumexp(row[no_ids], 0)
p = torch.softmax(torch.stack([ly, ln]), 0)[0].item()

temp = json.load(open(hf_hub_download(REPO, "temp_noul.json")))
p_cal = 1 / (1 + math.exp(-(math.log(p / (1 - p)) / temp["T"] + temp["b"])))
```

The early exit with the layer 13 head reads `out.hidden_states[13]`. The example above still runs all 52 layers. For the speed gain, stop the forward pass after layer 13. The server in the GitHub repository runs the full depth; the 21 ms number comes from a benchmark with the truncated model.

## Results

All 1,725 test images of MVTec AD, 15 products, one question: does this part have a visible defect. The heads were trained on half of the test images of each product and scored on the other half (866 images). The seed and the indices are in `known_split.json`.

| System | AUROC | Accuracy at 0.5 | ECE | Per image |
|---|---|---|---|---|
| Head, layer 52, held-out half | 0.962 | 90.2% | 0.045 | 45 ms batched |
| Head, layer 13, early exit, held-out half | 0.954 | 88.3% | 0.034 | 21 ms batched |
| Zero-shot + temperature, all images | 0.882 | 81.4% | 0.040 | 45 ms batched |
| Muse Spark 1.3, JSON output, default reasoning | 0.872 | 82.6% | 0.101 | 8.0 s |

Latency is on one H100 at 448 px, batched. The comparison with the closed decision models (Liquid d1-ultra, TypeSafe Jev 1.14, Baseten Elephant 1) and the per-product table are in the GitHub repository, in `results/report.md`.

The zero-shot temperature was fitted leave-one-product-out, so its number is for a product the model never saw.

## Limits

- The heads answer one question on one domain: a visible manufacturing defect on a part of one of the 15 MVTec AD products. They are not a general defect detector.
- A head is valid only with its template, the object noun, an image, left padding and the 448 px resize.
- The heads saw half of the MVTec AD test images of each product. The held-out numbers are for the other half of the same products. On a new product, use the zero-shot mode.
- Hard products for every system in the benchmark: pill, metal_nut, screw, transistor.
- The zero-shot temperature was fitted on inspection images. On text-only questions it gives soft probabilities.
- The browser demo resizes with the canvas and the Python client with Pillow. The same image gives slightly different probabilities. The verdict is the same.

## Training

The features are the hidden states of Glimmer at the answer position for the template above, on all 1,725 MVTec AD test images at 448 px. Each head is a `StandardScaler` and a `LogisticRegression` from scikit-learn, trained on a random half of each product (seed 0). The script is `model/src/train_head.py` in the GitHub repository.

## License and data

The heads, the temperature and the split are Apache 2.0. Muse Glimmer 30B is Apache 2.0, by Meta. The MVTec AD dataset is CC BY-NC-SA 4.0, for research use only. No image of the dataset is in this repository.

Built for the Meta Global AI Developer Hackathon 2026, indie developer track, by Aryan Srivastava.

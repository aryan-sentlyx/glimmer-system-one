# backend

FastAPI app on Modal, app name `glimmer-demo`, one CPU container. It calls the GPU class `SystemOne` of the app `glimmer-systemone` by name. The GPU URL and the heads never reach the browser.

| Route | What it does |
|---|---|
| `GET /api/model` | The model card from `model_card.json`. |
| `GET /api/examples` | The presets from `examples.json`. Images are under `/examples/`. |
| `GET /api/health` | `{"gpu": "cold" or "warming" or "warm"}`. |
| `POST /api/warm` | Wakes the GPU container and returns at once. The page calls it on load. |
| `POST /api/decide` | Resizes the image to 448 px, forwards the request, returns the answers with the round trip time. |
| `/` | The built frontend, or a placeholder page. |

Guards: 20 calls per IP per minute, 120 in total. Images up to 4 MB. Up to 24 prompts per call. An access code is optional: set `DEMO_ACCESS_CODE` in the root `.env` before deploy, and the page sends it in the header `X-Access-Code`. It is not set now.

Request body of `/api/decide`:

```json
{"state": "text", "image": "data:image/png;base64,...", "object": "bottle",
 "questions": {
   "defective": {"type": "noul", "instructions": "The part has a visible defect.", "head": "noul_defective_known_L52"},
   "defect_type": {"type": "choice", "instructions": "Which defect?", "gate": "defective",
                   "criteria": {"good": null, "broken_large": null, "contamination": null}},
   "severity": {"type": "score", "instructions": "How severe?", "criteria": ["none", "minor", "moderate", "severe"]}}}
```

`image` is optional. Without an image, a `head` falls back to zero-shot mode.

Commands, from this folder:

```
uv sync
uv run modal serve app.py     # dev, hot reload
uv run modal deploy app.py    # deploy
```

The example images are from MVTec AD (CC BY-NC-SA 4.0, research use), held-out images that the head never saw.

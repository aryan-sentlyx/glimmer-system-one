# API

Two APIs exist. Both take the same request body.

1. The GPU API, `POST https://aryan-59489--glimmer-decide.us-east.modal.run`. Source: `model/src/serve.py`. Takes a plain base64 image.
2. The demo backend, `POST https://aryan-59489--glimmer-demo.us-east.modal.run/api/decide`. Source: `demo/backend/app.py`. Takes a base64 image or a data URL, resizes it, forwards it to the GPU API, and adds the round trip time. Has a rate limit.

See `demo/backend/README.md` for the request body and the response.

Response fields: `answers` (one entry per question with `noul`, or `choice` + `probabilities`, or `score` + `probabilities` + `legend`), `input` (image present, state length), `usage` (prompts in the batch, tokens), `timing` (`forward_s` on the GPU, `total_s` on the server, `round_trip_s` from the backend).

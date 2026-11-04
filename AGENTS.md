# AGENTS.md

Context for any coding agent or new contributor who works in this repository. Read this first. The README files in each folder hold the details for that folder.

## What this project is

**Glimmer System One** is an open multimodal decision model built on Muse Glimmer 30B. It takes an image, a state text, and typed questions. It returns a calibrated probability per question, in one forward pass. It does not write text.

The entry is for the Meta Global AI Developer Hackathon 2026 (Meta and Cerebral Valley), indie developer track, theme "Push the Frontier". The submission deadline is **November 4, 2026, 9:00 PM ET**. Judging runs November 4 to 8. The submission needs the code and a demo video.

The pitch in one line: current vision language models are too slow for a production line. Muse Spark 1.3 writes a median of 1,144 reasoning tokens for one inspection image and takes 8.0 s. Glimmer System One answers in 45 ms per image batched, or 21 ms with an early exit, with better accuracy and real calibration.

## The three question types

The request shape follows the Decisions API of TypeSafe Jev, so the same client code works with both.

| Type | Input | Output | How |
|---|---|---|---|
| `noul` | a statement | P(true) | logit of "yes" against "no" at the answer position, then one temperature |
| `choice` | a question and a list of options | a probability per option | one yes/no prompt per option in the same batch, softmax over the log-odds |
| `score` | a question and an ordered list of levels | the expected level and the distribution | softmax over the digit tokens 0 to N |

Two modes for `noul`:
- **Zero-shot + temperature.** Any image, any question. The temperature was fitted leave-one-product-out on MVTec AD. It lives in `results/head/temp_noul.json`.
- **Head.** A logistic regression on the hidden state of layer 52 (or 13) at the answer position, trained on half of the known products. The head is valid only for the exact prompt template it was trained on. The template name is stored inside the `.npz` file. The templates live in `model/src/prompts.py`. Never change a template without retraining the head.

A `choice` question can carry `"gate": "<noul name>"`. Then P("good") = 1 − P(noul) and the other options share the rest.

## Repository layout

```
.
├── AGENTS.md            this file
├── README.md            results table, layout, licenses
├── LICENSE              Apache 2.0
├── .env.example         the keys the code needs; copy to .env (gitignored)
├── model/               Modal deployment of Glimmer, the decision API, the benchmarks, the head training (uv project)
│   └── src/             flat Python modules, run from this folder
├── results/             committed: raw predictions (JSONL), report.md, reliability.png, head weights, run logs
├── demo/
│   ├── backend/         FastAPI on Modal, CPU only, serves the API and the built frontend (uv project)
│   └── frontend/        Vite, React 19, TypeScript, Tailwind v4
├── video/               the demo video, a HyperFrames project (HTML rendered to video)
├── release/             the Hugging Face release of the heads (stub)
├── docs/                submission text, architecture, API reference, cost log (partly stubs)
└── data/                gitignored: MVTec AD parquet, features, sample images (146 MB)
```

## Releases

| Thing | Where | Account |
|---|---|---|
| Code | `https://github.com/aryan-sentlyx/glimmer-system-one`, public, Apache 2.0 | GitHub `aryan-sentlyx`, SSH alias `github-sentlyx`, `gh` active account. The local git identity of this repo is the noreply address of that account. |
| Heads | `https://huggingface.co/aryan-sentlyx/glimmer-system-one-heads`, model repo, Apache 2.0 | Hugging Face `aryan-sentlyx`. `release/upload.py` reads `HF_WRITE_TOKEN` from `.env`. The `HF_TOKEN` in `.env` belongs to another account and is read only. |

## Infrastructure

Everything runs on Modal, workspace `aryan-59489`.

| Thing | Name | Notes |
|---|---|---|
| GPU app | `glimmer-systemone` | class `SystemOne`, one H100, `max_containers=1`, idles out after 600 s, cold start about 50 s |
| GPU web endpoint | `POST https://aryan-59489--glimmer-decide.us-east.modal.run` | plain base64 image |
| GPU health | `GET https://aryan-59489--glimmer-health.us-east.modal.run` | |
| Demo app | `glimmer-demo` | `https://aryan-59489--glimmer-demo.us-east.modal.run`, serves `demo/frontend/dist` and `/api/*` |
| Volume | `glimmer-weights` | Glimmer bf16 weights, 59.6 GB, at `/weights/meta-models/Muse-Glimmer-30B` |
| Volume | `glimmer-data` | `/data/mvtec_ad/data/*.parquet`, `/data/features/`, `/data/head/` |
| Secret | `glimmer-secrets` | `MODEL_API_KEY`, `HF_TOKEN`, `OPENROUTER_API_KEY`, created from `.env` |

The demo backend calls the GPU class by name with `modal.Cls.from_name("glimmer-systemone", "SystemOne")` and the methods `decide_rpc` and `warm`. The GPU URL never reaches the browser.

The GPU image is in `model/src/glimmer_image.py`: CUDA 12.8, torch 2.9.0, transformers from git main (Glimmer needs 5.15+), torchvision 0.24.0. `LOCAL_MODULES` is mounted with `add_local_python_source` and **must stay the last layer** of the image. A pip layer after it fails.

## Commands

All Python runs with `uv`. The `model` and `demo/backend` folders each have their own `pyproject.toml` and `.venv`.

```
# first time
cp .env.example .env            # fill in the keys
cd model && uv sync
uv run modal secret create glimmer-secrets --from-dotenv ../.env --force

# GPU API
cd model/src && uv run modal deploy serve.py

# benchmarks, from model/src (they write to ../../results/)
uv run modal run glimmer_decide.py --objects all      # Glimmer zero-shot + feature dump
uv run python train_head.py --holdout 0.5             # heads for layers 13 and 52
uv run python bench_decisions.py --model typesafe/jev-1.14 --objects all
uv run python bench_spark.py --effort low --objects all
uv run python report.py                               # report.md + reliability.png

# demo
cd demo/frontend && npm install && npm run dev        # dev server, proxies /api to the live backend
cd demo/frontend && npm run build                     # then:
cd demo/backend && uv run modal deploy app.py         # bundles frontend/dist at deploy time

# video
cd video && npm run dev | npm run check | npm run render
```

`modal app stop <name>` needs `--yes` when it runs without a terminal.

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

Other facts that the video and the docs use:
- Throughput on one H100 at 448 px: 6 prompts per image 289 ms; 1 prompt full depth 45 ms batched; 1 prompt with exit at layer 13, 21 ms batched (48 images/s).
- Spark with default reasoning: median 1,144 reasoning tokens, p50 8.0 s, 8 failed requests out of 1,725. More reasoning did not raise its AUROC.
- The defect type question is weak for every system: 47% to 61% accuracy. It is a secondary point, not the headline.
- Hard products for every system: pill, metal_nut, screw, transistor.
- The raw predictions are in `results/decisions/*.jsonl`, one line per image per system. Files with `_bottle` are early smoke runs on one product.

The story is **speed and calibration**, not raw accuracy. Spark is accurate on the easy products.

## Rules for this repository

1. **Secrets.** Keys live only in `.env`, which is gitignored. Never print a key value, not even a part of it. Print names and presence only. Never commit `.env`.
2. **Spend.** The H100 costs about $4 per hour. The container idles out after 10 minutes. Every call to the demo or the GPU API wakes it. Do not add `min_containers` or keep-warm loops. Do not use the Muse API credits for hosting; they are for labels and comparisons only. State of the budgets on November 1, 2026: Muse about $12 of $150 used, OpenRouter $0.45, Modal about $6 of $100.
3. **Held-out images only.** Any demo of the head must use images from the held-out half. The indices are in `results/head/known_split.json`. The four example images in `demo/backend/examples/` are held-out.
4. **Templates.** A head and its prompt template are one unit. See above.
5. **Data license.** MVTec AD is CC BY-NC-SA 4.0, research use only. It is not committed. Four sample images are in the demo with attribution. Do not add more.
6. **Git.** The repository has no commits yet. Do not commit or push unless the owner asks.
7. **Scope.** The plan is fixed: the decision model, the benchmark, the demo page, the video, the release. A full diffusion conversion of Glimmer was ruled out as infeasible in the time and budget. Do not reopen it.
8. **Paths.** The scripts in `model/src/` use relative paths from that folder: `../../results/` and `../../data/`. Run them from `model/src/`.

## The demo page

The playground has two boxes and a Run button. Everything else sits in an "Advanced" fold. Keep it that way: a new user must be able to use the page without the words noul, head, gate, or template.

- **The example strip.** Seven cards at the top, read from `demo/backend/examples.json`. A click fills both boxes and highlights the card. The page does not run the example. The Run button pulses until the user presses it.
- **Box 1, context.** One card holds the optional image (drop, paste, browse) and the state text.
- **Box 2, questions.** One question per line. The parser in `demo/frontend/src/form.ts` reads each line:
  - a statement is a `noul`,
  - options in brackets `[a, b, c]` make a `choice` (also split on `|`),
  - levels with `<` in brackets `[none < minor < severe]` make a `score`.
  A list under the box shows each parsed line with its type tag. A click on the tag of a bracketed line switches choice and score.
- **Automatic settings.** A noul line that contains the word "defect" gets the head `noul_defective_known_L52` when an image is present. A choice with a `good` option is gated by the first noul that uses a head. The server ignores the instructions of a head question and uses the exact template, so the line text does not break the head.
- **Overrides.** Settings the parser cannot read (JSON key, forced type, head, raw, gate) live in `form.overrides`, keyed by the trimmed line. An edit of a line drops its overrides. A loaded example or an applied JSON body sets overrides for every line, so it round-trips exactly.
- **The Advanced fold** holds the object noun, the per-question keys, heads, raw, gates, and the request JSON editor with "Apply to the form". The API tab shows the same body as curl and Python.
- **The output pane** shows the question text as the title and the JSON key under it, the threshold slider for noul answers, and the timing line.
- Each preset in `examples.json` carries an `answers` field with a response from November 4. The page does not read it. It is kept for reference and for the video.

## The video

The film is a HyperFrames project in `video/`. HyperFrames renders HTML to MP4 by seeking a paused GSAP timeline frame by frame. Read `video/AGENTS.md` and run the `/hyperframes` skill before you edit a scene.

- **Length and shape.** 179.9 s, 1920 x 1080, 30 fps. Eight scenes in the order of the script, plus one presenter overlay that spans the whole film. The presenter is a stick figure with the headshot of Aryan as the head (`video/assets/headshot.png`, a cut-out with alpha). Aryan narrates. The screen never repeats a spoken sentence word for word.
- **The script.** `video/SCRIPT.docx` is the source of truth (a copy in `SCRIPT.final.docx`, a Markdown export in `SCRIPT.md`). 425 words after the cut of November 5 (the cut is in `SCRIPT.md`; the `.docx` still has the 476-word text). The ElevenLabs read is 178 s of speech. `STORYLINES.md` and `SPEC.md` are the earlier 96 s plan and are superseded by the script; the LOOK and BANNED lines of `SPEC.md` still apply.
- **Files.** `index.html` is the root with the eight hosts. The scenes are in `compositions/`: `intro` (0–19.9 s), `family` (19.9–55.2), `built` (55.2–87.2), `cases` (87.2–119.5), `compare` (119.5–153.9), `demo` (153.9–171.4), `end` (171.4–179.9), and `presenter` (0–179.9, z-index 5). The scene starts come from `uv run video/voice/generate_voice.py timeline --write`, which also rewrites the eight `<audio>` clips. The inner blocks of each scene carry their own `data-start` and `data-duration` windows; move them with the beats. Each scene file holds its own `@font-face` lines for IBM Plex Sans (variable), Mono and Sans Condensed from `assets/fonts/`.
- **The presenter rig** (`compositions/presenter.html`). One SVG, parts `#pr-head`, `#pr-armL`, `#pr-armR`, `#pr-legL`, `#pr-legR`, with `svgOrigin` at the joints. Helpers: `moveTo(at, x, y, scale, dur)`, `point(at, angle, hold)`, `walk(at, dur)`, `ink(at, colour)`. A positive `point` angle swings the arm to the left, a negative one to the right. The figure stands at bottom-left in the light scenes, bottom-right in the compare and demo scenes, at the end of the belt in the cases scene, and large in the intro and the end card. Light scenes use ink `#1c1a17`, dark scenes `#ece9e4`.
- **The voice.** The tools are in `video/voice/`. `RECORD.md` is the passage Aryan read for the ElevenLabs instant clone. `lines.json` holds the narration as the TTS speaks it, one entry per section with its scene, numbers spelled out ("zero point nine six two", "A U rock"). `generate_voice.py` runs with `uv run video/voice/generate_voice.py <cmd>` and reads the keys from the root `.env`: `voices` lists the account, `clone` makes a clone from `assets/voice/sample/`, `generate [--only id,id]` makes one MP3 per line with `eleven_v4` and writes `assets/voice/timing.json` with word timestamps, `trim` cuts the end silence of the files, and `timeline [--write]` prints the scene times and patches the hosts and the `<audio>` clips in `index.html` (0.4 s lead before a scene, 0.4 s gap between lines, 2.9 s hold on the end card). The clips sit on track 3 at volume 1. A changed line needs `generate --only`, `trim`, `timeline --write`, and a retime of the scene and of the presenter cues after it.
- **Look.** Two worlds: light `#e9e6e0` with ink `#1c1a17` (intro, family, cases, compare) and the demo's dark `#1c1a17` with ink `#ece9e4` (built, demo, end). The accent is the demo's amber `#f0b429`. No glow, no gradients, no logo in a corner.
- **Real things.** `assets/demo-full.png` is a capture of the live demo page. The output pane and the two boxes in the demo scene are rebuilt at 1.6x with the real labels and the numbers of a live run on November 4 (1.0% defective, good 99.0%, severity 0.82 / 3, forward 378 ms for 6 prompts). `assets/reliability.json` holds 10-bin reliability data for the head and for Spark on the same 866 held-out images, computed from `results/head/` and `results/decisions/`; the head reproduces AUROC 0.962, ECE 0.045, and Spark gives 0.863, 0.110 on those images. The four bottle photos are the held-out demo examples. The results table uses the numbers of the README. The belt, the factory hall, the locks and the mark are drawn in code.
- **Commands.** From `video/`: `npx hyperframes@0.8.225 check --json` (the gate, passes with one harmless warning about repeated bottle images), `npx hyperframes@0.8.225 snapshot --at <s,...>` (look at frames), `npx hyperframes@0.8.225 preview --background` (Studio at http://127.0.0.1:3002/#project/video; stop with `preview --stop`), `npm run render` (MP4).
- **Verified claims in the script** (sources in the table at the end of `SCRIPT.docx`): Muse Spark is the proprietary reasoning model; Muse Glimmer 30B is open under Apache 2.0, released August 2026; Muse Spark Open came October 15, 2026; Muse Code, Image and Video exist. TypeSafe Jev was released September 15, 2026, closed, text only. The OpenAI Decisions API was announced at DevDay on September 29, 2026, on GPT-6 Luna, takes text or images, public beta October 6; OpenAI did not document a probability output. Microsoft-Decision-1 came October 9, 2026, returns a calibrated probability per option, closed, in Microsoft Foundry and on OpenRouter. The claim "no open decision model takes images" is false (Baseten elephant-1, Cloudflare Clef, Perplexity pplx-decider, H2O-Lightning-4B, Mapika decider-31b take images) and was removed from the script.

## State of the work, November 5, 2026

Done:
- GPU API deployed, version `0.4-text`: image optional, text-only questions work, `decide_rpc` and `warm` for the backend.
- All benchmarks run. Report and reliability diagram written.
- Demo backend and frontend deployed and tested on the live URL. Seven presets: four held-out bottles with the head, one zero-shot image, two text-only cases (an agent safety gate, a support ticket).
- November 4, morning: the playground was rebuilt as the two-box page described above. The Examples tab is gone; four tabs remain: Playground, Benchmark, API, Model card. Tested in the browser on the live URL, with one live run.
- November 4, afternoon (IST), the video session:
  - The script was written with Aryan, in his order: who I am, push the frontier, the Muse family and the gap, what I built, use cases, how it compares, the demo page, close. It is in `video/SCRIPT.docx`. Sections 4 and 5 were rewritten in plain words at his request.
  - The claims about the Muse family and about the OpenAI and Microsoft decision models were verified on the web (see "The video" above).
  - All eight scenes and the presenter rig were built, checked (no errors) and snapshotted frame by frame. Overlaps between the presenter and the content were fixed.
  - Assets collected: the headshot, the four bottle photos, the demo capture, the brand mark, the IBM Plex fonts, the reliability bins.
  - Nano Banana (Gemini image generation) returned a 402 credits error, so no generated plates were used. The backdrops are drawn in code.
- November 5, night (IST), the voice session:
  - Aryan made an instant voice clone in ElevenLabs, named "Aryan Srivastava", from the passage in `video/voice/RECORD.md`. The keys `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are in `.env`.
  - The narration was made with `eleven_v4` by `video/voice/generate_voice.py`. The first read was 194.6 s of speech, so the script was cut by about 50 words (in `lines.json` and `SCRIPT.md`; the `.docx` still has the 476-word text). The `speed` setting of ElevenLabs has no effect on `eleven_v4`. The model varies by about 1 s between takes of one line; the longest sections were made again and the shortest takes kept. The end silence of every file was trimmed to 0.1 s.
  - `timeline --write` placed the eight `<audio>` clips in `index.html` and moved the scene hosts. The eight scene timelines and the inner `data-start` windows were retimed by hand to the word timestamps in `video/assets/voice/timing.json`. The film is 179.93 s.
  - The headshot was cut below the jaw with a soft curve, so the neck and the collar no longer show inside the circle clip of the presenter. The original is not in the repository.
  - `check` passes with no errors (one lint warning about the repeated bottle images, craft warnings about small type). 44 frames were looked at. The film was rendered twice; the current file is `video/renders/glimmer-system-one.mp4` (gitignored): 1920 x 1080, 30 fps, H.264 at delivery quality, AAC 48 kHz, 2 min 59.9 s, 19.1 MB.

- November 5, the release session:
  - Baseten Elephant 1 is open (MIT, weights on huggingface.co/baselabs/elephant-1). The row was corrected in the README, in this file and in the compare scene of the video.
  - `release/MODEL_CARD.md` and `release/upload.py` written. `docs/architecture.md` and `docs/submission.md` written.
  - The end card of the video names `hf.co/aryan-sentlyx/glimmer-system-one-heads`.
  - The hyperframes caches (`video/.hyperframes/`, `.thumbnails/`, `.waveform-cache/`) are gitignored.

Open, in the suggested order:
1. **The video, last steps.** (a) Aryan watches the MP4 and names the changes. After a change: `check`, `snapshot`, then `npm run render` (about 65 s). A changed line of narration needs `generate --only <id>`, `trim`, `timeline --write`, and a retime of that scene and of the presenter cues after it. (b) Optional sound effects from the free bundled set (`npx hyperframes media-use resolve --type sfx --local-only`): the belt stop, one stamp per bottle, the click on Run. (c) Stop the preview with `npx hyperframes@0.8.225 preview --stop` from `video/` after the review.
2. Optional: an early-exit "fast mode" in `serve.py` (the layer 13 head is loaded, but the server runs all 52 layers).
3. Parked: a custom domain through a Cloudflare Worker proxy; a webcam client; a second scene for a computer-use safety gate.

## Known quirks

- The zero-shot temperature was fitted on inspection images. On text-only questions it gives soft answers, for example 44% for a clear refund request. `"raw": true` skips it.
- The browser resizes images with the canvas, the Python client with Pillow. The head gives slightly different numbers for the same image (1.0% against 0.04% for a good bottle). The verdict is the same.
- A redeploy of the demo backend resets its in-memory GPU state to "cold" until the next call or warm.
- The first call after idle takes about 50 s. The page calls `/api/warm` on load and polls `/api/health` until warm.
- A choice option that contains a comma, or a question text that ends in brackets, does not round-trip through the questions box. The bracket is the only syntax. The JSON editor in the Advanced fold still accepts any body.
- After a deploy of the demo backend the browser can keep the old `index.html` for a while. A hard reload shows the new build.

## External references

- Muse Glimmer 30B: https://huggingface.co/meta-models/Muse-Glimmer-30B (Apache 2.0, 30B dense, 52 layers, hidden 6656, 1.8B vision encoder, class `MuseGlimmerForConditionalGeneration`)
- Meta Model API (Muse Spark 1.3): `https://api.meta.ai/v1`, OpenAI-compatible. Cookbook: https://github.com/meta-models/meta-model-cookbook
- TypeSafe Jev 1.14 on OpenRouter: `POST https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.14`
- MVTec AD on Hugging Face: `TheoM55/mvtec_all_objects_split`
- Modal docs: https://modal.com/docs

"""Backend of the Glimmer System One demo. One Modal app, CPU only.

Routes:
  GET  /api/model     the model card (model_card.json)
  GET  /api/examples  the built-in examples (examples.json), images under /examples/
  GET  /api/health    {"gpu": "cold" | "warming" | "warm"}
  POST /api/warm      wakes the GPU container, returns at once
  POST /api/decide    forwards the request to the GPU class SystemOne of the app glimmer-systemone
  /                   the built frontend (../frontend/dist), or a placeholder page

Guards: an optional access code (header X-Access-Code, env DEMO_ACCESS_CODE, read from ../../.env at deploy),
a rate limit per IP, a size limit on the image, a limit on the number of prompts per call.

Deploy: cd demo/backend && uv run modal deploy app.py
Dev:    cd demo/backend && uv run modal serve app.py
"""
import os
from pathlib import Path

import modal
from dotenv import dotenv_values

HERE = Path(__file__).parent
DIST = HERE.parent / "frontend" / "dist"
ENV = dotenv_values(HERE.parent.parent / ".env")
ACCESS_CODE = os.environ.get("DEMO_ACCESS_CODE") or ENV.get("DEMO_ACCESS_CODE") or ""

app = modal.App("glimmer-demo")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]>=0.115", "pillow>=11")
    .env({"DEMO_ACCESS_CODE": ACCESS_CODE, "HAS_DIST": "1" if DIST.exists() else "0"})
    .add_local_file(HERE / "model_card.json", "/app/model_card.json")
    .add_local_file(HERE / "examples.json", "/app/examples.json")
    .add_local_dir(HERE / "examples", remote_path="/app/examples")
)
if DIST.exists():
    image = image.add_local_dir(DIST, remote_path="/app/dist")

RATE_PER_MIN = 20          # calls per IP per minute
GLOBAL_PER_MIN = 120       # calls in total per minute
MAX_IMAGE_BYTES = 4 << 20  # decoded image bytes
MAX_SIDE = 448
MAX_PROMPTS = 24           # a choice with N options costs N prompts
WARM_WINDOW_S = 540        # the GPU idles out after 600 s


@app.function(image=image, max_containers=1, scaledown_window=300, timeout=300)
@modal.concurrent(max_inputs=50)
@modal.asgi_app(label="glimmer-demo")
def web():
    import base64, io, json, time
    from collections import defaultdict, deque

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from PIL import Image

    api = FastAPI(title="Glimmer System One demo")
    api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    SystemOne = modal.Cls.from_name("glimmer-systemone", "SystemOne")
    model_card = json.load(open("/app/model_card.json"))
    examples = json.load(open("/app/examples.json"))
    hits = defaultdict(deque)   # ip -> timestamps
    hits_all = deque()
    state = {"last_ok": 0.0, "warm_call": None}

    def check_access(req: Request):
        code = os.environ.get("DEMO_ACCESS_CODE", "")
        if code and req.headers.get("x-access-code", "") != code:
            raise HTTPException(401, "access code missing or wrong")

    def check_rate(req: Request):
        now = time.time()
        ip = req.headers.get("x-forwarded-for", req.client.host if req.client else "?").split(",")[0].strip()
        for dq in (hits[ip], hits_all):
            while dq and dq[0] < now - 60:
                dq.popleft()
        if len(hits[ip]) >= RATE_PER_MIN or len(hits_all) >= GLOBAL_PER_MIN:
            raise HTTPException(429, "rate limit: wait a minute")
        hits[ip].append(now); hits_all.append(now)

    def gpu_state() -> str:
        now = time.time()
        if now - state["last_ok"] < WARM_WINDOW_S:
            return "warm"
        fc = state["warm_call"]
        if fc is not None:
            try:
                fc.get(timeout=0)
                state["last_ok"] = now; state["warm_call"] = None
                return "warm"
            except TimeoutError:
                return "warming"
            except Exception:
                state["warm_call"] = None
        return "cold"

    @api.get("/api/model")
    def get_model():
        return model_card

    @api.get("/api/examples")
    def get_examples():
        return examples

    @api.get("/api/health")
    def health():
        return {"ok": True, "gpu": gpu_state(), "access_code": bool(os.environ.get("DEMO_ACCESS_CODE"))}

    @api.post("/api/warm")
    def warm(req: Request):
        check_access(req)
        s = gpu_state()
        if s == "cold":
            state["warm_call"] = SystemOne().warm.spawn()
            s = "warming"
        return {"gpu": s}

    @api.post("/api/decide")
    async def decide(req: Request):
        check_access(req); check_rate(req)
        body = await req.json()
        if not isinstance(body, dict) or not isinstance(body.get("questions"), dict):
            raise HTTPException(400, "body needs a 'questions' object")
        n_prompts = sum(len(q.get("criteria", {})) if q.get("type") == "choice" else 1 for q in body["questions"].values())
        if n_prompts == 0 or n_prompts > MAX_PROMPTS:
            raise HTTPException(400, f"between 1 and {MAX_PROMPTS} prompts per call, this call has {n_prompts}")
        img_b64 = body.get("image") or ""
        if img_b64:
            if "," in img_b64[:64] and img_b64.startswith("data:"):
                img_b64 = img_b64.split(",", 1)[1]        # a data URL from the browser
            if len(img_b64) * 3 // 4 > MAX_IMAGE_BYTES:
                raise HTTPException(413, "image larger than 4 MB")
            try:
                im = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert("RGB")
            except Exception:
                raise HTTPException(400, "image is not a valid PNG or JPEG")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            buf = io.BytesIO(); im.save(buf, format="PNG")
            body["image"] = base64.b64encode(buf.getvalue()).decode()
        else:
            body.pop("image", None)
            if not (body.get("state") or "").strip():
                raise HTTPException(400, "the request needs an image or a state text")
        body["max_side"] = MAX_SIDE
        t0 = time.time()
        try:
            out = SystemOne().decide_rpc.remote(body)
        except Exception as e:
            raise HTTPException(502, f"the model call failed: {type(e).__name__}")
        if "error" in out:
            raise HTTPException(400, out["error"])
        state["last_ok"] = time.time()
        out["timing"]["round_trip_s"] = round(time.time() - t0, 3)
        out["timing"]["cold_start"] = out["timing"]["round_trip_s"] > 20
        return out

    api.mount("/examples", StaticFiles(directory="/app/examples"), name="examples")
    if os.environ.get("HAS_DIST") == "1":
        api.mount("/", StaticFiles(directory="/app/dist", html=True), name="frontend")
    else:
        @api.get("/", response_class=HTMLResponse)
        def placeholder():
            return "<!doctype html><title>Glimmer System One</title><body style='font-family:system-ui;padding:2rem'>" \
                   "<h1>Glimmer System One</h1><p>The frontend is not built yet. The API is up: " \
                   "<a href='/api/model'>/api/model</a>, <a href='/api/examples'>/api/examples</a>, " \
                   "<a href='/api/health'>/api/health</a>.</p></body>"
    return api

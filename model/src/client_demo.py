"""Call the deployed Glimmer System One endpoint from the Mac.

Usage: uv run python src/client_demo.py <image path> [endpoint url]
"""
import base64, io, json, sys, time, requests
from PIL import Image

url = sys.argv[2] if len(sys.argv) > 2 else "https://aryan-59489--glimmer-decide.us-east.modal.run"
im = Image.open(sys.argv[1]).convert("RGB"); im.thumbnail((448, 448))  # resize on the client: small upload
buf = io.BytesIO(); im.save(buf, format="PNG"); img = base64.b64encode(buf.getvalue()).decode()
body = {"state": "Photo of a part from a production line, taken for quality inspection.", "image": img, "object": "bottle",
        "questions": {
            "defective": {"type": "noul", "instructions": "The part has a visible manufacturing defect.",
                          "head": "noul_defective_known_L52"},
            "defective_zeroshot": {"type": "noul", "instructions": "The part has a visible manufacturing defect.", "raw": True},
            "defect_type": {"type": "choice", "instructions": "Which defect does the part show?", "gate": "defective",
                            "criteria": {"good": None, "broken_large": None, "broken_small": None, "contamination": None}},
            "severity": {"type": "score", "instructions": "How severe is the damage?",
                         "criteria": ["none", "minor", "moderate", "severe"]}}}
for attempt in range(6):  # the first call after idle waits for the cold start (about 60 s)
    t0 = time.time(); r = requests.post(url, json=body, timeout=300); dt = time.time() - t0
    try:
        out = r.json(); break
    except ValueError:
        print(f"attempt {attempt+1}: HTTP {r.status_code}, not JSON, retry in 10 s", file=sys.stderr); time.sleep(10)
print(json.dumps(out, indent=1)); print(f"round trip: {dt:.2f}s")

# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Make the narration of the film with an ElevenLabs voice clone.

Run from anywhere with uv:

    uv run video/voice/generate_voice.py voices
    uv run video/voice/generate_voice.py clone
    uv run video/voice/generate_voice.py generate [--only intro,close]
    uv run video/voice/generate_voice.py trim
    uv run video/voice/generate_voice.py timeline [--write]

Keys come from the .env file at the root of the repository:

    ELEVENLABS_API_KEY   required
    ELEVENLABS_VOICE_ID  optional, the id of the clone; `clone` writes it to voice/voice.json

The script never prints a key value.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

API = "https://api.elevenlabs.io/v1"
VIDEO_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = VIDEO_DIR.parent
LINES_FILE = VIDEO_DIR / "voice" / "lines.json"
VOICE_FILE = VIDEO_DIR / "voice" / "voice.json"
SAMPLE_DIR = VIDEO_DIR / "assets" / "voice" / "sample"
OUT_DIR = VIDEO_DIR / "assets" / "voice"
TIMING_FILE = OUT_DIR / "timing.json"
INDEX_FILE = VIDEO_DIR / "index.html"

# The order of the scenes in index.html. The end card holds for three seconds after the last word.
SCENES = ["intro", "family", "built", "cases", "compare", "demo", "end"]
END_HOLD_S = 2.9


# ---------- keys ----------


def load_env() -> dict[str, str]:
    """Read KEY=VALUE lines from .env at the root. Inline comments after a space are dropped."""
    env: dict[str, str] = {}
    path = REPO_DIR / ".env"
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = re.split(r"\s+#", value, maxsplit=1)[0].strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def api_key() -> str:
    key = load_env().get("ELEVENLABS_API_KEY", "")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is missing from .env. Add it and run again.")
    return key


def headers() -> dict[str, str]:
    return {"xi-api-key": api_key()}


def voice_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    env_id = load_env().get("ELEVENLABS_VOICE_ID", "")
    if env_id:
        return env_id
    if VOICE_FILE.exists():
        return json.loads(VOICE_FILE.read_text())["voice_id"]
    sys.exit("No voice id. Run `clone` first, or set ELEVENLABS_VOICE_ID in .env, or pass --voice.")


def fail(resp: requests.Response, what: str) -> None:
    sys.exit(f"{what} failed with HTTP {resp.status_code}: {resp.text[:500]}")


# ---------- commands ----------


def cmd_voices(_args: argparse.Namespace) -> None:
    """List the voices of the account."""
    resp = requests.get(f"{API}/voices", headers=headers(), timeout=60)
    if not resp.ok:
        fail(resp, "List voices")
    rows = resp.json().get("voices", [])
    print(f"{'voice_id':<24} {'category':<12} name")
    for v in rows:
        print(f"{v['voice_id']:<24} {v.get('category', ''):<12} {v['name']}")


def cmd_clone(args: argparse.Namespace) -> None:
    """Make an instant voice clone from the files in assets/voice/sample/."""
    files = sorted(p for p in SAMPLE_DIR.iterdir() if p.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac", ".ogg"})
    if not files:
        sys.exit(f"No audio files in {SAMPLE_DIR}. Record the sections of voice/RECORD.md first.")
    total_mb = sum(p.stat().st_size for p in files) / 1e6
    print(f"{len(files)} sample files, {total_mb:.1f} MB")
    for p in files:
        mb = p.stat().st_size / 1e6
        flag = "  TOO LARGE, keep each file under 10 MB" if mb > 10 else ""
        print(f"  {p.name}  {mb:.1f} MB{flag}")
    handles = [open(p, "rb") for p in files]
    try:
        multipart = [("files", (p.name, h, "application/octet-stream")) for p, h in zip(files, handles)]
        data = {
            "name": args.name,
            "description": "Aryan Srivastava, narration of the Glimmer System One film",
            "remove_background_noise": "true" if args.denoise else "false",
        }
        resp = requests.post(f"{API}/voices/add", headers=headers(), data=data, files=multipart, timeout=600)
    finally:
        for h in handles:
            h.close()
    if not resp.ok:
        fail(resp, "Clone")
    vid = resp.json()["voice_id"]
    VOICE_FILE.write_text(json.dumps({"voice_id": vid, "name": args.name, "samples": [p.name for p in files]}, indent=2) + "\n")
    print(f"voice_id {vid} written to {VOICE_FILE.relative_to(REPO_DIR)}")
    print("Optional: add ELEVENLABS_VOICE_ID to .env with this id.")


def media_duration(path: Path, fallback: float) -> float:
    """Length of the file in seconds from ffprobe; the fallback is the end of the last timestamp."""
    if not shutil.which("ffprobe"):
        return fallback
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return fallback


def words_from_alignment(al: dict) -> list[dict]:
    """Group the character timestamps of ElevenLabs into words."""
    chars = al["characters"]
    starts = al["character_start_times_seconds"]
    ends = al["character_end_times_seconds"]
    words: list[dict] = []
    buf = ""
    w_start = 0.0
    w_end = 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if buf:
                words.append({"word": buf, "start": round(w_start, 3), "end": round(w_end, 3)})
                buf = ""
            continue
        if not buf:
            w_start = s
        buf += ch
        w_end = e
    if buf:
        words.append({"word": buf, "start": round(w_start, 3), "end": round(w_end, 3)})
    return words


def cmd_generate(args: argparse.Namespace) -> None:
    """Make one MP3 per line of lines.json and write timing.json."""
    vid = voice_id(args.voice)
    lines = json.loads(LINES_FILE.read_text())
    only = set(args.only.split(",")) if args.only else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timing: dict[str, dict] = {}
    if TIMING_FILE.exists():
        timing = {t["id"]: t for t in json.loads(TIMING_FILE.read_text())["lines"]}

    for i, line in enumerate(lines):
        if only and line["id"] not in only:
            continue
        name = f"{i + 1:02d}-{line['id']}.mp3"
        body = {
            "text": line["text"],
            "model_id": args.model,
            "previous_text": lines[i - 1]["text"] if i > 0 else None,
            "next_text": lines[i + 1]["text"] if i + 1 < len(lines) else None,
            "voice_settings": {
                "stability": args.stability,
                "similarity_boost": args.similarity,
                "style": args.style,
                "use_speaker_boost": True,
                "speed": args.speed,
            },
        }
        body = {k: v for k, v in body.items() if v is not None}
        print(f"{name}: {len(line['text'].split())} words ...", end=" ", flush=True)
        resp = requests.post(
            f"{API}/text-to-speech/{vid}/with-timestamps",
            headers={**headers(), "Content-Type": "application/json"},
            params={"output_format": args.format},
            json=body,
            timeout=300,
        )
        if not resp.ok:
            print()
            fail(resp, f"TTS of {line['id']}")
        payload = resp.json()
        (OUT_DIR / name).write_bytes(base64.b64decode(payload["audio_base64"]))
        words = words_from_alignment(payload["alignment"])
        duration = media_duration(OUT_DIR / name, words[-1]["end"] if words else 0.0)
        timing[line["id"]] = {
            "id": line["id"],
            "scene": line["scene"],
            "file": f"assets/voice/{name}",
            "duration_s": round(duration, 3),
            "words": words,
        }
        print(f"{duration:.1f} s")

    ordered = [timing[l["id"]] for l in lines if l["id"] in timing]
    total = sum(t["duration_s"] for t in ordered)
    TIMING_FILE.write_text(json.dumps({"voice_id": vid, "model": args.model, "speed": args.speed, "lines": ordered}, indent=1) + "\n")
    print(f"speech total {total:.1f} s for {len(ordered)} lines, timing in {TIMING_FILE.relative_to(REPO_DIR)}")
    print("Next: uv run video/voice/generate_voice.py timeline")


def trim_end(path: Path, keep_s: float, threshold_db: float) -> None:
    """Cut the silence at the end of the file down to keep_s seconds. The start is not touched."""
    tmp = path.with_suffix(".trim.mp3")
    chain = f"areverse,silenceremove=start_periods=1:start_threshold={threshold_db}dB:start_silence={keep_s},areverse"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path), "-af", chain, "-c:a", "libmp3lame", "-b:a", "128k", str(tmp)],
        check=True,
    )
    tmp.replace(path)


def cmd_trim(args: argparse.Namespace) -> None:
    """Trim the end silence of every file in timing.json and write the new lengths."""
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not installed.")
    data = json.loads(TIMING_FILE.read_text())
    for line in data["lines"]:
        path = VIDEO_DIR / line["file"]
        before = media_duration(path, line["duration_s"])
        trim_end(path, args.keep, args.threshold)
        after = media_duration(path, before)
        line["duration_s"] = round(after, 3)
        print(f"{path.name}: {before:.2f} s -> {after:.2f} s")
    TIMING_FILE.write_text(json.dumps(data, indent=1) + "\n")


def plan(gap: float, lead: float) -> tuple[list[dict], dict[str, dict], float]:
    """Place the lines one after another and derive the scene starts."""
    lines = json.loads(TIMING_FILE.read_text())["lines"]
    for line in lines:
        line["duration_s"] = round(media_duration(VIDEO_DIR / line["file"], line["duration_s"]), 3)
    t = lead
    placed = []
    for line in lines:
        placed.append({**line, "start": round(t, 3), "end": round(t + line["duration_s"], 3)})
        t += line["duration_s"] + gap
    total = placed[-1]["end"] + END_HOLD_S
    scenes: dict[str, dict] = {}
    for scene in SCENES:
        mine = [p for p in placed if p["scene"] == scene]
        if not mine:
            continue
        start = 0.0 if scene == "intro" else mine[0]["start"] - lead
        scenes[scene] = {"start": round(start, 3)}
    names = [s for s in SCENES if s in scenes]
    for a, b in zip(names, names[1:]):
        scenes[a]["duration"] = round(scenes[b]["start"] - scenes[a]["start"], 3)
    scenes[names[-1]]["duration"] = round(total - scenes[names[-1]]["start"], 3)
    return placed, scenes, round(total, 3)


def cmd_timeline(args: argparse.Namespace) -> None:
    """Print the scene times for the read. With --write, patch index.html."""
    if not TIMING_FILE.exists():
        sys.exit("No timing.json. Run `generate` first.")
    placed, scenes, total = plan(args.gap, args.lead)
    print(f"{'line':<10} {'start':>7} {'end':>7} {'dur':>6}")
    for p in placed:
        print(f"{p['id']:<10} {p['start']:>7.2f} {p['end']:>7.2f} {p['duration_s']:>6.2f}")
    print()
    print(f"{'scene':<10} {'start':>7} {'dur':>7}   (now in index.html)")
    html = INDEX_FILE.read_text()
    for scene, s in scenes.items():
        m = re.search(rf'id="{scene}"[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"', html)
        now = f"{m.group(1)} / {m.group(2)}" if m else "?"
        print(f"{scene:<10} {s['start']:>7.2f} {s['duration']:>7.2f}   {now}")
    print(f"total {total:.2f} s, the film is 180 s now")
    if not args.write:
        print("Run with --write to patch the hosts and the audio clips in index.html.")
        return

    for scene, s in scenes.items():
        pattern = re.compile(rf'(<div[^>]*id="{scene}"[^>]*?)data-start="[^"]*"(\s+)data-duration="[^"]*"')
        html, n = pattern.subn(rf'\1data-start="{s["start"]:g}"\2data-duration="{s["duration"]:g}"', html)
        if n != 1:
            sys.exit(f"Could not patch the host of scene {scene} in index.html")
    for host in ("presenter", "root"):
        pattern = re.compile(rf'(<div[^>]*id="{host}"[^>]*?)data-duration="[^"]*"')
        html, n = pattern.subn(rf'\1data-duration="{total:g}"', html)
        if n != 1:
            sys.exit(f"Could not patch the duration of #{host} in index.html")

    clips = ["      <!-- voice: written by voice/generate_voice.py timeline --write -->"]
    for p in placed:
        clips.append(
            f'      <audio id="vo-{p["id"]}" src="{p["file"]}" data-start="{p["start"]:g}" '
            f'data-duration="{p["duration_s"]:g}" data-volume="1" data-track-index="3" data-track-kind="audio"></audio>'
        )
    clips.append("      <!-- /voice -->")
    block = "\n".join(clips)
    if "<!-- voice:" in html:
        html = re.sub(r"      <!-- voice:.*?<!-- /voice -->", block, html, flags=re.S)
    else:
        html = re.sub(r'(<div[^>]*id="presenter"[^>]*></div>\n)', r"\1" + block + "\n", html, count=1)
    INDEX_FILE.write_text(html)
    print(f"index.html patched. The scene timelines inside compositions/*.html still use the old lengths. Review them, then run `npm run check`.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("voices", help="list the voices of the account").set_defaults(fn=cmd_voices)

    c = sub.add_parser("clone", help="make the instant voice clone from assets/voice/sample/")
    c.add_argument("--name", default="Aryan narration")
    c.add_argument("--no-denoise", dest="denoise", action="store_false")
    c.set_defaults(fn=cmd_clone)

    g = sub.add_parser("generate", help="make one MP3 per line and timing.json")
    g.add_argument("--voice", help="voice id; else ELEVENLABS_VOICE_ID or voice/voice.json")
    g.add_argument("--model", default="eleven_v4", help="eleven_v4, eleven_v3 or eleven_multilingual_v2")
    g.add_argument("--format", default="mp3_44100_128")
    g.add_argument("--speed", type=float, default=1.0, help="0.7 to 1.2; 1.05 gives a brisk read")
    g.add_argument("--stability", type=float, default=0.5)
    g.add_argument("--similarity", type=float, default=0.8)
    g.add_argument("--style", type=float, default=0.0)
    g.add_argument("--only", help="comma list of line ids to make again, for example intro,close")
    g.set_defaults(fn=cmd_generate)

    tr = sub.add_parser("trim", help="cut the silence at the end of each voice file")
    tr.add_argument("--keep", type=float, default=0.1, help="silence to keep at the end, seconds")
    tr.add_argument("--threshold", type=float, default=-45.0, help="silence threshold, dB")
    tr.set_defaults(fn=cmd_trim)

    t = sub.add_parser("timeline", help="print the scene times for the read; --write patches index.html")
    t.add_argument("--gap", type=float, default=0.4, help="silence between lines, seconds")
    t.add_argument("--lead", type=float, default=0.4, help="silence before the first word of a scene, seconds")
    t.add_argument("--write", action="store_true")
    t.set_defaults(fn=cmd_timeline)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

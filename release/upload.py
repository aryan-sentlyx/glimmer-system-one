"""Push the Glimmer System One heads to the Hugging Face Hub.

Run from model/ (the folder with the venv):
    cd model && uv run python ../release/upload.py [--dry-run] [--repo aryan-sentlyx/glimmer-system-one-heads]

Reads HF_WRITE_TOKEN from the root .env. Falls back to HF_TOKEN. Never prints a token.
Creates the model repo if it does not exist, then uploads the files listed in FILES and the model card.
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HEAD = ROOT / "results" / "head"
DEFAULT_REPO = "aryan-sentlyx/glimmer-system-one-heads"

# (local path, path in the repo)
FILES = [
    (HEAD / "noul_defective_known_L52.npz", "noul_defective_known_L52.npz"),
    (HEAD / "noul_defective_known_L13.npz", "noul_defective_known_L13.npz"),
    (HEAD / "temp_noul.json", "temp_noul.json"),
    (HEAD / "known_split.json", "known_split.json"),
    (HEAD / "results.json", "results.json"),
    (ROOT / "results" / "reliability.png", "reliability.png"),
    (HERE / "MODEL_CARD.md", "README.md"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--dry-run", action="store_true", help="list the files and check the token, no upload")
    a = ap.parse_args()

    load_dotenv(ROOT / ".env")
    token = os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print("no HF_WRITE_TOKEN and no HF_TOKEN in .env", file=sys.stderr)
        return 1

    missing = [str(p) for p, _ in FILES if not p.exists()]
    if missing:
        print("missing files:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    api = HfApi(token=token)
    who = api.whoami()
    role = (who.get("auth") or {}).get("accessToken", {}).get("role")
    print(f"token owner: {who.get('name')}  role: {role}")
    if role not in ("write", "fineGrained"):
        print("the token has no write role; make a write token at huggingface.co/settings/tokens", file=sys.stderr)
        return 1

    for p, name in FILES:
        print(f"  {name:36s} {p.stat().st_size / 1024:8.1f} KB")
    if a.dry_run:
        print("dry run, nothing uploaded")
        return 0

    url = api.create_repo(a.repo, repo_type="model", exist_ok=True)
    print(f"repo: {url}")
    for p, name in FILES:
        api.upload_file(path_or_fileobj=str(p), path_in_repo=name, repo_id=a.repo, repo_type="model",
                        commit_message=f"add {name}")
        print(f"uploaded {name}")
    print(f"done: https://huggingface.co/{a.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

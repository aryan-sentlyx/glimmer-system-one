# release

The Hugging Face release of the heads, Apache 2.0: [aryan-sentlyx/glimmer-system-one-heads](https://huggingface.co/aryan-sentlyx/glimmer-system-one-heads).

| File | Content |
|---|---|
| `MODEL_CARD.md` | The model card. It becomes the `README.md` of the Hub repo. |
| `upload.py` | Pushes the two heads, `temp_noul.json`, `known_split.json`, `results.json`, `reliability.png` and the card to the Hub. |

```
cd model
uv run python ../release/upload.py --dry-run   # check the token and the files
uv run python ../release/upload.py             # upload
```

The script reads `HF_WRITE_TOKEN` from the root `.env`. The token must have the write role for the account `aryan-sentlyx`.

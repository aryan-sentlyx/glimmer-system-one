# results

| Path | Content |
|---|---|
| `decisions/*.jsonl` | One line per image per system: label, probability, latency, cost. Files with `_bottle` are the first smoke runs on one object. |
| `report.md`, `reliability.png` | Output of `model/src/report.py`. |
| `head/noul_defective_known_L52.npz` | Logistic head on layer 52. Template `inspect_defective_v1`. |
| `head/noul_defective_known_L13.npz` | Logistic head on layer 13 for early exit. |
| `head/known_split.json` | The held-out image indices per object, seed 0. Use these for any demo of the head. |
| `head/temp_noul.json` | The temperature for zero-shot mode. |
| `latency_race.jsonl` | Spark against Glimmer on 20 held-out bottles. |
| `logs/` | The run logs. |

"""Read MVTec AD rows from the parquet mirror on the glimmer-data volume."""
import io
from dataclasses import dataclass

import os
DATA_DIR = os.environ.get("MVTEC_DIR", "/data/mvtec_ad/data")
OBJECTS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather", "metal_nut",
           "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]


@dataclass
class Row:
    image: object  # PIL.Image
    obj: str
    defect: str    # "good" or a defect name
    label: int     # 0 good, 1 defective
    split: str


def load_rows(obj: str, split: str, limit: int | None = None, seed: int = 0) -> list[Row]:
    import pyarrow.parquet as pq
    from PIL import Image
    import random

    path = f"{DATA_DIR}/{obj}.{split}-00000-of-00001.parquet"
    try:
        table = pq.read_table(path)
    except FileNotFoundError:
        # carpet.train has two shards
        import glob
        import pyarrow as pa
        parts = sorted(glob.glob(f"{DATA_DIR}/{obj}.{split}-*.parquet"))
        table = pa.concat_tables([pq.read_table(p) for p in parts])
    rows = table.to_pylist()
    random.Random(seed).shuffle(rows)
    if limit:
        rows = rows[:limit]
    out = []
    for r in rows:
        img = r["image_path"]
        if isinstance(img, dict):
            img = Image.open(io.BytesIO(img["bytes"]))
        out.append(Row(image=img.convert("RGB"), obj=r["object"], defect=r["defect"],
                       label=int(r["label"]), split=r["split"]))
    return out

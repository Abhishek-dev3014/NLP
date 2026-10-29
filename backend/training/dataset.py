"""One reproducible LIAR split preparation shared by both generations."""

import hashlib
import re
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from app.ml.preprocessing import clean_text

LABELS = {"true": 0, "mostly-true": 0, "false": 1, "pants-fire": 1}


def load_splits(directory: Path):
    frames = []
    for split in ("train", "valid", "test"):
        frame = pd.read_csv(
            directory / f"{split}.tsv", sep="\t", header=None, quoting=3, dtype=str
        )
        frame = frame[frame[1].isin(LABELS)].copy()
        frame["label"] = frame[1].map(LABELS)
        frame["text"] = frame[2].map(clean_text)
        frame["id"] = frame[0]
        frame["split"] = split
        frames.append(frame[["id", "text", "label", "split"]])
    data = pd.concat(frames, ignore_index=True)
    original = len(data)
    data["fingerprint"] = data.text.map(lambda x: re.sub(r"\W+", "", x.lower()))
    data = data.drop_duplicates("fingerprint").reset_index(drop=True)
    exact = original - len(data)
    x = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=50000
    ).fit_transform(data.text)
    matches = (
        NearestNeighbors(metric="cosine", algorithm="brute", radius=0.08, n_jobs=1)
        .fit(x)
        .radius_neighbors(x, return_distance=False)
    )
    dropped = set()
    for i, indices in enumerate(matches):
        if i not in dropped:
            dropped.update(int(j) for j in indices if j > i)
    data = data.drop(index=list(dropped)).reset_index(drop=True)
    digest = hashlib.sha256("\n".join(data.id).encode()).hexdigest()
    return tuple(
        data[data.split == s].reset_index(drop=True) for s in ("train", "valid", "test")
    ), {
        "exact": exact,
        "near": len(dropped),
        "near_cosine_threshold": 0.92,
        "split_fingerprint": digest,
    }

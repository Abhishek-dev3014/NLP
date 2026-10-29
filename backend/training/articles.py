"""Prepare grouped WELFake splits, select on validation, calibrate separately, test once."""

import hashlib
import json
from datetime import datetime, timezone
import re
import time
import joblib
import numpy as np
import pandas as pd
from datasketch import MinHash, MinHashLSH
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, classification_report
from app.ml.article_features import article_text
from app.core.config import ROOT
from training.improve import measurements, calibration_bins, wilson

DATA = ROOT.parent / "data/raw/articles/WELFake_Dataset.csv"
OUT = ROOT / "artifacts/articles"
SPECS = [("Linear SVM C=0.5", 0.5), ("Linear SVM C=1", 1.0), ("Linear SVM C=2", 2.0)]


def prepare():
    cache = OUT / "prepared.joblib"
    if cache.exists():
        return joblib.load(cache)
    if hashlib.md5(DATA.read_bytes()).hexdigest() != "73c9675a4b3d09f86a6933d0b8d7d908":
        raise ValueError("Dataset checksum mismatch")
    raw = pd.read_csv(DATA)
    raw["id"] = raw.iloc[:, 0].astype(str)
    raw["text"] = raw["text"].fillna("").map(article_text)
    raw["title"] = raw["title"].fillna("").astype(str)
    counts = raw.label.value_counts().to_dict()
    # Zenodo prose reverses label meaning; CSV frequencies and Reuters source audit agree with 1=fake.
    assert counts == {1: 37106, 0: 35028}, counts
    # The source-tag audit is recorded separately because preprocessing removes these markers.
    original = pd.read_csv(DATA, usecols=["text", "label"])
    tagged = original.text.fillna("").str.contains(r"\(Reuters\)", regex=True)
    source_counts = {
        int(k): int(v) for k, v in original.loc[tagged, "label"].value_counts().items()
    }
    assert source_counts.get(0, 0) > 20000 and source_counts.get(1, 0) < 100, (
        source_counts
    )
    print(
        "CSV label audit: 0=35028 real; 1=37106 fake; authors description reverses the numeric mapping.",
        flush=True,
    )
    raw = raw[raw.text.str.split().str.len().between(40, 2500)].reset_index(drop=True)
    before = len(raw)
    raw["fingerprint"] = raw.text.map(
        lambda t: hashlib.sha256(re.sub(r"\W+", "", t).encode()).hexdigest()
    )
    conflicting = raw.groupby("fingerprint").label.nunique()
    ambiguous = set(conflicting[conflicting > 1].index)
    raw = (
        raw[~raw.fingerprint.isin(ambiguous)]
        .drop_duplicates("fingerprint")
        .reset_index(drop=True)
    )
    print("Usable after exact duplicates/contradictions:", len(raw), flush=True)
    parent = list(range(len(raw)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    titles = {}
    leads = {}
    lsh = MinHashLSH(threshold=0.80, num_perm=64)
    # LSH candidates are grouped conservatively. No true/fake label enters clustering.
    for i, row in enumerate(raw.itertuples()):
        words = re.findall(r"\b\w+\b", row.text)
        title = re.sub(r"\W+", "", row.title.lower())
        if len(title) > 25:
            if title in titles:
                union(i, titles[title])
            else:
                titles[title] = i
        lead = " ".join(words[:80])
        if lead in leads:
            union(i, leads[lead])
        else:
            leads[lead] = i
        shingles = set(
            " ".join(words[j : j + 3]).encode() for j in range(len(words) - 2)
        )
        signature = MinHash(num_perm=64, seed=42)
        signature.update_batch(list(shingles))
        for other in lsh.query(signature):
            union(i, int(other))
        lsh.insert(str(i), signature)
        if i % 10000 == 0:
            print(f"Near-duplicate grouping {i}/{len(raw)}", flush=True)
    raw["group"] = [find(i) for i in range(len(raw))]
    # Keep every duplicate group in one split; assign ten disjoint folds.
    splitter = StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)
    raw["fold"] = -1
    for fold, (_, idx) in enumerate(splitter.split(raw.text, raw.label, raw.group)):
        raw.loc[idx, "fold"] = fold
    raw["split"] = np.select(
        [raw.fold < 6, raw.fold == 6, raw.fold == 7],
        ["train", "validation", "calibration"],
        default="test",
    )
    audit = {
        "raw_rows": len(pd.read_csv(DATA, usecols=["label"])),
        "usable_rows": len(raw),
        "filtered_exact_or_conflicting": before - len(raw),
        "ambiguous_fingerprints": len(ambiguous),
        "groups": int(raw.group.nunique()),
        "near_grouped_rows": int(len(raw) - raw.group.nunique()),
        "grouping": "Exact body duplicates removed; identical title/80-word lead and 64-permutation MinHash LSH at 0.80 similarity kept in a common group. Approximate grouping can miss paraphrases.",
        "split_fingerprint": hashlib.sha256(
            "\n".join(raw.id + ":" + raw.split).encode()
        ).hexdigest(),
        "label_audit": "CSV 0=real (35028), 1=fake (37106); Zenodo description reverses numeric mapping. Reuters source-tagged rows and published class totals corroborate this mapping.",
    }
    for name in raw.split.unique():
        group = set(raw.loc[raw.split == name, "group"])
        assert not group.intersection(raw.loc[raw.split != name, "group"])
    bundle = (raw, audit)
    joblib.dump(bundle, cache)
    (OUT / "split-manifest.json").write_text(
        json.dumps(raw[["id", "group", "split"]].to_dict("records"))
    )
    return bundle


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame, audit = prepare()
    splits = {
        name: frame[frame.split == name]
        for name in ["train", "validation", "calibration", "test"]
    }
    print("Splits", {k: len(v) for k, v in splits.items()}, flush=True)
    train, valid, cal, test = [splits[k] for k in splits]
    vectorizer = TfidfVectorizer(
        preprocessor=article_text,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.98,
        max_features=140000,
        sublinear_tf=True,
        dtype=np.float32,
    )
    x = vectorizer.fit_transform(train.text)
    v = vectorizer.transform(valid.text)
    print("Fitted vocabulary", x.shape, flush=True)
    results = []
    best = None
    key = (-1, -1)
    for name, c in SPECS:
        start = time.monotonic()
        model = LinearSVC(
            C=c, class_weight="balanced", random_state=42, max_iter=5000, dual="auto"
        ).fit(x, train.label)
        logits = model.decision_function(v)
        probs = 1 / (1 + np.exp(-logits))
        scores = measurements(valid.label.to_numpy(), probs)
        results.append(
            {"name": name, "C": c, **scores, "seconds": time.monotonic() - start}
        )
        print(name, json.dumps(scores), flush=True)
        candidate = (scores["macro_f1"], scores["roc_auc"])
        if candidate > key:
            key = candidate
            best = (name, c, model)
    name, c, model = best
    # Dedicated calibration group: never used to learn vocabulary, model weights, or C.
    calibration_x = vectorizer.transform(cal.text)
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", random_state=42).fit(
        model.decision_function(calibration_x).reshape(-1, 1), cal.label
    )
    # Fixed operating policy; no test-based threshold search.
    threshold = 0.65
    xt = vectorizer.transform(test.text)
    logits = model.decision_function(xt)
    p = calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]
    y = test.label.to_numpy()
    scores = measurements(y, p)
    bins, ece = calibration_bins(y, p)
    mask = np.maximum(p, 1 - p) >= threshold
    count = int(mask.sum())
    correct = int(((p[mask] >= 0.5) == y[mask]).sum())
    version = "welfake-article-" + audit["split_fingerprint"][:10]
    metadata = {
        "version": version,
        "model_name": "Article TF-IDF + calibrated Linear SVM",
        "threshold": threshold,
        "max_words": 2500,
        "min_words": 40,
        "dataset": "WELFake",
        "calibrated": True,
    }
    metrics = {
        **scores,
        "model_name": metadata["model_name"],
        "version": version,
        "dataset": "WELFake English full-article benchmark (2021 release)",
        "dataset_url": "https://zenodo.org/records/4561253",
        "dataset_size": len(frame),
        "class_distribution": {
            "credible": int((frame.label == 0).sum()),
            "misleading": int((frame.label == 1).sum()),
        },
        "split": {k: len(df) for k, df in splits.items()},
        "split_method": "Stratified duplicate-group split: 60% train, 10% validation, 10% calibration, 20% test. All four partitions are group-disjoint.",
        "evaluation_note": "Full test accuracy is measured before abstention, without excluding low-confidence examples. Not source/time held out; not validated on contemporary Indian news.",
        "confusion_matrix": confusion_matrix(y, p >= 0.5, labels=[0, 1]).tolist(),
        "classification_report": classification_report(
            y, p >= 0.5, target_names=["credible", "misleading"], output_dict=True
        ),
        "calibrated": True,
        "calibration": {
            "method": "Sigmoid calibration on a separate 10% group-disjoint calibration set",
            "brier_before": float(
                measurements(y, 1 / (1 + np.exp(-logits)))["brier_score"]
            ),
            "brier_after": scores["brier_score"],
            "ece": ece,
            "reliability_bins": bins,
        },
        "confidence_policy": {
            "threshold": threshold,
            "evaluation_scope": "confidence_only",
            "test_count": count,
            "test_correct": correct,
            "test_coverage": count / len(y),
            "test_accuracy": correct / count if count else None,
            "test_accuracy_interval": wilson(correct, count),
            "note": "Fixed 0.65 threshold. These conditional results supplement, never replace, full-test metrics.",
        },
        "accuracy_interval": wilson(int(((p >= 0.5) == y).sum()), len(y)),
        "validation_search": results,
        "selected_C": c,
        "seed": 42,
        "selection_rule": "Highest validation macro-F1; ROC-AUC breaks ties. Calibration on separate groups. Test evaluated once after selection.",
        "label_mapping": {
            "credible": ["CSV label 0 (real)"],
            "misleading": ["CSV label 1 (fake)"],
            "excluded": [
                "Missing/short bodies",
                "Exact duplicate bodies",
                "Contradictory exact duplicates",
            ],
        },
        "duplicates_removed": {
            "exact": audit["filtered_exact_or_conflicting"],
            "near": 0,
        },
        "data_audit": audit,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "license_note": "Authors distribute WELFake on Zenodo under CC BY 4.0. Attribute Verma, Agrawal and Prodan (2021). Article copyrights may differ; raw content is kept local, not republished.",
        "limitations": [
            "Benchmark labels are inherited from merged datasets, sometimes publisher-level rather than individually verified claims.",
            "Source and writing-style shortcuts remain despite stripping obvious Reuters/AP/byline/URL markers. This is not source-disjoint evaluation.",
            "Training news is historical and largely US-focused. Indian/current-news accuracy has not been measured.",
            "Approximate duplicate grouping reduces leakage but does not prove absence of paraphrase leakage.",
            "Calibrated model confidence is benchmark class probability, not factual verification.",
            "Only the first 2500 words of each article enter the classifier. Short snippets below 40 words receive an uncertain result.",
        ],
    }
    # LIAR is separately labeled domain stress, not pooled into the article benchmark.
    from training.dataset import load_splits

    (_, _, liar), _ = load_splits(ROOT.parent / "data/raw")
    lp = calibrator.predict_proba(
        model.decision_function(vectorizer.transform(liar.text)).reshape(-1, 1)
    )[:, 1]
    metrics["domain_stress"] = {
        "dataset": "LIAR short political claims (different task/domain)",
        "count": len(liar),
        **measurements(liar.label.to_numpy(), lp),
        "note": "Cross-domain diagnostic. Not included in WELFake test metrics and not used for tuning.",
    }
    bundle = {
        "kind": "article-svm-v1",
        "vectorizer": vectorizer,
        "classifier": model,
        "calibrator": calibrator,
        "metadata": metadata,
        "metrics": metrics,
    }
    joblib.dump(bundle, OUT / "model.joblib")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (OUT / "test-predictions.json").write_text(
        json.dumps(
            [
                {"id": str(row.id), "label": int(row.label), "p_fake": float(prob)}
                for row, prob in zip(test.itertuples(), p)
            ]
        )
    )
    print(
        "FINAL",
        json.dumps(
            {
                "test": scores,
                "scope_stress": metrics["domain_stress"],
                "output": str(OUT),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

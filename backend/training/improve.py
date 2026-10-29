"""Compare predeclared candidates, select on validation, calibrate OOF, then test once."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    brier_score_loss,
    log_loss,
)
from app.ml.features import FeatureEncoder, embed
from training.dataset import load_splits

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [
    {"name": "Word TF-IDF", "char_weight": 0.0, "semantic_weight": 0.0, "C": 1.0},
    {
        "name": "Word + character TF-IDF",
        "char_weight": 0.5,
        "semantic_weight": 0.0,
        "C": 1.0,
    },
    {
        "name": "Word + character TF-IDF, stronger regularization",
        "char_weight": 0.5,
        "semantic_weight": 0.0,
        "C": 0.5,
    },
    {
        "name": "TF-IDF + MiniLM embeddings",
        "char_weight": 0.35,
        "semantic_weight": 1.0,
        "C": 1.0,
    },
    {
        "name": "TF-IDF + MiniLM embeddings, semantic emphasis",
        "char_weight": 0.35,
        "semantic_weight": 2.0,
        "C": 1.0,
    },
    {
        "name": "TF-IDF + MiniLM embeddings, stronger regularization",
        "char_weight": 0.35,
        "semantic_weight": 1.0,
        "C": 0.5,
    },
]


def measurements(y, p):
    predicted = (p >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "macro_f1": float(f1_score(y, predicted, average="macro")),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
    }


def calibration_bins(y, p):
    bins = []
    for low in np.linspace(0, 0.9, 10):
        mask = (p >= low) & (p < (low + 0.1) if low < 0.9 else p <= 1)
        if mask.any():
            bins.append(
                {
                    "lower": round(float(low), 1),
                    "upper": round(float(low + 0.1), 1),
                    "count": int(mask.sum()),
                    "predicted": float(p[mask].mean()),
                    "observed": float(y[mask].mean()),
                }
            )
    ece = sum(b["count"] * abs(b["predicted"] - b["observed"]) for b in bins) / len(y)
    return bins, float(ece)


def wilson(correct, total):
    if not total:
        return [None, None]
    z = 1.96
    p = correct / total
    denom = 1 + z * z / total
    middle = (p + z * z / (2 * total)) / denom
    delta = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denom
    return [middle - delta, middle + delta]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexical-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "backend/artifacts/v2")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (train, valid, test), dedup = load_splits(ROOT / "data/raw")
    print(f"Retained splits: {len(train)}/{len(valid)}/{len(test)}", flush=True)
    candidates = CANDIDATES[:3] if args.lexical_only else CANDIDATES
    etrain = evalid = None
    if not args.lexical_only:
        cache = ROOT / "backend/artifacts/embedding-cache.npz"
        fingerprint = hashlib.sha256(
            ("\n".join(train.text) + "\n".join(valid.text)).encode()
        ).hexdigest()
        if cache.exists() and str(np.load(cache)["fingerprint"]) == fingerprint:
            values = np.load(cache)
            etrain, evalid = values["train"], values["valid"]
        else:
            print(
                "Encoding train/validation statements with frozen MiniLM (encoder is not fine-tuned).",
                flush=True,
            )
            etrain, evalid = embed(train.text), embed(valid.text)
            np.savez_compressed(
                cache, train=etrain, valid=evalid, fingerprint=fingerprint
            )
    results = []
    best = None
    best_key = (-1, -1)
    for spec in candidates:
        started = time.monotonic()
        encoder = FeatureEncoder(spec["semantic_weight"], spec["char_weight"])
        x = encoder.fit_transform(train.text, etrain)
        v = encoder.transform(valid.text, evalid)
        model = LogisticRegression(
            C=spec["C"],
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
            solver="liblinear",
        )
        model.fit(x, train.label)
        score = measurements(valid.label.to_numpy(), model.predict_proba(v)[:, 1])
        result = {**spec, **score, "seconds": round(time.monotonic() - started, 2)}
        results.append(result)
        print(json.dumps(result), flush=True)
        key = (score["macro_f1"], score["roc_auc"])
        if key > best_key:
            best_key = key
            best = (spec, encoder, model)
    spec, encoder, model = best
    print(f"Selected using validation macro-F1: {spec['name']}", flush=True)
    # Every calibration logit is generated with both vectorizer and classifier fitted without that row.
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof = np.zeros(len(train))
    for fold, (fit_idx, cal_idx) in enumerate(folds.split(train.text, train.label)):
        fold_encoder = FeatureEncoder(spec["semantic_weight"], spec["char_weight"])
        x = fold_encoder.fit_transform(
            train.text.iloc[fit_idx], etrain[fit_idx] if etrain is not None else None
        )
        v = fold_encoder.transform(
            train.text.iloc[cal_idx], etrain[cal_idx] if etrain is not None else None
        )
        fold_model = LogisticRegression(
            C=spec["C"],
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
            solver="liblinear",
        ).fit(x, train.label.iloc[fit_idx])
        oof[cal_idx] = fold_model.decision_function(v)
        print(f"Calibration fold {fold + 1}/5 completed", flush=True)
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", random_state=42).fit(
        oof.reshape(-1, 1), train.label
    )
    vp = calibrator.predict_proba(
        model.decision_function(encoder.transform(valid.text, evalid)).reshape(-1, 1)
    )[:, 1]
    threshold = 0.70
    # Predeclared target, selected on validation only; lower confidence never means a false claim.
    validation_gate = []
    for value in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        mask = np.maximum(vp, 1 - vp) >= value
        correct = int(
            ((vp[mask] >= 0.5).astype(int) == valid.label.to_numpy()[mask]).sum()
        )
        count = int(mask.sum())
        accuracy = correct / count if count else None
        validation_gate.append(
            {
                "threshold": value,
                "count": count,
                "accuracy": accuracy,
                "interval": wilson(correct, count),
            }
        )
    acceptable = [
        v
        for v in validation_gate
        if v["count"] >= 40 and v["accuracy"] >= 0.80 and v["interval"][0] >= 0.65
    ]
    if acceptable:
        threshold = acceptable[0]["threshold"]
    # Only now is test content encoded and the final selected model evaluated.
    test_x = encoder.transform(test.text)
    raw = model.predict_proba(test_x)[:, 1]
    probabilities = calibrator.predict_proba(
        model.decision_function(test_x).reshape(-1, 1)
    )[:, 1]
    y = test.label.to_numpy()
    score = measurements(y, probabilities)
    bins, ece = calibration_bins(y, probabilities)
    mask = np.maximum(probabilities, 1 - probabilities) >= threshold
    correct = int(((probabilities[mask] >= 0.5).astype(int) == y[mask]).sum())
    count = int(mask.sum())
    old_bundle = joblib.load(ROOT / "backend/artifacts/v1/baseline.joblib")
    old_score = measurements(y, old_bundle["pipeline"].predict_proba(test.text)[:, 1])
    digest = hashlib.sha256(
        json.dumps(spec, sort_keys=True).encode() + dedup["split_fingerprint"].encode()
    ).hexdigest()[:12]
    version = f"liar-calibrated-{digest}"
    metadata = {
        "version": version,
        "seed": 42,
        "model_name": "Calibrated " + spec["name"] + " + Logistic Regression",
        "calibrated": True,
        "threshold": threshold,
        "feature_spec": spec,
        "max_claim_words": 160,
        "min_coverage": 0.35,
    }
    prior = json.loads((ROOT / "backend/artifacts/v1/metrics.json").read_text())
    metrics = {
        **prior,
        **score,
        "version": version,
        "model_name": metadata["model_name"],
        "calibrated": True,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "selected_C": spec["C"],
        "duplicates_removed": dedup,
        "selected_features": spec,
        "validation_search": results,
        "selection_rule": "Highest validation macro-F1; ROC-AUC breaks ties. Test labels never used for selection.",
        "calibration": {
            "method": "Sigmoid / Platt scaling using 5-fold out-of-fold training logits",
            "folds": 5,
            "brier_before": float(brier_score_loss(y, raw)),
            "brier_after": score["brier_score"],
            "ece": ece,
            "reliability_bins": bins,
            "slope": float(calibrator.coef_[0, 0]),
            "intercept": float(calibrator.intercept_[0]),
        },
        "previous_model": {
            "name": prior["model_name"],
            "version": prior["version"],
            **old_score,
        },
        "confidence_policy": {
            "evaluation_scope": "confidence_only",
            "threshold": threshold,
            "target_met_on_validation": bool(acceptable),
            "validation_curve": validation_gate,
            "test_coverage": count / len(y),
            "test_count": count,
            "test_correct": correct,
            "test_accuracy": correct / count if count else None,
            "test_accuracy_interval": wilson(correct, count),
            "note": "Accuracy among accepted predictions is conditional and may be based on few samples. Always read coverage and the interval together.",
        },
        "accuracy_interval": wilson(
            int(((probabilities >= 0.5).astype(int) == y).sum()), len(y)
        ),
        "confusion_matrix": confusion_matrix(
            y, probabilities >= 0.5, labels=[0, 1]
        ).tolist(),
        "classification_report": classification_report(
            y,
            probabilities >= 0.5,
            target_names=["credible", "misleading"],
            output_dict=True,
        ),
        "encoder": {
            "name": "sentence-transformers/all-MiniLM-L6-v2",
            "fine_tuned_here": False,
            "dimensions": 384,
        }
        if spec["semantic_weight"]
        else None,
        "limitations": [
            "Only short historical US political claims are evaluated; full articles and other topics need additional validation.",
            "Calibration is fitted on out-of-fold training predictions and assessed on held-out claims; it does not guarantee calibration in other domains.",
            "Historical test set was also reported for v1; this comparison is retrospective, not a new unseen benchmark.",
            "Middle truthfulness labels are excluded; this is not the original six-class task.",
            "Sources and speakers overlap across official splits. Dataset framing can become a shortcut.",
            "Model estimates measure learned label associations, not independent factual truth.",
        ],
    }
    bundle = {
        "kind": "calibrated-hybrid-v2",
        "encoder": encoder,
        "classifier": model,
        "calibrator": calibrator,
        "metadata": metadata,
        "metrics": metrics,
    }
    joblib.dump(bundle, args.output / "model.joblib")
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (args.output / "test-predictions.json").write_text(
        json.dumps(
            [
                {"id": str(row.id), "label": int(row.label), "probability": float(p)}
                for row, p in zip(test.itertuples(), probabilities)
            ],
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "selected": spec,
                "test": score,
                "previous": old_score,
                "confidence_policy": metrics["confidence_policy"],
                "output": str(args.output),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

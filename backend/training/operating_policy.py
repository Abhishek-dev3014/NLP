"""Select an abstention policy on validation without changing the baseline weights.

The historical test set is a retrospective comparison. It is never used to
choose a threshold. Both conditional accuracy and coverage are reported.
"""

import json
from pathlib import Path
import joblib
import numpy as np
from app.ml.classifier import BaselineClassifier
from training.dataset import load_splits
from training.improve import measurements, wilson

ROOT = Path(__file__).resolve().parents[2]


def main():
    (_, valid, test), _ = load_splits(ROOT / "data/raw")
    path = ROOT / "backend/artifacts/v1/baseline.joblib"
    model = BaselineClassifier(str(path))
    bundle = joblib.load(path)

    def screen(frame):
        return np.array([model.predict(t)["in_domain"] for t in frame.text])

    valid_scope = screen(valid)
    vp = bundle["pipeline"].predict_proba(valid.text)[:, 1]
    curve = []
    for threshold in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        mask = valid_scope & (np.maximum(vp, 1 - vp) >= threshold)
        correct = int(
            ((vp[mask] >= 0.5).astype(int) == valid.label.to_numpy()[mask]).sum()
        )
        count = int(mask.sum())
        curve.append(
            {
                "threshold": threshold,
                "count": count,
                "accuracy": correct / count if count else None,
                "interval": wilson(correct, count),
            }
        )
    acceptable = [
        r
        for r in curve
        if r["count"] >= 40 and r["accuracy"] >= 0.8 and r["interval"][0] >= 0.65
    ]
    threshold = acceptable[0]["threshold"] if acceptable else 0.70
    p = bundle["pipeline"].predict_proba(test.text)[:, 1]
    mask = screen(test) & (np.maximum(p, 1 - p) >= threshold)
    count = int(mask.sum())
    correct = int(((p[mask] >= 0.5).astype(int) == test.label.to_numpy()[mask]).sum())
    policy = {
        "threshold": threshold,
        "target_met_on_validation": bool(acceptable),
        "validation_curve": curve,
        "test_coverage": count / len(test),
        "test_count": count,
        "test_correct": correct,
        "test_accuracy": correct / count if count else None,
        "test_accuracy_interval": wilson(correct, count),
        "note": "Actual serving policy: keyword/length/vocabulary scope screen plus confidence threshold. Conditional accuracy covers only accepted claims; rejected claims receive no definitive class. Confidence remains uncalibrated.",
    }
    metrics = json.loads((ROOT / "backend/artifacts/v1/metrics.json").read_text())
    metrics.update(measurements(test.label.to_numpy(), p))
    metrics.update(
        {
            "confidence_policy": policy,
            "version": metrics["version"] + "-policy2",
            "selection_rule": "Baseline weights retained after the validation-selected challenger regressed on the retrospective test comparison. Abstention threshold chosen on validation only.",
            "evaluation_note": "Full-test metrics measure the underlying classifier before abstention. Policy metrics measure accepted predictions. This is a retrospective evaluation on the previously reported test set.",
        }
    )
    bundle["metadata"].update({"threshold": threshold, "version": metrics["version"]})
    bundle["metrics"] = metrics
    joblib.dump(bundle, ROOT / "backend/artifacts/baseline.joblib")
    (ROOT / "backend/artifacts/metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(policy, indent=2))


if __name__ == "__main__":
    main()

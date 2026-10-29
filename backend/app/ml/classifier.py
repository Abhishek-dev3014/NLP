from typing import Protocol
from pathlib import Path
import json
import joblib
from app.core.config import settings
from app.ml.preprocessing import clean_text, tokens


class Classifier(Protocol):
    def predict(self, text: str) -> dict: ...


class BaselineClassifier:
    def __init__(self, path: str):
        bundle = joblib.load(path)  # Only load trusted, locally trained artifacts.
        self.pipeline = bundle["pipeline"]
        self.metadata = bundle["metadata"]
        self.metrics = bundle.get("metrics")

    def predict(self, text: str) -> dict:
        text = clean_text(text)
        vectorizer = self.pipeline.named_steps["tfidf"]
        model = self.pipeline.named_steps["classifier"]
        x = vectorizer.transform([text])
        probabilities = self.pipeline.predict_proba([text])[0]
        risk_index = list(model.classes_).index(1)
        risk = float(probabilities[risk_index])
        values = x.toarray()[0] * model.coef_[0]
        names = vectorizer.get_feature_names_out()
        indices = sorted(x.indices, key=lambda i: abs(values[i]), reverse=True)[:14]
        features = [
            {
                "term": str(names[i]),
                "contribution": round(float(values[i]), 6),
                "direction": "misleading" if values[i] > 0 else "credible",
            }
            for i in indices
            if values[i] != 0
        ]
        words = tokens(text)
        from app.ml.calibrated import POLITICAL

        political = POLITICAL
        coverage = sum(
            w in vectorizer.vocabulary_ or w.lower() in vectorizer.vocabulary_
            for w in words
        ) / max(1, len(words))
        in_domain = (
            bool(political.intersection(w.lower() for w in words))
            and len(words) <= 160
            and coverage >= 0.35
        )
        threshold = self.metadata.get("threshold", settings.uncertainty_threshold)
        confidence = max(risk, 1 - risk)
        label = (
            "Insufficient Evidence"
            if not in_domain
            else (
                "Needs Further Verification"
                if confidence < threshold
                else ("Potentially Misleading" if risk >= 0.5 else "Likely Credible")
            )
        )
        warnings = [
            "Uncalibrated model estimates describe similarity to training labels, not factual truth.",
            "Training data consists of US political claims from 2007–2016; source and time biases remain.",
            "Scope is screened using length, vocabulary and keywords. This heuristic does not prove that a claim is in-domain.",
        ]
        if not in_domain:
            warnings.append(
                "Input is outside the supported short US political-claim domain or has low vocabulary coverage. Do not rely on its classification."
            )
        return {
            "label": label,
            "confidence": confidence if in_domain else None,
            "probabilities": {"credible": 1 - risk, "misleading": risk}
            if in_domain
            else None,
            "confidence_threshold": threshold,
            "decision_reason": "The model found language associations, not factual evidence. Verify this claim with original sources."
            if in_domain
            else "Language review only. This input did not pass the short political-claim scope screen; a reliability score is withheld.",
            "model_name": "TF-IDF + Logistic Regression",
            "model_version": self.metadata["version"],
            "calibrated": False,
            "in_domain": in_domain,
            "features": features if in_domain else [],
            "warnings": warnings,
            "vocabulary_coverage": round(min(coverage, 1), 3),
        }


class TransformerClassifier:
    """Optional local fine-tuned model. No automatic weight downloads."""

    def __init__(self, path: str):
        from transformers import pipeline

        self.pipeline = pipeline(
            "text-classification",
            model=path,
            tokenizer=path,
            local_files_only=True,
            top_k=None,
        )
        config = json.loads((Path(path) / "verifact.json").read_text())
        self.labels = config["label_mapping"]
        self.version = config["version"]

    def predict(self, text: str) -> dict:
        scores = self.pipeline(clean_text(text), truncation=True, max_length=512)[0]
        probabilities = {
            self.labels[item["label"]]: float(item["score"]) for item in scores
        }
        if set(probabilities) != {"credible", "misleading"}:
            raise ValueError(
                "Transformer must provide binary credible/misleading probabilities"
            )
        confidence = max(probabilities.values())
        return {
            "label": "Insufficient Evidence",
            "confidence": confidence,
            "probabilities": probabilities,
            "model_name": "Local fine-tuned transformer",
            "model_version": self.version,
            "calibrated": False,
            "in_domain": False,
            "features": [],
            "warnings": [
                "Transformer domain validation and feature attribution are not configured. Estimates are uncalibrated."
            ],
            "vocabulary_coverage": None,
        }


def load_classifier() -> Classifier | None:
    path = settings.model_path
    if not Path(path).exists():
        return None
    if settings.model_type == "transformer":
        return TransformerClassifier(path)
    bundle = joblib.load(path)
    if bundle.get("kind") == "article-svm-v1":
        from app.ml.article_classifier import ArticleClassifier

        return ArticleClassifier(bundle)
    if bundle.get("kind") == "calibrated-hybrid-v2":
        from app.ml.calibrated import CalibratedClassifier

        return CalibratedClassifier(bundle)
    return BaselineClassifier(path)

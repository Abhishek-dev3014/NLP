"""Calibrated hybrid inference with additive feature-group explanations."""

import numpy as np
from app.ml.preprocessing import clean_text, tokens

POLITICAL = {
    "government",
    "president",
    "senate",
    "congress",
    "tax",
    "taxes",
    "budget",
    "election",
    "voters",
    "obama",
    "trump",
    "republican",
    "democrat",
    "federal",
    "unemployment",
    "medicare",
    "medicaid",
    "legislation",
    "governor",
    "senator",
    "congressional",
}


class CalibratedClassifier:
    def __init__(self, bundle):
        self.encoder = bundle["encoder"]
        self.model = bundle["classifier"]
        self.calibrator = bundle["calibrator"]
        self.metadata = bundle["metadata"]
        self.metrics = bundle["metrics"]
        if self.encoder.semantic_weight:
            from app.ml.features import sentence_encoder

            sentence_encoder()

    def predict(self, text):
        text = clean_text(text)
        words = [t.lower() for t in tokens(text)]
        vocabulary = self.encoder.word.vocabulary_
        coverage = sum(w in vocabulary for w in words) / max(1, len(words))
        in_domain = (
            len(words) <= self.metadata["max_claim_words"]
            and bool(POLITICAL.intersection(words))
            and coverage >= self.metadata["min_coverage"]
        )
        base = {
            "model_name": self.metadata["model_name"],
            "model_version": self.metadata["version"],
            "calibrated": True,
            "in_domain": in_domain,
            "vocabulary_coverage": round(coverage, 3),
            "confidence_threshold": self.metadata["threshold"],
            "attribution_method": "Word TF-IDF × coefficient × calibration slope. Character and semantic features are reported only as group totals.",
            "warnings": [
                "Calibration was assessed on historical US political claims, not arbitrary news or factual truth.",
                "Scope screening uses length, political terms, and vocabulary coverage. It is a heuristic, not a validated domain detector.",
            ],
        }
        if not in_domain:
            return {
                **base,
                "label": "Insufficient Evidence",
                "confidence": None,
                "probabilities": None,
                "features": [],
                "decision_reason": "Language review only: the input did not pass the short political-claim scope screen. Choose a specific claim below or inspect the language analysis.",
                "score_breakdown": None,
            }
        x = self.encoder.transform([text])
        logit = float(self.model.decision_function(x)[0])
        risk = float(self.calibrator.predict_proba([[logit]])[0, 1])
        slope = float(self.calibrator.coef_[0, 0])
        values = x.toarray()[0] * self.model.coef_[0] * slope
        names = self.encoder.word.get_feature_names_out()
        word_end = len(names)
        char_end = word_end + (
            len(self.encoder.char.get_feature_names_out())
            if self.encoder.char is not None
            else 0
        )
        indices = sorted(
            np.flatnonzero(values[:word_end]),
            key=lambda i: abs(values[i]),
            reverse=True,
        )[:14]
        features = [
            {
                "term": str(names[i]),
                "contribution": round(float(values[i]), 6),
                "direction": "misleading" if values[i] > 0 else "credible",
            }
            for i in indices
        ]
        breakdown = {
            "word": float(values[:word_end].sum()),
            "character": float(values[word_end:char_end].sum()),
            "semantic": float(values[char_end:].sum()),
            "intercept": float(
                self.model.intercept_[0] * slope + self.calibrator.intercept_[0]
            ),
        }
        confidence = max(risk, 1 - risk)
        uncertain = confidence < self.metadata["threshold"]
        return {
            **base,
            "label": "Needs Further Verification"
            if uncertain
            else ("Potentially Misleading" if risk >= 0.5 else "Likely Credible"),
            "confidence": confidence,
            "probabilities": {"credible": 1 - risk, "misleading": risk},
            "features": features,
            "score_breakdown": breakdown,
            "decision_reason": (
                "The model is below its validation-selected confidence threshold. Verify the claim using primary sources."
                if uncertain
                else "The model passed its confidence threshold for this dataset task. The claim still needs independent evidence."
            ),
        }

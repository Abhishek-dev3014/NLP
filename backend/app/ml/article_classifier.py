"""Article-level screening, separately disclosed from independent fact checking."""

import numpy as np
from app.ml.article_features import article_text
from app.ml.preprocessing import tokens


class ArticleClassifier:
    def __init__(self, bundle):
        self.vectorizer = bundle["vectorizer"]
        self.model = bundle["classifier"]
        self.calibrator = bundle["calibrator"]
        self.metadata = bundle["metadata"]
        self.metrics = bundle["metrics"]

    def predict(self, text: str) -> dict:
        cleaned = article_text(text)
        words = tokens(cleaned)
        original_words = len(tokens(text))
        x = self.vectorizer.transform([cleaned])
        logit = float(self.model.decision_function(x)[0])
        risk = float(self.calibrator.predict_proba([[logit]])[0, 1])
        confidence = max(risk, 1 - risk)
        coverage = sum(w in self.vectorizer.vocabulary_ for w in words) / max(
            1, len(words)
        )
        adequate = len(words) >= self.metadata["min_words"] and coverage >= 0.20
        uncertain = not adequate or confidence < self.metadata["threshold"]
        label = (
            "Needs Further Verification"
            if uncertain
            else ("Potentially Misleading" if risk >= 0.5 else "Likely Credible")
        )
        # Exact additive calibrated-logit contributions, not generated rationales.
        slope = float(self.calibrator.coef_[0, 0])
        row = x.tocsr()
        weighted = row.data * self.model.coef_[0, row.indices] * slope
        order = np.argsort(np.abs(weighted))[::-1][:14]
        names = self.vectorizer.get_feature_names_out()
        features = [
            {
                "term": str(names[row.indices[k]]),
                "contribution": round(float(weighted[k]), 6),
                "direction": "misleading" if weighted[k] > 0 else "credible",
            }
            for k in order
        ]
        warnings = [
            "This is a trained fake/real article-pattern prediction. No independent factual verification has been performed.",
            "Evaluation covers historical English news. Accuracy on current Indian news or other new domains has not been measured.",
            "Publisher and writing-style bias can affect the result even after obvious source markers are removed.",
        ]
        if not adequate:
            warnings.append(
                "This input has limited text or vocabulary overlap. Add the complete article; treat this estimate as preliminary."
            )
        if original_words > self.metadata["max_words"]:
            warnings.append(
                "Classification uses the first 2500 words; the remaining article is included in the language review only."
            )
        if uncertain:
            reason = "The model cannot make a strong fake/real distinction for this input. Its tentative class estimate is shown below; verify the main claims before sharing."
        elif risk >= 0.5:
            reason = "This article resembles examples labeled fake or misleading in the training corpus. Check the original reporting and primary evidence before trusting or sharing it."
        else:
            reason = "This article resembles examples labeled real in the training corpus. This is a credibility screening result; verify its specific claims and publication context."
        return {
            "label": label,
            "confidence": confidence,
            "probabilities": {"credible": 1 - risk, "misleading": risk},
            "model_name": self.metadata["model_name"],
            "model_version": self.metadata["version"],
            "calibrated": True,
            "in_domain": adequate,
            "features": features,
            "warnings": warnings,
            "vocabulary_coverage": round(coverage, 3),
            "confidence_threshold": self.metadata["threshold"],
            "decision_reason": reason,
            "assessment_scope": "article_screening",
            "factual_status": "Not independently verified",
            "evaluated_domain": "Historical English full-news benchmark; current Indian news not separately validated",
            "analyzed_words": min(original_words, self.metadata["max_words"]),
            "attribution_method": "TF-IDF × linear SVM coefficient × sigmoid-calibration slope. Signed contributions explain learned article-label associations, not factual truth.",
            "score_breakdown": {
                "words": float(weighted.sum()),
                "intercept": float(
                    self.model.intercept_[0] * slope + self.calibrator.intercept_[0]
                ),
            },
        }

from typing import Protocol
from pathlib import Path
import json
import joblib
import numpy as np
from app.core.config import settings
from app.ml.preprocessing import clean_text, tokens


class Classifier(Protocol):
    def predict(self, text: str) -> dict: ...


class BaselineClassifier:
    def __init__(self, path: str):
        bundle = joblib.load(path)  # Only load trusted, locally trained artifacts.
        self.pipeline = bundle['pipeline']
        self.metadata = bundle['metadata']

    def predict(self, text: str) -> dict:
        text = clean_text(text)
        vectorizer = self.pipeline.named_steps['tfidf']
        model = self.pipeline.named_steps['classifier']
        x = vectorizer.transform([text])
        probabilities = self.pipeline.predict_proba([text])[0]
        risk_index = list(model.classes_).index(1)
        risk = float(probabilities[risk_index])
        values = x.toarray()[0] * model.coef_[0]
        names = vectorizer.get_feature_names_out()
        indices = sorted(x.indices, key=lambda i: abs(values[i]), reverse=True)[:14]
        features = [{'term': str(names[i]), 'contribution': round(float(values[i]), 6),
                     'direction': 'misleading' if values[i] > 0 else 'credible'} for i in indices if values[i] != 0]
        words = tokens(text)
        coverage = float(len(x.indices) / max(1, len(words)))
        political = {'government', 'president', 'senate', 'congress', 'tax', 'taxes', 'state', 'states', 'budget', 'election', 'voters', 'obama', 'trump', 'republican', 'democrat', 'federal', 'jobs', 'health', 'care', 'law', 'bill', 'unemployment', 'spending', 'million', 'billion', 'percent'}
        in_domain = bool(political.intersection(w.lower() for w in words)) and len(words) <= 160 and coverage >= .12
        confidence = max(risk, 1 - risk)
        label = 'Insufficient Evidence' if not in_domain else ('Needs Further Verification' if confidence < settings.uncertainty_threshold else ('Potentially Misleading' if risk >= .5 else 'Likely Credible'))
        warnings = ['Uncalibrated model estimates describe similarity to training labels, not factual truth.',
                    'Training data consists of US political claims from 2007–2016; source and time biases remain.']
        if not in_domain:
            warnings.append('Input is outside the supported short US political-claim domain or has low vocabulary coverage. Do not rely on its classification.')
        return {'label': label, 'confidence': confidence, 'probabilities': {'credible': 1 - risk, 'misleading': risk},
                'model_name': 'TF-IDF + Logistic Regression', 'model_version': self.metadata['version'],
                'calibrated': False, 'in_domain': in_domain, 'features': features, 'warnings': warnings,
                'vocabulary_coverage': round(min(coverage, 1), 3)}


class TransformerClassifier:
    """Optional local fine-tuned model. No automatic weight downloads."""
    def __init__(self, path: str):
        from transformers import pipeline
        self.pipeline = pipeline('text-classification', model=path, tokenizer=path, local_files_only=True, top_k=None)
        config = json.loads((Path(path) / 'verifact.json').read_text())
        self.labels = config['label_mapping']
        self.version = config['version']

    def predict(self, text: str) -> dict:
        scores = self.pipeline(clean_text(text), truncation=True, max_length=512)[0]
        probabilities = {self.labels[item['label']]: float(item['score']) for item in scores}
        if set(probabilities) != {'credible', 'misleading'}:
            raise ValueError('Transformer must provide binary credible/misleading probabilities')
        confidence = max(probabilities.values())
        return {'label': 'Insufficient Evidence', 'confidence': confidence, 'probabilities': probabilities,
                'model_name': 'Local fine-tuned transformer', 'model_version': self.version, 'calibrated': False,
                'in_domain': False, 'features': [], 'warnings': ['Transformer domain validation and feature attribution are not configured. Estimates are uncalibrated.'], 'vocabulary_coverage': None}


def load_classifier() -> Classifier | None:
    path = settings.model_path
    if not Path(path).exists():
        return None
    return TransformerClassifier(path) if settings.model_type == 'transformer' else BaselineClassifier(path)

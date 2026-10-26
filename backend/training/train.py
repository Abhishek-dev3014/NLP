"""Reproducible, text-only binary LIAR baseline. No metadata enters features."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from app.ml.preprocessing import clean_text

LABELS = {'true': 0, 'mostly-true': 0, 'false': 1, 'pants-fire': 1}
ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--output', type=Path, default=ROOT / 'backend/artifacts')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    frames = []
    for split in ['train', 'valid', 'test']:
        path = args.data / f'{split}.tsv'
        if not path.exists():
            raise SystemExit(f'Missing {path}. Run python -m training.download_data first.')
        frame = pd.read_csv(path, sep='\t', header=None, quoting=3, dtype=str)
        frame = frame[frame[1].isin(LABELS)].copy()
        frame['label'] = frame[1].map(LABELS)
        frame['text'] = frame[2].map(clean_text)
        frame['split'] = split
        frames.append(frame[['text', 'label', 'split']])
    data = pd.concat(frames, ignore_index=True)
    before = len(data)
    data['normalized'] = data.text.map(lambda t: re.sub(r'\W+', '', t.lower()))
    data = data.drop_duplicates('normalized').reset_index(drop=True)
    exact_removed = before - len(data)
    # Detect near duplicates across all splits without using class labels.
    fingerprints = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=50000).fit_transform(data.text)
    neighbors = NearestNeighbors(metric='cosine', algorithm='brute', radius=.08, n_jobs=1).fit(fingerprints).radius_neighbors(fingerprints, return_distance=False)
    drop = set()
    for i, matches in enumerate(neighbors):
        if i not in drop:
            drop.update(int(j) for j in matches if j > i)
    data = data.drop(index=list(drop))
    train, valid, test = [data[data.split == s] for s in ['train', 'valid', 'test']]
    best, best_score, best_c = None, -1, None
    validation = []
    for c in [.5, 1., 2., 4.]:
        pipeline = Pipeline([('tfidf', TfidfVectorizer(preprocessor=clean_text, lowercase=True, ngram_range=(1, 2), min_df=2, max_df=.98, sublinear_tf=True, max_features=40000)), ('classifier', LogisticRegression(C=c, max_iter=1500, class_weight='balanced', random_state=args.seed))])
        pipeline.fit(train.text, train.label)
        score = float(f1_score(valid.label, pipeline.predict(valid.text)))
        validation.append({'C': c, 'f1': score})
        if score > best_score:
            best, best_score, best_c = pipeline, score, c
    predicted = best.predict(test.text)
    probabilities = best.predict_proba(test.text)[:, 1]
    data_hash = hashlib.sha256('\n'.join(train.text).encode()).hexdigest()[:12]
    version = f'liar-binary-{data_hash}'
    metrics = {'model_name': 'TF-IDF + Logistic Regression', 'version': version, 'dataset': 'LIAR (Wang, ACL 2017), binary subset',
               'dataset_url': 'https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip', 'dataset_size': len(data),
               'class_distribution': {'credible': int((data.label == 0).sum()), 'misleading': int((data.label == 1).sum())},
               'split': {'train': len(train), 'validation': len(valid), 'test': len(test)},
               'split_method': 'Original official splits; exact and near duplicates removed globally, keeping the earliest split. No speaker metadata used. Speakers can overlap between splits; this is not a source-held-out benchmark.',
               'duplicates_removed': {'exact': exact_removed, 'near': len(drop), 'near_cosine_threshold': .92},
               'label_mapping': {'credible': ['true', 'mostly-true'], 'misleading': ['false', 'pants-fire'], 'excluded': ['half-true', 'barely-true']},
               'accuracy': float(accuracy_score(test.label, predicted)), 'precision': float(precision_score(test.label, predicted)),
               'recall': float(recall_score(test.label, predicted)), 'f1': float(f1_score(test.label, predicted)), 'roc_auc': float(roc_auc_score(test.label, probabilities)),
               'confusion_matrix': confusion_matrix(test.label, predicted, labels=[0, 1]).tolist(),
               'classification_report': classification_report(test.label, predicted, target_names=['credible', 'misleading'], output_dict=True),
               'validation_search': validation, 'selected_C': best_c, 'seed': args.seed, 'calibrated': False,
               'evaluated_at': datetime.now(timezone.utc).isoformat(),
               'limitations': ['Short US political statements from 2007–2016, not general news articles.', 'Text patterns alone cannot verify factual truth.', 'Middle truthfulness labels are excluded; this is not the original six-class LIAR task.', 'Uncalibrated probabilities may be overconfident and should not be interpreted as truth probabilities.', 'Speakers, topics, and political framing may overlap across official splits. Near-duplicate filtering reduces, but cannot eliminate, leakage.', 'Language and sentiment heuristics do not establish misinformation.'],
               'license_note': 'Original LIAR distribution contains no explicit blanket license grant. Underlying PolitiFact content may have separate terms. Data is downloaded locally and not redistributed; review rights for your intended use.'}
    args.output.mkdir(parents=True, exist_ok=True)
    joblib.dump({'pipeline': best, 'metadata': {'version': version, 'seed': args.seed}}, args.output / 'baseline.joblib')
    (args.output / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps({k: metrics[k] for k in ['version', 'split', 'accuracy', 'precision', 'recall', 'f1', 'roc_auc']}, indent=2))

if __name__ == '__main__':
    main()

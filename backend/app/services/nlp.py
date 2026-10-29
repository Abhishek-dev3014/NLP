"""Local trained linguistic pipeline; deterministic extractive summaries."""

from collections import Counter
from functools import lru_cache
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@lru_cache(maxsize=1)
def pipeline():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return None


def explore(text: str, doc=None) -> dict:
    nlp = pipeline()
    if nlp is None:
        return {
            "available": False,
            "message": "Install en_core_web_sm to enable grammatical analysis and entity recognition.",
        }
    if doc is None:
        doc = nlp(text)
    sentences = [s for s in doc.sents if s.text.strip()]
    # Bound pairwise work for very long documents; tell the reader the actual scope.
    candidates = []
    seen = set()
    for sentence in sentences[:200]:
        fingerprint = sentence.text.strip().casefold()
        if fingerprint not in seen and sum(t.is_alpha for t in sentence) >= 5:
            candidates.append(sentence)
            seen.add(fingerprint)
    ranked = []
    if candidates:
        try:
            matrix = TfidfVectorizer(
                stop_words="english", sublinear_tf=True
            ).fit_transform([s.text for s in candidates])
            # Centrality to the document centroid; no generative or factual inference.
            scores = np.asarray(matrix @ matrix.mean(axis=0).T).ravel()
            order = sorted(
                range(len(candidates)), key=lambda k: float(scores[k]), reverse=True
            )[:3]
            ranked = [candidates[k] for k in sorted(order)]
        except ValueError:
            ranked = candidates[:3]
    counts = Counter(
        t.lemma_.lower()
        for t in doc
        if t.pos_ in {"NOUN", "PROPN"} and t.is_alpha and not t.is_stop
    )
    representative = next(
        (s for s in sentences if 5 <= len(s) <= 35), sentences[0] if sentences else None
    )
    syntax = []
    if representative is not None:
        syntax = [
            {
                "text": t.text,
                "relation": t.dep_,
                "head": t.head.text,
                "start": t.idx,
                "head_start": t.head.idx,
            }
            for t in list(representative)[:35]
        ]
    unique_entities = {}
    for entity in doc.ents:
        key = (entity.text.casefold(), entity.label_)
        if key not in unique_entities:
            unique_entities[key] = entity
    return {
        "available": True,
        "pipeline": f"en_core_web_sm {nlp.meta['version']}",
        "method": "Trained spaCy POS, lemma, dependency and named-entity pipeline. Summary: TF-IDF centroid sentence ranking. Topics: noun-lemma frequency.",
        "summary": [
            {"text": s.text, "start": s.start_char, "end": s.end_char} for s in ranked
        ],
        "summary_scope": f"Extracted from the first {min(len(sentences), 200)} of {len(sentences)} sentences. Original wording is preserved; importance is estimated, not verified.",
        "entities": [
            {
                "text": e.text,
                "label": e.label_,
                "start": e.start_char,
                "end": e.end_char,
            }
            for e in list(unique_entities.values())[:50]
        ],
        "topics": [
            {"term": term, "count": count} for term, count in counts.most_common(10)
        ],
        "tokens": [
            {
                "text": t.text,
                "lemma": t.lemma_,
                "pos": t.pos_,
                "morphology": str(t.morph),
                "start": t.idx,
                "end": t.idx + len(t.text),
            }
            for t in list(doc)[:120]
            if not t.is_space
        ],
        "token_count": len(doc),
        "pos_counts": dict(Counter(t.pos_ for t in doc if not t.is_space)),
        "dependencies": syntax,
        "sentence_count": len(sentences),
        "dependency_sentence": representative.text
        if representative is not None
        else "",
    }

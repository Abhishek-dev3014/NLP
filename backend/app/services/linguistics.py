import re
from app.ml.preprocessing import tokens, sentences

PATTERNS = {
    'emotional': (r'\b(shocking|outrage|terrifying|disaster|miracle|horrifying|unbelievable|furious|panic|fear|destroy|crisis)\b', 'Emotionally charged wording; this does not establish whether a claim is false.'),
    'clickbait': (r"\b(you won.t believe|what happened next|they don.t want you to know|share before|breaking|secret revealed)\b", 'Attention or urgency cue, identified by a phrase-matching heuristic.'),
    'certainty': (r'\b(always|never|everyone|guaranteed|undeniable|100 percent|without a doubt|proves)\b', 'Absolute certainty cue; check the supporting evidence.')
}
POSITIVE = {'good', 'growth', 'improve', 'improved', 'success', 'benefit', 'peace', 'safe', 'better', 'gain'}
NEGATIVE = {'bad', 'crisis', 'fear', 'loss', 'danger', 'disaster', 'failed', 'harm', 'war', 'worse'}


def analyze_language(text: str) -> tuple[dict, list, list]:
    words = tokens(text)
    spans = sentences(text)
    lower = [w.lower() for w in words]
    hits = []
    for kind, (pattern, reason) in PATTERNS.items():
        for match in re.finditer(pattern, text, re.I):
            hits.append({'start': match.start(), 'end': match.end(), 'text': match.group(), 'kind': kind, 'reason': reason})
    pos, neg = sum(w in POSITIVE for w in lower), sum(w in NEGATIVE for w in lower)
    insights = {'word_count': len(words), 'character_count': len(text), 'sentence_count': len(spans),
                'average_sentence_length': round(len(words) / max(1, len(spans)), 1),
                'sentiment_score': round((pos - neg) / max(1, pos + neg), 3), 'subjectivity_score': None,
                'clickbait_indicator': sum(h['kind'] == 'clickbait' for h in hits),
                'emotional_indicator': sum(h['kind'] == 'emotional' for h in hits),
                'certainty_indicator': sum(h['kind'] == 'certainty' for h in hits),
                'method': 'Transparent lexicon counts and untrained Punkt sentence segmentation. Sentiment is a small lexical balance, not a contextual sentiment model. Subjectivity is not implemented.'}
    claims = []
    for sentence, start, end in spans:
        if len(tokens(sentence)) >= 6 and re.search(r'\d|\b(is|are|was|were|has|have|will|increased|decreased|said|reported)\b', sentence, re.I):
            claims.append({'text': sentence, 'start': start, 'end': end, 'reason': 'Contains a number or a factual-style predicate. Candidate selection is a linguistic heuristic, not verified claim detection.', 'status': 'Not verified'})
        if len(claims) >= 6:
            break
    return insights, sorted(hits, key=lambda h: h['start']), claims

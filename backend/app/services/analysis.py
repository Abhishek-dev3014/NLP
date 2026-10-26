from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.analysis import Analysis, AnalysisInsight, ExtractedClaim, EvidenceSource
from app.schemas.analysis import TextInput
from app.services.linguistics import analyze_language
from app.services.evidence import retrieve_evidence


def create_analysis(payload: TextInput, session_id: str, db: Session, classifier) -> dict:
    text = payload.text
    # Language validation is deterministic for script; probabilistic detection is used only on longer inputs.
    from langdetect import detect, DetectorFactory, LangDetectException
    DetectorFactory.seed = 42
    try:
        if len(text.split()) >= 20 and detect(text) != 'en':
            raise HTTPException(422, 'This model currently supports English content. Please submit an English article.')
    except LangDetectException:
        raise HTTPException(422, 'The language could not be identified. Please provide more English text.')
    insights, highlights, claims = analyze_language(text)
    if classifier:
        prediction = classifier.predict(f'{payload.headline} {text}'.strip())
    else:
        prediction = {'label': 'Insufficient Evidence', 'confidence': None, 'probabilities': None, 'model_name': 'Unavailable', 'model_version': 'untrained', 'calibrated': False, 'in_domain': False, 'features': [], 'warnings': ['No trained model is loaded. Train the baseline to enable predictions. Language heuristics remain available.']}
    features = prediction['features'][:3]
    explanation = 'The linear model found ' + ', '.join('“' + f['term'] + '”' for f in features) + ' among the strongest active TF-IDF feature contributions. Contributions describe learned language associations, not evidence of truth.' if features else 'Model feature attributions are unavailable. The language observations below are separately labeled heuristics.'
    evidence = retrieve_evidence(payload.headline or (claims[0]['text'] if claims else text[:300]), payload.allow_external_evidence)
    report = {'id': str(uuid4()), 'headline': payload.headline.strip() or 'Untitled analysis', 'text': text, 'source_url': payload.source_url,
              'input_type': payload.input_type, 'created_at': datetime.now(timezone.utc).isoformat(), 'prediction': prediction,
              'insights': insights, 'highlights': highlights, 'claims': claims, 'evidence': evidence, 'explanation': explanation,
              'recommendations': ['Check the original source and its publication date.', 'Compare independent reporting and supporting primary documents.', 'Verify the highlighted factual statements before sharing.', 'Treat language patterns and model confidence as prompts for investigation.']}
    row = Analysis(id=report['id'], session_id=session_id, headline=report['headline'], article_text=text, source_url=payload.source_url, input_type=payload.input_type,
                   predicted_label=prediction['label'], prediction_confidence=prediction['confidence'], model_name=prediction['model_name'], model_version=prediction['model_version'], report=report)
    row.insights = AnalysisInsight(sentiment_score=insights['sentiment_score'], subjectivity_score=None, word_count=insights['word_count'], sentence_count=insights['sentence_count'], clickbait_indicator=insights['clickbait_indicator'], explanation={'prediction': prediction, 'insights': insights, 'highlights': highlights})
    row.claims = [ExtractedClaim(claim_text=c['text'], claim_position=c['start'], verification_status=c['status']) for c in claims]
    if row.claims:
        row.claims[0].evidence = [EvidenceSource(source_title=e['title'], source_url=e['url'], source_name=e['source_name'], publication_date=e['publication_date'], evidence_status=e['status']) for e in evidence['items']]
    db.add(row)
    db.commit()
    return report

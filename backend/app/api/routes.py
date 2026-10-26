import json
from pathlib import Path
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.analysis import Analysis
from app.schemas.analysis import TextInput, URLInput, AnalysisReport, AnalysisList
from app.services.analysis import create_analysis
from app.services.extraction import extract_url, extract_file
from app.core.config import settings

router = APIRouter(prefix='/api')

@router.get('/health')
def health(request: Request):
    return {'status': 'ok', 'model_loaded': request.app.state.classifier is not None, 'model_type': settings.model_type, 'evidence_configured': bool(settings.evidence_enabled and settings.fact_check_api_key)}

@router.post('/analyze/text', response_model=AnalysisReport)
def analyze_text(payload: TextInput, request: Request, db: Session = Depends(get_db)):
    return create_analysis(payload, request.state.session_id, db, request.app.state.classifier)

@router.post('/extract/url')
def preview_url(payload: URLInput):
    return extract_url(payload.url)

@router.post('/analyze/url', response_model=AnalysisReport)
def analyze_url(payload: URLInput, request: Request, db: Session = Depends(get_db)):
    extracted = extract_url(payload.url)
    return create_analysis(TextInput(**extracted, input_type='url', allow_external_evidence=payload.allow_external_evidence), request.state.session_id, db, request.app.state.classifier)

@router.post('/extract/file')
def preview_file(file: UploadFile = File(...)):
    return extract_file(file.filename or '', file.content_type or '', file.file.read(settings.max_upload_bytes + 1))

@router.post('/analyze/file', response_model=AnalysisReport)
def analyze_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    extracted = extract_file(file.filename or '', file.content_type or '', file.file.read(settings.max_upload_bytes + 1))
    return create_analysis(TextInput(**extracted, input_type='file'), request.state.session_id, db, request.app.state.classifier)

@router.get('/analyses', response_model=AnalysisList)
def list_analyses(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), search: str = Query('', max_length=300), label: str = '', order: str = 'newest', db: Session = Depends(get_db)):
    filters = [Analysis.session_id == request.state.session_id]
    if search:
        escaped = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        filters.append(Analysis.headline.ilike(f'%{escaped}%', escape='\\'))
    if label:
        filters.append(Analysis.predicted_label == label)
    total = db.scalar(select(func.count()).select_from(Analysis).where(*filters))
    rows = db.scalars(select(Analysis).where(*filters).order_by(Analysis.created_at.asc() if order == 'oldest' else Analysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': [r.report for r in rows], 'total': total, 'page': page, 'page_size': page_size}

@router.get('/analyses/{analysis_id}', response_model=AnalysisReport)
def get_analysis(analysis_id: str, request: Request, db: Session = Depends(get_db)):
    row = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.session_id == request.state.session_id))
    if not row:
        raise HTTPException(404, 'This analysis was not found in your browser session. It may have been deleted.')
    return row.report

@router.delete('/analyses/{analysis_id}', status_code=204)
def delete_analysis(analysis_id: str, request: Request, db: Session = Depends(get_db)):
    row = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.session_id == request.state.session_id))
    if not row:
        raise HTTPException(404, 'Analysis not found in your session.')
    db.delete(row)
    db.commit()

@router.delete('/analyses', status_code=204)
def clear_history(request: Request, db: Session = Depends(get_db)):
    for row in db.scalars(select(Analysis).where(Analysis.session_id == request.state.session_id)):
        db.delete(row)
    db.commit()

@router.get('/dashboard/stats')
def dashboard(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(Analysis).where(Analysis.session_id == request.state.session_id).order_by(Analysis.created_at)).all()
    distribution, activity = {}, {}
    indicators = {'Emotional': 0, 'Clickbait': 0, 'Certainty': 0}
    for row in rows:
        distribution[row.predicted_label] = distribution.get(row.predicted_label, 0) + 1
        day = row.created_at.date().isoformat()
        point = activity.setdefault(day, {'date': day, 'count': 0, 'confidences': []})
        point['count'] += 1
        if row.prediction_confidence is not None:
            point['confidences'].append(row.prediction_confidence)
        insights = row.report['insights']
        for label, key in [('Emotional', 'emotional_indicator'), ('Clickbait', 'clickbait_indicator'), ('Certainty', 'certainty_indicator')]:
            indicators[label] += insights[key]
    return {'total': len(rows), 'distribution': [{'name': k, 'value': v} for k, v in distribution.items()],
            'activity': [{'date': p['date'], 'count': p['count'], 'confidence': round(sum(p['confidences']) / len(p['confidences']) * 100, 1) if p['confidences'] else None} for p in activity.values()],
            'indicators': [{'name': k, 'value': v} for k, v in indicators.items()], 'recent': [r.report for r in rows[-5:][::-1]]}

@router.get('/model/metrics')
def metrics():
    path = Path(settings.metrics_path)
    if not path.exists():
        return {'available': False, 'message': 'No evaluation artifacts are available. Follow the training instructions to generate genuine metrics.'}
    return {'available': True, **json.loads(path.read_text())}

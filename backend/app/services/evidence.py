from urllib.parse import urlsplit
import httpx
from app.core.config import settings


def retrieve_evidence(query: str, consent: bool) -> dict:
    if not settings.evidence_enabled or not settings.fact_check_api_key:
        return {'status': 'unconfigured', 'message': 'External fact-check evidence is not configured. This assessment is based on NLP analysis only.', 'items': []}
    if not consent:
        return {'status': 'disabled', 'message': 'External evidence was not requested. Your content was not sent to the evidence provider.', 'items': []}
    try:
        response = httpx.get('https://factchecktools.googleapis.com/v1alpha1/claims:search', params={'key': settings.fact_check_api_key, 'query': query[:500], 'languageCode': 'en', 'pageSize': 5}, timeout=8)
        response.raise_for_status()
        items = []
        for claim in response.json().get('claims', []):
            for review in claim.get('claimReview', []):
                url = review.get('url', '')
                if urlsplit(url).scheme not in {'http', 'https'}:
                    continue
                items.append({'source_name': review.get('publisher', {}).get('name', 'Fact-check publisher'), 'title': review.get('title', 'Related fact-check'), 'url': url, 'publication_date': review.get('reviewDate'), 'summary': f"Reviewed claim: {claim.get('text', '')}. Publisher rating: {review.get('textualRating', 'Not supplied')}. This may concern a different claim.", 'status': 'Related evidence, inconclusive'})
        return {'status': 'related' if items else 'none', 'message': 'Retrieved related fact-checks. Relevance and factual relationships require human review.' if items else 'No evidence found for this query; absence of evidence does not establish truth.', 'items': items}
    except (httpx.HTTPError, ValueError):
        return {'status': 'unavailable', 'message': 'Evidence service unavailable. Your NLP analysis is still available.', 'items': []}

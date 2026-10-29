# API guide

FastAPI's generated interactive schema is at `http://127.0.0.1:8000/docs`, and the complete machine-readable contract is `/openapi.json`. The frontend uses `/api/*` through its same-origin Next.js proxy.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API/model/evidence configuration status |
| POST | `/api/analyze/text` | Validate, run NLP, persist, return actual report |
| POST | `/api/extract/url` | Safely extract text for user review |
| POST | `/api/extract/file` | Read TXT/PDF text for user review |
| POST | `/api/analyze/url` | Extract and immediately analyze (programmatic clients) |
| POST | `/api/analyze/file` | Extract and immediately analyze multipart `file` |
| GET | `/api/analyses` | Session-scoped, paginated reports |
| GET | `/api/analyses/{id}` | Authorized stored report |
| DELETE | `/api/analyses/{id}` | Delete one authorized report |
| DELETE | `/api/analyses` | Delete current session's reports and related records |
| GET | `/api/dashboard/stats` | Actual session aggregates, activity, indicators, recent reports |
| GET | `/api/model/metrics` | Real evaluation artifact or honest unavailable state |

## Cookie-preserving example

The content below is an unverified demonstration claim, not verified reporting.

```bash
curl -c /tmp/verifact-cookies.txt -b /tmp/verifact-cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"headline":"Federal spending claim","text":"The federal government spends more money on public education than on national defense. The proposed budget will increase education funding by twenty percent next year, according to the statement."}' \
  http://127.0.0.1:8000/api/analyze/text

curl -b /tmp/verifact-cookies.txt \
  'http://127.0.0.1:8000/api/analyses?page=1&page_size=10&order=newest'

curl -b /tmp/verifact-cookies.txt http://127.0.0.1:8000/api/dashboard/stats
```

Use the returned `id` for retrieval/deletion; never assume an ID or prediction value. `search` matches literal headline substrings; `label` filters by exact assessment name; `order=oldest|newest` controls chronology. Page size is bounded to 50.

## Report structure

`AnalysisReport` is fully modeled in Pydantic and mirrored in `frontend/src/lib/types.ts`:

- `id`, `headline`, cleaned `text`, `source_url`, `input_type`, UTC ISO `created_at`.
- `prediction`: assessment `label`, nullable `confidence` and class `probabilities`, actual `model_name`/`model_version`, `calibrated`, `in_domain`, signed `features`, `warnings`, and vocabulary coverage heuristic.
- `insights`: counts, average sentence length, lexical sentiment, nullable subjectivity, heuristic counts, and method disclosure.
- `highlights`: exact character offsets, matched text, category, and reason. Offsets reference the returned cleaned article text.
- `claims`: exact candidate text, character offsets, heuristic reason, and `Not verified` status.
- `evidence`: configuration/retrieval status, explanation, and actual retrieved source records only.
- `explanation`: deterministic description grounded in the model's strongest active feature contributions.
- `recommendations`: source-checking actions, with explicit uncertainty.

Unavailable model probabilities and subjectivity use `null`, never a made-up number. Evidence items have source name/title, HTTP(S) URL, optional publication date, publisher context, and a relationship status. Keyword overlap never establishes supporting/contradicting evidence.

## Extraction and limits

Text: 12 words minimum, 60,000 characters maximum, English only. Optional headline: 300 characters. Upload: 5 MB maximum; TXT UTF-8 or unencrypted, text-based PDF with at most 50 pages. PDFs are parsed in a time-limited disposable process. Scanned PDFs require external OCR before use.

URL extraction permits public HTTP(S), ports 80/443, no credentials, no private/loopback/link-local/reserved addresses. DNS answers are validated and the connection is pinned to a validated IP with the original TLS SNI and Host. Each redirect is validated independently, with at most four hops, response-type checks, timeouts, and a 2 MB response cap. Paywalls are not bypassed.

## Errors

Errors return a concise `{ "detail": "Actionable explanation" }`, without article content or exception traces. Typical codes: 422 validation/extraction, 413 limits, 415 unsupported file, 403 wrong Origin, 404 unauthorized/missing report, 429 request limit, 503 storage/backend unavailable. A failed persistence transaction never reports a successful saved analysis. The frontend proxy times out in 40 seconds; if interrupted, check history before resubmitting.

## NLP exploration (v2)

`POST /api/nlp/explore` accepts the same validated `text` shape as text analysis (English, minimum 12 words, maximum 60,000 characters). It returns pipeline availability, extractive summary spans, entities, topics, tokens/lemmas/POS/morphology, and dependency annotations. It does not persist an analysis or contact an external service.

New analysis reports include optional `nlp` details. Older saved reports remain readable. Prediction may include `confidence_threshold`, `decision_reason`, `attribution_method`, and calibrated `score_breakdown`. Out-of-scope new predictions have null confidence/probabilities. `/api/model/metrics` includes the actual active confidence policy and a separately labeled experimental evaluation when available, and returns unavailable if the loaded model and evaluation do not match.

### Article prediction fields

The current model adds `assessment_scope: "article_screening"`, `factual_status: "Not independently verified"`, `evaluated_domain`, and `analyzed_words`. Unlike legacy scope abstention, full articles receive numerical model estimates; short/low-coverage text remains uncertain. `in_domain` is a legacy input-sufficiency flag, not evidence of real-world domain validation. The frontend explicitly displays the evaluated-domain limitation. Metrics include a separate `calibration` split and `domain_stress` diagnostic; do not pool it with article-test metrics.

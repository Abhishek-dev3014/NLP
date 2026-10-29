# VeriFact AI

**Think Critically. Verify Intelligently.**

Fake News Detection and Misinformation Analysis Using Natural Language Processing — a full-stack university project with a genuine trainable classifier, transparent model explanations, and a polished research workspace.

An NLP classifier identifies language associated with its training labels. It **cannot independently verify factual truth**. Model outputs, linguistic heuristics, and external factual evidence are deliberately presented separately.

## Current release: full-article screening

The default model is now **TF-IDF + a calibrated linear SVM trained on WELFake articles**. On 12,110 group-held-out articles it reached **96.3% accuracy, 96.5% precision, 95.0% recall and 95.7% F1**. These are dataset-specific results: a separate short-claim stress test reached 47.2%, and current Indian news accuracy has not been measured. The app shows a model prediction and a separate **Not independently verified** status.

MSN public article links now extract correctly, including the supplied Siddaramaiah article. URL failures offer actionable errors and a paste-text fallback. Full articles receive a prediction instead of the old 160-word abstention screen.

See the [current model card, label audit and reproduction guide](docs/ARTICLE-MODEL.md), [syllabus mapping](docs/SYLLABUS.md), and [archived LIAR experiment](docs/IMPROVEMENT-REPORT.md). On this prepared desktop, run `./scripts/dev.sh`; restart the backend to load new model weights.

## What works

- Next.js App Router application: landing, analyzer, results, dashboard, history, methodology, model performance, about, and privacy/settings.
- Strict TypeScript, Tailwind CSS, shadcn-style Radix UI primitives, Lucide icons, Motion, React Hook Form/Zod, TanStack Query, and Recharts.
- Dark/light themes with local preference persistence, responsive workspace/sidebar, reduced-motion support, keyboard input tabs, accessible confirmation dialogs, and print layouts.
- Text analysis; safe public URL extraction with editable review; TXT and text-based PDF extraction with editable review.
- Actual scikit-learn TF-IDF + calibrated linear SVM inference, signed feature contributions, explicit uncertainty and domain limitations, linguistic indicators, and exact candidate claim excerpts.
- SQLAlchemy database persistence, session-isolated history, search/filter/sort/pagination, deletion, JSON exports, summary copy, browser print/PDF, and real dashboard aggregates.
- Alembic migrations; durable SQLite local development; optional PostgreSQL/Supabase connection configuration.
- Optional, consent-based Google Fact Check Tools search. Missing credentials result in a clear unavailable state, never invented sources.
- Real training/evaluation pipeline with six lexical/semantic candidates, out-of-fold calibration, retrospective test comparison, and validation-selected abstention.
- Trained spaCy entities, POS, lemmas, morphology, dependency inspection, extractive summaries, recurring topics, and an interactive NLP lab.

## Quick start

Requirements: **Python 3.11+**, **Node.js 20.9+**, npm, and internet access for the initial package/data download. The implementation was tested here with Python 3.13 and Node 24. No paid service is needed.

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
./scripts/setup-nlp.sh
npm --prefix frontend ci
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

The local configuration stores history in `backend/verifact.db` when the backend starts from its directory. Use a strong session secret for anything beyond a personal local demo:

```bash
.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

Put that value in `backend/.env` as `SESSION_SECRET`. If unset, the application creates a private, ignored `backend/.session-secret` file which persists across restarts. Never commit either file.

### Get the article data and train (fresh checkouts)

```bash
.venv/bin/python -m pip install -r backend/requirements-articles.txt
cd backend
../.venv/bin/python -m training.download_articles
../.venv/bin/python -m training.download_data
../.venv/bin/python -m training.articles
../.venv/bin/alembic upgrade head
```

The original article corpus is approximately 245 MB. The downloader verifies its checksum. Training creates `backend/artifacts/articles/model.joblib` and matching `metrics.json`, plus split and test-prediction audit artifacts. All data and weights are already prepared in this working directory; do not retrain merely to start the website. See the model card for the source license and numeric-label discrepancy.

Without model weights, the API provides language observations and explicitly marks classification unavailable.

### Start both services

From the root:

```bash
./scripts/dev.sh
```

Or in two terminals:

```bash
# Terminal 1, from the root
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# Terminal 2, from the root
cd frontend
npm run dev
```

Open **http://127.0.0.1:3000**. API docs: **http://127.0.0.1:8000/docs**. Use the same host consistently; `FRONTEND_ORIGIN` defaults to `http://127.0.0.1:3000`. If you prefer `localhost`, update that variable and restart the backend.

## Folder structure

```text
NLP/
├── frontend/
│   ├── src/app/                 # App Router pages + same-origin API proxy
│   ├── src/components/          # Analyzer, report, charts, tables, layout
│   │   └── ui/                  # shadcn-style Button and Radix dialog
│   ├── src/lib/                 # Typed contracts, API client, utilities
│   ├── tests/                   # Component tests and browser smoke tests
│   ├── .env.example
│   └── package.json / package-lock.json
├── backend/
│   ├── app/
│   │   ├── api/                 # Validated routes
│   │   ├── core/                # Settings and streamed body limits
│   │   ├── db/                  # Engine, sessions, declarative base
│   │   ├── ml/                  # Cleaning, tokenization, inference adapter
│   │   ├── models/              # Analysis/insight/claim/evidence relationships
│   │   ├── schemas/             # Typed Pydantic contracts
│   │   └── services/            # Orchestration, extraction, NLP, evidence
│   ├── training/                # Original LIAR ingestion + real training
│   ├── alembic/                 # Versioned schema migration
│   ├── artifacts/metrics.json   # Genuine holdout evaluation
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── requirements.lock.txt
├── data/raw/                    # Local dataset, ignored
├── docs/                        # Architecture, API, dataset/model card
├── scripts/                     # Development/training entry points
├── compose.yaml                 # Optional local PostgreSQL
└── README.md
```

## Architecture

```text
Next.js form → same-origin API proxy → FastAPI input/session validation
  → shared text normalization → fitted TF-IDF → linear SVM → sigmoid calibration
  → signed feature contributions + separate linguistic heuristics
  → local spaCy annotations + TF-IDF extractive summary
  → optional consent-based evidence lookup → SQLAlchemy transaction
  → typed JSON → report / history / dashboard visualizations
```

See [architecture and privacy boundaries](docs/ARCHITECTURE.md) and [API documentation](docs/API.md).

## Dataset and methodology

The active model uses full English article bodies from WELFake, with source-marker scrubbing, exact duplicate removal, approximate-duplicate grouping, and separate train/validation/calibration/test partitions. It is evaluated against inherited dataset labels, which may reflect publisher reputation rather than individual fact checks. Source/time shortcuts remain. A high confidence score does not establish truth.

See [the active article model card](docs/ARTICLE-MODEL.md) for precise methods, metrics, provenance and limitations. [The legacy LIAR model card](docs/DATASET.md) and [its experiments](docs/IMPROVEMENT-REPORT.md) remain available for comparison; their scores concern a different task.

Attribution is `TF-IDF value × SVM coefficient × calibration slope`. Its signed values describe learned associations, not evidence. Short excerpts are marked uncertain. Model input is capped at the first 2,500 words; full submitted text remains available for reading and language analysis.

### Optional transformer

No DistilBERT model has been trained. To enable the local adapter:

1. Install `backend/requirements-transformer.txt` separately.
2. Supply a local fine-tuned binary Hugging Face model/tokenizer directory, including `verifact.json`:

```json
{"version":"your-evaluated-model-v1","label_mapping":{"LABEL_0":"credible","LABEL_1":"misleading"}}
```

3. Set `MODEL_TYPE=transformer` and `MODEL_PATH=/absolute/path/to/model`. Supply the matching evaluation artifact via `METRICS_PATH`.
4. Implement and evaluate domain validation/attribution before relying on its classification. The adapter currently abstains with “Insufficient Evidence” and no attribution; it does not pretend those capabilities exist.

Only trusted local joblib files should be loaded: pickle-derived model formats can execute code.

## Configuration

Backend reads `backend/.env`; frontend reads `frontend/.env.local`. Restart after changes.

| Variable | Default / purpose |
| --- | --- |
| `DATABASE_URL` | Durable SQLite; PostgreSQL via `postgresql+psycopg://...` |
| `MODEL_TYPE` | `baseline`; optional `transformer` |
| `MODEL_PATH` | `backend/artifacts/articles/model.joblib`; relative paths resolve from backend working directory |
| `METRICS_PATH` | `backend/artifacts/articles/metrics.json` |
| `SESSION_SECRET` | Strong HMAC secret; persistent local file generated if omitted |
| `FRONTEND_ORIGIN` | `http://127.0.0.1:3000`; CORS/Origin allowlist |
| `COOKIE_SECURE` | `false` for local HTTP; use `true` behind HTTPS |
| `UNCERTAINTY_THRESHOLD` | `.65`, maximum class estimate below which assessment is uncertain |
| `EVIDENCE_ENABLED` | `false`; explicitly enable optional Google fact-check search |
| `FACT_CHECK_API_KEY` | Optional server-side Google Fact Check Tools API key |
| `API_BASE_URL` | Frontend server proxy target, `http://127.0.0.1:8000` |
| `POSTGRES_PASSWORD` | Only used for optional Docker PostgreSQL |

No database, evidence, or session secrets belong in `NEXT_PUBLIC_` variables. The optional evidence checkbox explains that the headline/first candidate claim is sent to Google; absent per-request consent, no lookup occurs.

## PostgreSQL / Supabase

SQLite is the zero-service local option. To use local PostgreSQL:

```bash
export POSTGRES_PASSWORD='choose-a-strong-password'
docker compose up -d postgres
```

Set the backend environment (URL-encode special characters in the password):

```dotenv
DATABASE_URL=postgresql+psycopg://verifact:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/verifact
```

Then run `alembic upgrade head` from `backend/` and restart FastAPI. Changing databases does not copy prior history; the SQLite file remains on disk.

For Supabase, copy the direct or **session-pooler** connection string from your project's Connect panel, use the `postgresql+psycopg` SQLAlchemy scheme, and require TLS (`?sslmode=require`; prefer certificate verification for production). Direct connections may require IPv6; the session pooler supports IPv4. Keep credentials exclusively on the backend. This persistent backend does not use the transaction pooler.

Migrations enable PostgreSQL RLS and revoke Data API roles; access is exclusively through the server role and FastAPI's ownership filtering. Use an owner/migration role for migrations, and review the intended server-role permissions. This app does not configure or consume Supabase Auth. No Supabase project or remote data was changed during development. Live PostgreSQL/Supabase connectivity requires your configuration and was not verified without credentials.

## Testing and verification

```bash
cd backend
../.venv/bin/python -m pytest -q
```

Backend integration tests use an isolated temporary SQLite database and require the local article and preserved legacy model artifacts. They need no live external services. Coverage includes preprocessing, schema validation, real inference, exact attributions, domain abstention, file handling, URL/redirect SSRF protection, isolated retrieval/deletion, aggregates, and unavailable evidence behavior.

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

E2E tests start separate servers on **3001/8001** and a separate temporary SQLite database. They use an installed Google Chrome (`channel: 'chrome'`). If Chrome is unavailable, install Playwright Chromium and remove the channel setting:

```bash
npx playwright install chromium
```

The smoke test submits content through the UI, checks the actual FastAPI response, opens/reloads the persisted result, visits dashboard/history, then deletes the result. The mobile test covers navigation, overflow, and persisted light theme. Browser tests never seed a user's real database.

`requirements.lock.txt` records the exact Python packages installed on this development machine; use `requirements.txt` to resolve compatible wheels on another Python/platform. The npm lockfile is used by `npm ci`.

## Production deployment guidance

Build/start the Next.js application with `npm run build` and `npm run start`. Deploy FastAPI as a separate persistent Python service and PostgreSQL as the database. Run migrations as a controlled release step; generate trusted model/evaluation artifacts in the training environment and ship them together to the backend. Configure absolute artifact paths when changing working directories.

Use HTTPS, a stable strong session secret, `COOKIE_SECURE=true`, and an exact `FRONTEND_ORIGIN`. Keep FastAPI private behind the Next.js proxy or a controlled gateway. Set an ingress body limit of 5 MB plus multipart overhead, an upstream timeout, request/concurrency limits, and appropriate connection pooling. The included process-local limiter is for development; use a shared limiter for multiple workers. Apply a retention/deletion policy and protect database backups. No public deployment has been performed.

Do not use this research baseline for consequential automated decisions. There are no accounts, cross-device recovery, audit administration, enterprise security controls, or independently verified claim verdicts.

## Viva walkthrough

1. Open **How it works** and describe the actual preprocessing/vectorization/classification flow.
2. Open **Model performance** and explain the dataset subset, split, confusion matrix, metrics, and limitations.
3. Analyze the clearly labeled example or enter a short political claim.
4. Explain benchmark calibration, domain shift, and signed feature contributions.
5. Point out that language highlights and candidate claims use separate, explicit heuristics.
6. Show unavailable external evidence honestly; it is not a fact-check verdict.
7. Reload the report, open history/dashboard, export the data, and delete the analysis.

## Current limits and future work

- Historical US political claims do not represent all languages, cultures, topics, or full news articles.
- Dataset-specific high scores, inherited labels, source overlap and domain shift limit real-world reliability.
- Sentiment uses a small documented lexicon; subjectivity, OCR, semantic claim extraction, and automated evidence entailment are not implemented.
- Optional external evidence requires credentials, server enablement, and user consent; returned items remain related/inconclusive.
- The transformer adapter is an extension point, not a trained advanced detector.
- Anonymous history is cookie-scoped; no account sync or recovery exists.
- Future improvements: properly licensed article datasets, source/temporal holdouts, calibration studies, multilingual models, rigorous OOD evaluation, trained claim extraction, and evidence-grounded human review.

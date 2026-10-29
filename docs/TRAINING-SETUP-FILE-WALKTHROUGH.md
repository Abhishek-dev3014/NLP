# VeriFact AI: training, setup, and source-code walkthrough

This guide describes the current article model in this working directory. It is based on the source files and inspected local artifacts. Use the quoted statements as presentation material; examples labeled hypothetical illustrate concepts rather than actual model weights.

## 1. Start with the two workflows

There are two separate workflows:

1. **Offline training:** labeled dataset → preprocessing → grouped splits → TF-IDF fitting → SVM fitting/selection → calibration → test evaluation → saved artifacts.
2. **Application inference:** submitted article → validation → loaded model and separate NLP observations → stored report → browser display.

“Sir, training creates the model from labeled examples. Running the website loads that model and applies it to a new article. The article submitted during the demo is not automatically added to the training data.”

Classroom analogy: training is learning from solved examples, validation is choosing a study strategy using a different practice set, calibration checks how confidence relates to outcomes using another set, and testing is the final unseen exam.

## 2. How the active model was trained

### A. Download and verify the dataset

**Open:** `backend/training/download_articles.py`.

**Dataset:** `data/raw/articles/WELFake_Dataset.csv`.

The downloader retrieves the author-published WELFake CSV, verifies the expected MD5 checksum, and records its source in a download manifest. A checksum confirms that the bytes match the expected download; it does not establish the truth of the dataset's labels.

“I used a labeled English-news dataset rather than inventing training examples. Each training article is paired with a class label. My project explicitly interprets the distributed CSV as 0=real and 1=fake. The model card documents a discrepancy with the source webpage description and the count/source audit used for this mapping.”

The original corpus contains 72,134 rows. Inherited dataset labels are training targets, not a guarantee that every sentence received an individual fact check.

### B. Normalize and prepare the text

**Open:** `backend/app/ml/preprocessing.py` and `backend/app/ml/article_features.py`.

`clean_text()` removes markup, decodes HTML entities, normalizes Unicode, and standardizes whitespace. `article_text()` additionally lowercases classification text, removes selected URLs/publisher markers/reporting credits, and retains up to 2,500 whitespace-separated words.

Hypothetical example:

```text
Input:      <p>LONDON (Reuters) - The court issued an order.</p>
Model text: the court issued an order.
```

“I apply the same article preprocessing during training and prediction. Removing selected publisher markers reduces obvious shortcuts, although writing style and topic shortcuts can remain.”

The displayed spaCy entity/grammar pipeline uses the normalized article with its capitalization retained. Do not describe lowercasing or stop-word removal as applying identically to every analysis branch. The classifier does not apply a blanket English stop-word list; the summary vectorizer does.

### C. Filter and handle duplicate articles

**Open:** `backend/training/articles.py`, function `prepare()`, beginning around line 26.

The pipeline filters unsuitable/short cleaned bodies, removes exact text fingerprints and conflicting exact duplicates, and groups approximate duplicates. It uses matching normalized titles, matching 80-word leads, and 64-permutation MinHash/LSH candidates at a 0.80 threshold. Near duplicates are grouped rather than all deleted.

“If almost the same news article appears in both training and testing, the evaluation can reward memorization. I remove exact duplicates and keep approximate-duplicate groups within one partition.”

Analogy: a rewritten version of the same exam question should not be treated as a completely independent unseen question. Approximate grouping can still miss paraphrases.

After preparation, the retained dataset contains 60,544 articles in 59,424 groups.

### D. Create separate partitions

**Open:** `backend/training/articles.py` around line 107.

| Partition | Articles | Purpose |
|---|---:|---|
| Training | 36,325 | Learn vocabulary, IDF values, and SVM weights |
| Validation | 6,054 | Select the SVM regularization setting |
| Calibration | 6,055 | Fit the score-to-probability mapping |
| Test | 12,110 | Evaluate the selected calibrated model |

The code creates ten stratified group folds with seed 42, then assigns six to training, one to validation, one to calibration, and two to testing. Group-disjoint assertions check that no group spans partitions. These are not ten separately reported cross-validation evaluations.

**Artifact:** `backend/artifacts/articles/split-manifest.json` records article IDs, group IDs, and partition assignments.

“The groups are separated across all four partitions. However, this is not a publisher-held-out or time-held-out experiment.”

### E. Fit TF-IDF

**Open:** `backend/training/articles.py` around line 149.

```python
vectorizer = TfidfVectorizer(
    preprocessor=article_text,
    ngram_range=(1, 2),
    min_df=3,
    max_df=0.98,
    max_features=140000,
    sublinear_tf=True,
    dtype=np.float32,
)
x = vectorizer.fit_transform(train.text)
v = vectorizer.transform(valid.text)
```

“TF-IDF converts article words and phrases into numerical features. Unigrams are single words; bigrams are consecutive two-word phrases. The vectorizer learns its vocabulary and document-frequency statistics from training articles only.”

The inspected artifact contains **140,000 features**. An article becomes a sparse vector: most positions are zero because it uses only a fraction of the complete vocabulary. A vector position is a learned word/phrase feature, not a neuron or a training article.

| Setting | Meaning |
|---|---|
| `ngram_range=(1, 2)` | Use single words and two-word phrases |
| `min_df=3` | Keep features occurring in at least three training documents |
| `max_df=0.98` | Exclude features occurring in more than 98% of training documents |
| `max_features=140000` | Limit vocabulary size |
| `sublinear_tf=True` | Reduce the effect of repeated occurrences using logarithmic frequency |

`fit_transform()` learns a representation and applies it. `transform()` reuses an already fitted representation. Fitting a new vocabulary separately for every submitted article would destroy the correspondence with the trained SVM weights.

### F. Fit and select the SVM

**Open:** `backend/training/articles.py` around line 164.

```python
model = LinearSVC(
    C=c,
    class_weight="balanced",
    random_state=42,
    max_iter=5000,
    dual="auto",
).fit(x, train.label)
```

“During fitting, the SVM learns a separating boundary in the numerical feature space. It learns feature weights by optimizing its classification objective; I do not manually declare that particular words are true or false.”

The code tries C=0.5, 1, and 2. C controls the tradeoff between regularization and penalties for training errors. Validation macro-F1 selects the candidate, with ROC-AUC as a tie breaker. **C=2 was selected.** The inspected model has a coefficient array of shape **1 × 140,000**.

Hypothetical arithmetic: if a feature value is 0.2 and its coefficient is -0.8, its contribution to the uncalibrated decision score is -0.16. These illustrative numbers are not the stored values for any particular word.

### G. Fit the calibrator

**Open:** `backend/training/articles.py` around line 182.

```python
calibration_x = vectorizer.transform(cal.text)
calibrator = LogisticRegression(
    C=1e6, solver="lbfgs", random_state=42
).fit(
    model.decision_function(calibration_x).reshape(-1, 1),
    cal.label,
)
```

“The main classifier is an SVM. Here logistic regression acts as a one-dimensional sigmoid calibrator: it receives the SVM decision score and maps it to class estimates. It is fitted using the separate calibration partition.”

This distinction matters because the repository also contains an older logistic-regression classifier. Do not confuse that older model with the calibrator used by the current SVM.

Calibration analogy: someone can correctly choose many answers but still be too confident. Calibration learns a mapping between raw scores and observed labels on comparable examples. It does not guarantee reliability in a new domain.

### H. Evaluate and save

**Open:** `backend/training/articles.py` around line 188, then line 288.

The selected model and calibrator are evaluated on the separate test partition. The saved full-test metrics include all articles before the optional confidence-only filtering.

| Metric | Result |
|---|---:|
| Accuracy | 96.31% |
| Misleading-class precision | 96.51% |
| Misleading-class recall | 94.99% |
| Misleading-class F1 | 95.74% |

“These are results against this benchmark's labels. They do not measure current Indian-news accuracy. A separate diagnostic on 798 short LIAR political claims achieved 47.24% accuracy, illustrating domain and task differences.”

The training script uses LIAR only for its separate cross-domain diagnostic, not to fit this article model. The current script expects that LIAR data to be available when completing the run.

| Generated file | What it contains |
|---|---|
| `backend/artifacts/articles/model.joblib` | Fitted vectorizer, SVM, calibrator, metadata, and metrics |
| `backend/artifacts/articles/metrics.json` | Evaluation scores, settings, audit information, and limitations |
| `backend/artifacts/articles/split-manifest.json` | Article/group IDs and split assignments |
| `backend/artifacts/articles/test-predictions.json` | Test IDs, labels, and misleading-class estimates |
| `backend/artifacts/articles/prepared.joblib` | Cached prepared dataset and audit, not the inference model |

The current inspected model version is `welfake-article-11bbf1821c`. `model.joblib` is a binary artifact: show the serialization code and metadata rather than trying to read it as ordinary text. The application's history database is a different file and does not contain the trained SVM in place of the model artifact.

## 3. How the project is set up

### Existing prepared workspace

The CSV, fitted model, evaluation artifacts, and database are already present in this working directory. Start the application without retraining:

```bash
cd /Users/admin36/Desktop/NLP
./scripts/dev.sh
```

Open `http://127.0.0.1:3000`. The API runs at `http://127.0.0.1:8000`; its interactive API documentation is `/docs` and the health endpoint is `/api/health`.

`scripts/dev.sh` checks basic dependencies, runs Alembic migrations, starts FastAPI through Uvicorn, and starts the Next.js development server. It does not train the classifier.

### Fresh setup explanation

These commands explain reproduction on a fresh checkout. Do not recreate the current environment or overwrite its configuration merely for a demo.

```bash
cd /Users/admin36/Desktop/NLP
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-articles.txt
./scripts/setup-nlp.sh
npm --prefix frontend ci
```

1. `.venv` isolates Python dependencies from other projects.
2. `requirements-articles.txt` includes backend dependencies plus `datasketch`, used for near-duplicate grouping.
3. `scripts/setup-nlp.sh` installs the pretrained `en_core_web_sm` spaCy model. The inspected installed model is version 3.8.0. This downloads a pretrained model; it does not train spaCy on WELFake.
4. `npm ci` installs frontend dependencies using `package-lock.json`.
5. On a fresh checkout, create local environment files from `backend/.env.example` and `frontend/.env.example`. Retain the model/metrics paths and configure a proper session secret, or omit that setting to use the application's generated persistent local secret.
6. `backend/app/core/config.py` reads backend settings. The frontend's `API_BASE_URL` identifies the Python API target.

Use `.env.example` to explain configuration on screen rather than displaying actual credential values.

### Explicit article-model reproduction

After dependencies are installed, from a fresh checkout with the required configuration:

```bash
cd /Users/admin36/Desktop/NLP/backend
../.venv/bin/python -m training.download_articles
../.venv/bin/python -m training.download_data
../.venv/bin/python -m training.articles
```

The second command obtains LIAR for the separate domain diagnostic. Model fitting and artifact creation occur in the third command. Restart the backend to load newly produced weights.

**Important repository distinction:** `scripts/train.sh` currently invokes `training.train`, the older LIAR experiment. It is not the training entry point for the active article SVM. The active pipeline is `training.articles`.

## 4. Architecture through one article's journey

Imagine submitting the same 1,049-word article shown in the screenshots.

| Stage | File to show | What happens in this scenario |
|---|---|---|
| Input screen | `frontend/src/components/analyzer.tsx` | Collects the article and submits it; URL/file extraction can be reviewed first |
| Browser API client | `frontend/src/lib/api.ts` | Sends the analysis request and handles response/errors |
| Frontend proxy | `frontend/src/app/api/[...path]/route.ts` | Forwards the request to FastAPI |
| API route | `backend/app/api/routes.py` | Receives `POST /api/analyze/text` and calls the analysis service |
| Input contract | `backend/app/schemas/analysis.py` | Validates and normalizes fields using Pydantic |
| Coordinator | `backend/app/services/analysis.py` | Checks language and combines classifier, spaCy, rules, evidence, and persistence |
| Classifier preprocessing | `backend/app/ml/article_features.py` | Produces consistent cleaned classifier input |
| Saved model inference | `backend/app/ml/article_classifier.py` | Transforms text, computes score, calibrates, applies uncertainty checks, and computes contributions |
| Linguistic annotations | `backend/app/services/nlp.py` | Produces entities, grammar, summary, and recurring topics |
| Rules and counts | `backend/app/services/linguistics.py` | Produces wording cues, lexical sentiment, statistics, and claim candidates |
| Optional evidence | `backend/app/services/evidence.py` | Returns unconfigured/disabled status or consented related fact-check search results |
| Database schema | `backend/app/models/analysis.py` | Defines analysis, insight, claim, and evidence records |
| Database access | `backend/app/db/session.py` | Opens SQLAlchemy sessions and database connections |
| Saved data | `backend/verifact.db` | Stores session-owned reports locally |
| Results screen | `frontend/src/components/results.tsx` | Displays the returned/saved report |
| Explanation interaction | `frontend/src/components/prediction-explainer.tsx` | Displays signed bars and original text context when a feature is selected |
| Content inspection | `frontend/src/components/nlp-inspector.tsx` | Displays the summary, entities, topics, tokens, and grammar |

Startup is separate: `backend/app/main.py` initializes FastAPI and loads the model. `backend/app/ml/classifier.py`, function `load_classifier()`, recognizes the saved bundle's `article-svm-v1` kind and chooses `ArticleClassifier`. A `MODEL_TYPE=baseline` configuration name does not mean the legacy logistic-regression classifier is used for an article bundle.

For the matching saved report, the credible-class estimate is 95.61%. The 59 sentences and recurring topics are produced by separate linguistic processing. The sentiment score of 1.00 results from two positive-list matches, “good” and “gain,” and no negative-list matches. Those counts do not cause the SVM's prediction.

Selecting “October” shows a +0.647 contribution toward misleading, whereas “said” has about -0.603 toward credible. The complete sum of all feature contributions and the intercept determines the final prediction. A displayed feature is not a factual error, and an excerpt occurrence is not an independently scored claim.

## 5. Technologies: purpose and concrete scenario

| Technology | Meaning and role | Example in this project |
|---|---|---|
| React | Library for interface components | Updates the explanation panel when a word is selected |
| Next.js | Framework organizing the React application and server routes | Serves analyzer/results pages and the API proxy |
| TypeScript | Adds static type checking to JavaScript | Checks the expected report fields while developing |
| Tailwind CSS | Utility classes for visual styling | Controls report layout, spacing, and responsive design |
| TanStack Query | Manages remote data requests and cached query state | Fetches saved reports, metrics, history, and dashboard data |
| React Hook Form + Zod | Browser-side form handling and validation | Checks input before submitting a request |
| FastAPI | Python API framework | Exposes analysis, extraction, history, and metric endpoints |
| Uvicorn | Server that runs the FastAPI application | Listens for API requests on port 8000 locally |
| Pydantic | Runtime data validation and structured schemas | Rejects an invalid analysis payload |
| scikit-learn | Machine-learning implementations | Fits TF-IDF, LinearSVC, calibrator, and evaluation metrics |
| pandas | Table-shaped data processing | Loads/filter/splits the dataset CSV |
| NumPy | Numerical arrays and calculations | Handles scores and contribution computations |
| datasketch | Approximate similarity tools | MinHash/LSH grouping for near-duplicate articles |
| joblib | Serialization of Python data/model objects | Saves and loads the fitted model bundle |
| spaCy + en_core_web_sm | NLP library plus a pretrained English pipeline | Identifies entities, lemmas, POS, and dependencies |
| Regular expressions | Explicit character/word pattern rules | Matches selected clickbait or emotional wording |
| langdetect | Language identification | Helps reject longer non-English input |
| trafilatura | Article-content extraction | Extracts readable text from supported public webpages |
| pypdf | PDF reading and text extraction | Reads a text-based PDF uploaded by a user |
| HTTPX | HTTP client | Fetches article pages and optional evidence results |
| SQLAlchemy | Database access and object-relational mapping | Saves a Python analysis object as database records |
| SQLite | Local database stored in a file | Keeps report history in `backend/verifact.db` |
| Alembic | Versioned database migrations | Creates/updates database tables before startup |
| Recharts | Frontend chart components | Renders report/dashboard/evaluation charts |
| pytest / Vitest / Playwright | Backend, component, and browser test tools | Verify API behavior, report rendering, and full workflows |

## 6. Eight files to open if time is limited

1. `backend/training/articles.py` — “Here is the actual training pipeline.” Start at lines 149, 166, 183, and 296.
2. `backend/app/ml/article_features.py` — “Here is the shared article preprocessing.”
3. `backend/artifacts/articles/metrics.json` — “Here are the saved settings, splits, and measured results.”
4. `backend/app/ml/article_classifier.py` — “Here is how a new article is predicted and explained.”
5. `backend/app/services/nlp.py` — “Here are entities, summary, topics, and grammar.”
6. `backend/app/services/linguistics.py` — “Here are the separate wording rules and lexical calculations.”
7. `backend/app/services/analysis.py` — “Here is how outputs are combined and saved.”
8. `scripts/dev.sh` — “Here is how I start the prepared application.”

For a frontend question, show `analyzer.tsx`, `results.tsx`, and `prediction-explainer.tsx`. For a setup question, show the requirements files, `frontend/package.json`, `.env.example`, and `scripts/setup-nlp.sh`. For database creation, show `backend/alembic/versions/0001_initial.py`.

## 7. Read-only inspection of the binary model

Run from `backend/` using the project's Python environment:

```bash
../.venv/bin/python - <<'PY'
import joblib

bundle = joblib.load('artifacts/articles/model.joblib')
print('Bundle kind:', bundle['kind'])
print('Objects:', list(bundle))
print('Classifier:', type(bundle['classifier']).__name__)
print('Calibrator:', type(bundle['calibrator']).__name__)
print('Vocabulary size:', len(bundle['vectorizer'].vocabulary_))
print('Coefficient shape:', bundle['classifier'].coef_.shape)
print('Model version:', bundle['metadata']['version'])
PY
```

For this inspected artifact, the class names are `LinearSVC` and `LogisticRegression`, the vocabulary size is 140,000, and the coefficient shape is `(1, 140000)`. Load the project's trusted local artifact for this demonstration.

## 8. Strong answers to likely questions

**“Where did training actually happen?”**

“In `training/articles.py`: `fit_transform(train.text)` fits the representation, `LinearSVC(...).fit(x, train.label)` fits the classifier, and the calibrator's `.fit()` fits its separate score mapping.”

**“Did you train the named-entity model?”**

“No. I integrated the pretrained spaCy English pipeline. The article classifier and calibrator were fitted on the project dataset partitions.”

**“Where are your manually written fake-word rules?”**

“The classifier's weights are learned rather than a manually written fake-word list. Separate explicit language rules are in `services/linguistics.py`, and they do not calculate the SVM prediction.”

**“Why are some common words in the explanations?”**

“The classifier keeps eligible common-word features and can learn writing-style associations. That makes its operation inspectable, but also exposes possible dataset shortcuts.”

**“Why not train again during the demo?”**

“Normal application use loads the saved fitted artifact. I can show the reproduction command and training implementation; inference does not require retraining.”

**“How did you test the application?”**

“Backend tests cover inference, attribution consistency, split-group separation, API/session handling, and extraction. Frontend component tests check report interactions, and Playwright tests exercise browser workflows. Software tests and held-out model evaluation answer different questions.”

Useful test files: `backend/tests/test_nlp.py`, `backend/tests/test_api.py`, `backend/tests/test_extraction.py`, `frontend/tests/results.test.tsx`, and `frontend/tests/e2e/analysis.spec.ts`. This guide does not claim these checks were rerun when preparing the explanation.

**One-minute training answer:**

“Sir, I trained a supervised article classifier on WELFake. I cleaned the article bodies, removed exact duplicates, and grouped near duplicates to reduce leakage. I separated training, validation, calibration, and test data. TF-IDF learned unigram and bigram features from training articles, and a linear SVM learned the classification weights. I compared three C settings on validation data, selected C=2, fitted sigmoid calibration on a separate partition, and evaluated on 12,110 held-out articles. The resulting model bundle is saved under `backend/artifacts/articles/`. The website loads that bundle to analyze new articles, while a separate pretrained spaCy pipeline produces the linguistic annotations.”

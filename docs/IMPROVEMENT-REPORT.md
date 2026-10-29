# Archived LIAR training and product review

This describes the previous short-claim release. The default is now the separately trained article model; see [ARTICLE-MODEL.md](ARTICLE-MODEL.md). Historical figures and decisions below are preserved.

The active classifier retains its original weights. A newly trained, validation-selected challenger failed to improve overall test performance and was not promoted. No claim of a perfect or general-purpose fact-checking model is justified by these results.

## Actual comparison

The original official LIAR partitions retain 6,472 training, 791 validation and 798 test statements after binary label filtering and duplicate removal. The test set was already reported in the first version: these results are a retrospective comparison, not a new unseen benchmark.

| Metric | Active baseline | Calibrated challenger |
|---|---:|---:|
| Accuracy across all 798 test statements | 66.29% | 63.66% |
| Misleading-class precision | 0.6000 | 0.5860 |
| Misleading-class recall | 0.6195 | 0.4926 |
| Misleading-class F1 | 0.6096 | 0.5353 |
| ROC-AUC | 0.7187 | 0.7069 |
| Brier score (lower is better) | 0.2130 | 0.2128 |

Six candidates were predeclared: word TF-IDF; word plus character TF-IDF at two regularization levels; and three word/character/frozen-MiniLM combinations. Candidate selection used validation macro-F1, with ROC-AUC as a tie breaker. The winner was word/character TF-IDF with C=0.5. Its sigmoid calibration was fitted on five-fold out-of-fold training logits, with the entire feature vectorizer refitted inside each fold. Test labels did not choose candidates, calibration parameters, or confidence thresholds. The comparison informed the conservative deployment decision to retain the existing model.

MiniLM generated real 384-dimensional semantic embeddings. Its pretrained encoder was **not fine-tuned**. Logistic-regression heads were trained on the supervised task. Adding transformer embeddings did not win validation selection. Character features, explicit lowercase normalization, and calibration remain available in the experimental artifact, rather than being silently swapped into the existing fitted vocabulary.

## Confidence is not accuracy

The active model now uses a threshold chosen on validation: maximum class estimate >= 0.70, plus a heuristic screen requiring short text, political terms, and sufficient unigram vocabulary coverage. The screen is not a validated domain detector.

- Validation: 51/63 accepted predictions correct (80.95%).
- Test: 47/54 accepted predictions correct (**87.04%**).
- Test coverage: **54/798 = 6.77%**; most examples receive uncertainty or scope abstention.
- Wilson 95% interval for accepted-test accuracy: **75.58–93.58%**.
- Baseline probabilities remain **uncalibrated**. Changing an abstention policy does not improve the classifier's overall 66.29% accuracy.

The challenger confidence-only policy achieved 81.25% on 272/798 claims (34.09% coverage). That figure excludes its separate scope screen and must not be described as deployed performance. Its full-test accuracy was lower. The UI clearly labels the challenger as not deployed.

Out-of-scope new reports now withhold confidence, probabilities, and model features; they still provide a useful language review. Existing saved reports are preserved with their original model versions.

## Implemented product and NLP improvements

- A three-step guide: add content, understand the story, verify the claims.
- An input scope explanation that changes for long articles.
- Extractive summaries using sentence TF-IDF and centroid similarity, with exact original offsets and explicit 200-sentence scope.
- Trained spaCy tokenization, lemmatization, POS, morphology, named entities and dependency parsing; bounded detail tables prevent oversized reports.
- Recurring topics from noun lemmas; grammatical annotations are inspectable, not treated as evidence of truth.
- An interactive `/nlp-lab` that processes locally without saving lab content to history.
- Candidate claims can be sent back to the analyzer via sessionStorage; article text is not put in the address bar.
- Comparison metrics, actual acceptance coverage, intervals, validation candidate table, and a challenger reliability chart with accessible numeric data.
- Typed, additive report fields preserve older histories. Loaded model and evaluation versions must match before metrics are served.
- Chunked oversized requests return a clear 413 before the body parser; existing session, extraction and persistence tests remain applicable.

## Reproducing the experiment

From the repository root, install regular dependencies, then:

```bash
./scripts/setup-nlp.sh
.venv/bin/python -m pip install -r backend/requirements-training.txt
cd backend
../.venv/bin/python -m training.download_data
# On a fresh clone, train and preserve the original baseline first.
../.venv/bin/python -m training.train
mkdir -p artifacts/v1
cp -n artifacts/baseline.joblib artifacts/v1/baseline.joblib
cp -n artifacts/metrics.json artifacts/v1/metrics.json
../.venv/bin/python -m training.download_models
../.venv/bin/python -m training.improve
../.venv/bin/python -m training.operating_policy
```

On this prepared workspace the artifacts already exist; do not retrain merely to run the website. `training.operating_policy` changes metadata and evaluation policy, not weights. The model downloader pins MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The English pipeline is en_core_web_sm 3.8.0. The recorded environment is `backend/requirements.lock.txt`; normal serving does not require PyTorch or MiniLM.

Files: `backend/artifacts/metrics.json` (active), `backend/artifacts/v1/metrics.json` (original), `backend/artifacts/v2/metrics.json` (challenger), plus local trusted `.joblib` weights. Raw data/weights stay ignored. No user content is sent to a model API; downloads occur only during explicit setup.

For experimental local inference, point `MODEL_PATH` at the absolute `backend/artifacts/v2/model.joblib` path and `METRICS_PATH` at its metrics, then restart. Leave `MODEL_TYPE=baseline`; the artifact loader identifies its format. Do not present this configuration as the default or as a proven accuracy improvement.

## Next research step

Obtain a suitable licensed, recent dataset with evidence and speaker/source/time-disjoint evaluation; preregister candidate selection and test on genuinely unseen claims. Fine-tuning a larger encoder or claiming 90% from a narrow accepted subset would not solve this evidence gap. The current system is a local NLP research aid, not independent factual verification.

## Verification completed

- Backend: 35 tests passed, including inference/attribution consistency, calibrated score reconstruction, exact NLP spans, abstention, history isolation, extraction, body limits and non-persistent lab exploration.
- Frontend: 7 component tests passed; TypeScript and ESLint passed.
- Browser: 5 workflows passed against real temporary FastAPI/Next.js servers, including mobile navigation, report/history/deletion, the NLP lab, article-to-claim review, and the model comparison page.
- Production: Next.js build passed. A cached sandbox worker-port error was resolved by moving the generated build cache aside and rebuilding with local worker access.
- Visual inspection: desktop lab/report and 390px mobile model page checked; no horizontal overflow after responsive layout settles.

Browser tests used temporary databases. Existing user history was not cleared. Start the prepared application with `./scripts/dev.sh`; restart any older backend process to load the new NLP pipeline and policy metadata.

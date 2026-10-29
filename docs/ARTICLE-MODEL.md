# Full-article model release — 26 October 2026

## What changed

VeriFact now uses a classifier trained on full news articles. It returns a fake/real-pattern assessment, calibrated benchmark confidence, signed feature explanations, and a separate factual-verification status. The old 160-word political-claim screen no longer suppresses full-article results. Inputs below 40 words remain explicitly uncertain; they can still receive a preliminary estimate. Source text is analyzed locally.

The product still does not independently determine truth. In particular, a high score is not proof that an article is fake. The user's contemporary Indian MSN article is flagged by this model, with date-related terms among its strong features. That result demonstrates potential dataset bias. It is **not** a verified false-news finding and was not used to tune the model.

## Data provenance and audit

Source: [WELFake, Verma, Agrawal and Prodan (2021)](https://zenodo.org/records/4561253), author-published version 0.1, CC BY 4.0 in the record metadata. Underlying publishers may retain article copyright; raw text remains local and is not republished. The release merges several historical news corpora and does not provide reliable source/date fields for every article.

- Original CSV: 72,134 rows, 245,086,152 bytes.
- Verified MD5: `73c9675a4b3d09f86a6933d0b8d7d908`.
- **Label discrepancy:** the record description says 0=fake/1=real, but the CSV has 35,028 rows labeled 0 and 37,106 labeled 1, matching the authors' real/fake class totals in the opposite order. Among records containing `(Reuters)`, 21,266 are label 0 and 16 label 1. The loader explicitly uses **0=real, 1=fake**, with count/source assertions. This is a documented interpretation supported by the actual distributed data, not an unreported label swap.
- Missing bodies and articles under 40 words are filtered. Text is capped at 2,500 words consistently in training and inference.
- Obvious Reuters/AP datelines, publisher strings, URLs, reporting/editing credits and bracketed media markers are removed. This does not eliminate source, topic, date or writing-style shortcuts.
- Exact body duplicates and conflicting exact duplicates are removed. Identical titles/80-word leads and MinHash LSH matches share a group. This approximate technique reduces leakage but can miss paraphrases.
- 60,544 retained articles in 59,424 groups. 1,120 rows share an approximate-duplicate group with another retained article.

## Experimental design

Ten stratified group folds are assigned deterministically with seed 42: six train folds, one validation, one calibration, and two test folds. Group identity is never derived from labels. All four partitions are group-disjoint; the saved split manifest is tested for overlap.

| Partition | Articles | Purpose |
|---|---:|---|
| Training | 36,325 | Fit TF-IDF vocabulary and SVM coefficients |
| Validation | 6,054 | Choose regularization among C=0.5, 1, 2 |
| Calibration | 6,055 | Fit sigmoid scaling on separate decision scores |
| Test | 12,110 | Evaluate the selected calibrated model once |

TF-IDF uses word unigrams/bigrams, sublinear term frequency, minimum frequency 3, maximum document frequency .98, and up to 140,000 features. LinearSVC uses balanced class weights. Validation macro-F1 selects C, with ROC-AUC as tie breaker; C=2 won. Test labels did not select C, fit calibration, or adjust the fixed .65 uncertainty threshold. No low-confidence test articles are excluded from the headline metrics.

This release **trains and tunes a supervised SVM**. It does not claim to fine-tune a transformer encoder. Earlier MiniLM experiments used frozen embeddings and remain documented separately. Fine-tuning an encoder is a valid research option, but its value must be established on appropriate held-out data, not assumed from the model name.

## Measured full-test performance

| Metric | Result |
|---|---:|
| Accuracy | 96.31% |
| Misleading-class precision | 96.51% |
| Misleading-class recall | 94.99% |
| Misleading-class F1 | 95.74% |
| Macro-F1 | 96.24% |
| ROC-AUC | 0.9939 |
| Brier score | 0.0278 |

All requested classification metrics exceed 90% **on this benchmark**. These are not measurements of current Indian news, source-disjoint generalization, or universal factual verification. The older LIAR result of 66.3% concerns a different task/dataset and is not a valid before/after accuracy comparison.

The separately reported cross-domain test on 798 short LIAR claims reached **47.24% accuracy**. It is not pooled into the article metric or used for tuning. It exposes how strongly performance depends on the task and dataset. Calibration on historical articles does not fix domain shift.

## User experience

The report leads with a model assessment, confidence and explanation, followed by separate prediction/factual-verification/next-step cards. A prominent note states that current Indian news has not been independently evaluated. “Not independently verified” remains visible even for very confident predictions. Users can inspect feature contributions and search exact claims themselves; searches occur only when they click the external link.

Summaries, entities, grammar details, report export, session-owned history and the NLP lab remain available. Existing reports retain their original model versions; they are not silently re-scored.

## URL extraction fix

The user's MSN link returned a JavaScript shell. The extractor now reads MSN's public CDN article feed, yielding the correct title and 134 words, while respecting premium/rendering restrictions. Every request and redirect still validates public DNS addresses and pins the actual connection IP. There is no general proxy fallback and no bypass of sign-in or paywalls.

Other improvements: plain-text responses, a public Article/NewsArticle JSON-LD fallback, charset handling, explicit 403/404/429 messages, and a paste-text recovery button. A live browser workflow exercises the exact MSN URL through extraction, review, classification and saved results. Public endpoints can change or remove content; mock-based regression tests cover the extractor independently.

## Reproduction

The current workspace already has the data and trained weights. To reproduce from a fresh checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-articles.txt
./scripts/setup-nlp.sh
cd backend
../.venv/bin/python -m training.download_articles
../.venv/bin/python -m training.download_data  # LIAR data for the cross-domain stress test
../.venv/bin/python -m training.articles
```

Weights and active metrics are in `backend/artifacts/articles/model.joblib` and `metrics.json`. The split manifest and test predictions contain IDs, split/group identifiers and numbers rather than raw article text. Raw corpus, encoder caches and serialized weights remain ignored. If preprocessing or split rules change, remove the generated `prepared.joblib` cache and retrain all four partitions; do not evaluate modified preprocessing against old weights.

`MODEL_PATH` and `METRICS_PATH` now default to these article artifacts. Existing explicit environment overrides take precedence. Legacy LIAR model artifacts remain preserved under `backend/artifacts/` and `v1/`; the calibrated LIAR challenger remains under `v2/`.

Restart with:

```bash
cd /Users/admin36/Desktop/NLP
./scripts/dev.sh
```

Run `pytest`, frontend component tests and Playwright against isolated test databases. No existing user history is cleared by the upgrade.

## Verification completed

On October 26, 2026: 41 backend tests, 9 frontend component tests and 6 browser workflows passed. The browser suite includes the supplied live MSN URL, its extracted content, the numerical model result, history, mobile layouts and the benchmark disclosure. TypeScript, ESLint, targeted Python lint and the production Next.js build passed. Desktop and mobile report screenshots were visually reviewed. These software checks verify behavior; model accuracy is measured separately by the held-out evaluation above.


## Interactive explanation interface

The report includes a three-view explanation panel: actual model feature contributions, separate rule-based language cues, and a plain-language NLP walkthrough. Selecting a word or bigram shows its original context when an exact match exists, its signed class direction, and an expandable technical contribution. Bars are relative to the largest displayed absolute contribution, not probabilities. The panel does not infer factual reasons from model weights or add linguistic heuristics to the classifier.

The report uses glass-style surfaces with opaque fallbacks, subtle inset/raised controls, light/dark themes, visible keyboard focus and responsive layouts. Ten component tests and three targeted browser workflows passed for this redesign, together with TypeScript, ESLint and a production build. Desktop and mobile screenshots were reviewed.

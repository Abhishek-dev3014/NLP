> Legacy LIAR model card. The current default uses a separately documented [full-article model](ARTICLE-MODEL.md).

# Dataset and model card

## Source and rights

William Yang Wang (2017), “Liar, Liar Pants on Fire”: A New Benchmark Dataset for Fake News Detection, ACL short papers, pp. 422–426.

- Author's release: https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip
- Paper: https://aclanthology.org/P17-2067/
- Archive downloaded directly; its SHA-256 is written to `data/raw/archive.sha256`.
- The original distribution does not include an explicit blanket license grant. Underlying PolitiFact material may have separate terms. Public availability is not permission for unrestricted commercial redistribution. Review source rights before distributing data or derived artifacts. Raw data and model weights are ignored by Git.

## Task

LIAR consists of short human-labeled political statements from PolitiFact, predominantly US politics, 2007–2016. It is **not a corpus of full news articles**. We use only statement text, not speaker credit histories, party, identity, or metadata. The original distribution warns that credit histories include the current statement; those fields are intentionally excluded.

For the first classifier:

| Target | Source labels |
| --- | --- |
| 0, credible class | true, mostly-true |
| 1, misleading class | false, pants-fire |
| excluded | half-true, barely-true |

This is a custom binary subset, not the original six-way benchmark. Results are not comparable with six-way LIAR results. These targets reflect dataset annotations, not independent verification of submitted content.

## Leakage controls and evaluation

Original train/valid/test partition membership is preserved. Unicode/HTML cleanup is shared with inference. Exact text fingerprints are deduplicated globally; char 3–5-gram cosine similarity ≥ 0.92 removes near duplicates, favoring the earlier split. The unsupervised fingerprint index uses all splits solely to remove overlaps; it never supplies model features or labels. No test labels are used for feature fitting or parameter selection.

The TF-IDF classifier is fitted only on retained training claims. C ∈ {0.5, 1, 2, 4} is selected using validation misleading-class F1. The selected model is then evaluated once on the test set. It is not retrained on validation data. Split speaker/topic overlap still exists; there is no source-held-out or temporal generalization claim. Deduplication is imperfect.

Inspect `backend/artifacts/metrics.json` for the actual split sizes, class counts, selected C, validation scores, confusion matrix, full classification report, and test metrics. Do not hand-edit it. Run training to regenerate it.

## Interpretation and domain

Word/bigram TF-IDF, sublinear TF, minimum document frequency 2, maximum 40,000 features, balanced Logistic Regression, seed 42. Stopwords and negation are retained; no stemming. The logit decomposition is `intercept + sum(tfidf_i * coefficient_i)`. Features shown are the strongest signed active contributions, not causal explanations.

Probabilities are **uncalibrated**. A maximum class estimate below the validation-selected artifact threshold (.70 in the current policy; .65 legacy fallback) produces “Needs Further Verification.” A conservative heuristic abstains for long (>160-word), low-coverage, or non-political inputs. It is not a formally validated OOD detector and can be wrong. Historical topics and class-label simplification limit accuracy. Even in-domain predictions are not truth probabilities.

Language insights use documented small lexicons and phrase patterns. Sentiment is a lexical positive/negative balance; subjectivity is unavailable. Claim extraction selects sentences with numbers or factual-style predicates. It is incomplete and never marks claims verified.

## Reproduction

```bash
cd backend
../.venv/bin/python -m training.download_data
../.venv/bin/python -m training.train
```

For manual ingestion, place the original `train.tsv`, `valid.tsv`, and `test.tsv` in `data/raw/` without changing columns. Do not silently substitute WELFake, FakeNewsNet, or a different LIAR variant. Add a separately documented loader and task mapping for any future dataset.

The active weights remain the original baseline. For the six-candidate comparison, sigmoid calibration experiment, rejection decision, and actual 6.8% acceptance coverage, see [the improvement report](IMPROVEMENT-REPORT.md). New out-of-scope reports withhold probabilities and confidence.

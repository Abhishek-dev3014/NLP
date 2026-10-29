# Syllabus mapping

| Unit | Implemented and inspectable | Where |
|---|---|---|
| 1: word-level analysis | Unicode/HTML normalization, regex cues, tokenization, trained lemmatization, morphology, POS, NER; TF-IDF word/bigram classification; character n-grams in training experiments | NLP lab and report grammar/annotation panels; `app/services/nlp.py`, `app/services/linguistics.py`, `app/ml/features.py` |
| 2: syntax | Trained dependency parsing, grammatical head and relation inspection | Expand grammar details in the NLP lab or any new report |
| 3: semantics/discourse | Frozen MiniLM sentence embeddings evaluated as semantic features; extractive sentence selection and noun-lemma topics | Six-candidate experiment and training report |
| 4: language models | Real transformer encoder used in training experiments; supervised linear heads; regularization, validation selection, out-of-fold sigmoid calibration, held-out evaluation | Model information page; `training/improve.py` |
| 5: applications | Information extraction, safe article/document extraction, extractive summarization; optional evidence retrieval with consent | Analyzer, results, NLP lab, evidence panel |

## Exact boundaries

Dependency parsing is implemented; CFG/CKY/Earley/PCFG parsers are not. Lemmatization is implemented; stemming is not applied to the classifier. We preserve negation and function words for classification. Summary TF-IDF drops English stopwords; its purpose differs from classification.

The semantic experiment uses pretrained transformer embeddings; it does not train Word2Vec, GloVe, RNNs or LSTMs, and does not fine-tune MiniLM encoder weights. Coreference, word-sense disambiguation, machine translation, generative QA and abstractive summarization are not implemented. Adding unrelated algorithms solely to list syllabus terms would make the system harder to explain and would not establish better accuracy.

Sentiment and emotional/clickbait cues are transparent lexical heuristics, not a trained contextual sentiment classifier. Summary sentences are exact excerpts ranked by TF-IDF centroid similarity, not generated or fact-checked. Named entities and parse annotations can be wrong. Candidate claims are selected by sentence rules and are not verified.

## Suggested demonstration

1. Open NLP lab and run its fictional example.
2. Inspect London as a place, borrowed → borrow as a lemma, VERB as a POS tag, and the dependency head relationships.
3. Paste a longer article in New analysis; explain its extractive summary and the trained article assessment, separate from factual verification.
4. Select a candidate claim and inspect the classifier's actual word contributions.
5. Open Model information: explain precision/recall, the confusion matrix, and why 96.3% article-benchmark accuracy does not imply the same accuracy on current Indian news.
6. Inspect SVM validation selection, the disjoint calibration set, and cross-domain stress results. Explain why a calibrated classifier is not an evidence-based fact checker.

The current release adds linear Support Vector Machines, group-disjoint data splitting, MinHash near-duplicate grouping and a separate sigmoid calibration partition. These are documented in [ARTICLE-MODEL.md](ARTICLE-MODEL.md).

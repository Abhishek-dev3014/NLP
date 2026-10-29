# VeriFact AI: presentation and working-demo script

Prepared from the three supplied screenshots, the current implementation, the saved report matching the screenshots, and the active model evaluation artifact. The example article is treated as input text; this guide does not verify its allegations or legal reporting.

Use the quoted paragraphs as your spoken script. Directions in brackets tell you what to show. The main walkthrough takes approximately 15–20 minutes, depending on pauses and questions. The technical notes and viva answers are for preparation.

## 1. Introduce the project

[Open the home page or analyzer.]

“Good morning, sir. My project is VeriFact AI, a web application for fake-news screening and misinformation analysis using Natural Language Processing.

“The application accepts an English news article and helps the reader answer three questions: What does the article say? What language patterns influenced the model’s prediction? And which statements should be checked against original evidence?

“It combines a supervised machine-learning classifier, an NLP pipeline for content analysis, and an interactive explanation interface. The current classifier uses TF-IDF and a calibrated linear Support Vector Machine.

“Its output is a credibility-screening estimate based on learned article patterns. Independent factual verification is shown as a separate status, because language patterns alone cannot establish whether a statement is true.”

## 2. Explain the architecture

[Open How it works, or show this flow.]

```text
User: paste text / extract a public URL / upload TXT or text-based PDF
                              |
                              v
                 Next.js + React + TypeScript interface
                              |
                     Same-origin API proxy
                              |
                              v
                   FastAPI validation and orchestration
                              |
             +----------------+------------------+
             |                |                  |
             v                v                  v
      CLASSIFICATION      CONTENT ANALYSIS    LANGUAGE RULES
      Article cleaning    Trained spaCy      Phrase matching
      TF-IDF features     Sentences          Emotion / clickbait /
      Linear SVM          Entities / grammar certainty cues
      Sigmoid calibration Extractive summary Candidate claims
      Signed attribution  Recurring topics  Counts / sentiment
             |                |                  |
             +----------------+------------------+
                              |
                  Compose a structured report
                  Optional evidence search, if
                  configured and consented to
                              |
                  SQLAlchemy database storage
                    SQLite by default locally
                              |
                              v
                  JSON response to the interface
                  Results / history / dashboard
```

“At the presentation layer, I use Next.js with React and TypeScript. This layer handles article input, report display, navigation, and user interaction.

“Requests pass through a same-origin API proxy to a Python FastAPI backend. The backend validates the request and coordinates the analysis.

“There are three logical analysis branches. The classifier estimates the article’s class. The trained spaCy pipeline extracts linguistic information. Separate rules detect selected wording patterns and candidate claims. These branches are combined into one report; this diagram does not imply they execute simultaneously.

“SQLAlchemy stores the analysis. The default local database is SQLite. The backend returns structured JSON, and the frontend displays the report and makes the saved analysis available in history and dashboard views.

“The classifier and calibrator are fitted offline. During a demo, the application loads those saved artifacts and performs inference; it does not retrain on each submitted article.”

## 3. Demonstrate input and preprocessing

[Open Analyze. Paste the same complete article used in the screenshots. If demonstrating URL or file input, first show extraction and editable review.]

“The application supports direct text, public article URLs, and TXT or text-based PDF files. URL and file extraction let the user review the extracted text before analysis. Scanned PDFs require OCR before upload; OCR is not implemented here.

“For this demonstration, I am using the article shown in these screenshots. The article is an input example, and I will explain the system’s behavior without treating its reporting as independently verified.

“The backend normalizes whitespace and Unicode, decodes HTML entities, and removes HTML markup. For classification, it also lowercases the text and removes selected publisher identifiers, URLs, and reporting-credit patterns. These same article-preprocessing rules are used during training and inference.

“The classifier uses the article body. The headline is retained as report metadata, rather than being appended to the classifier input. Classification is capped at the first 2,500 words. The complete accepted text remains available for reading and language analysis.”

[Click Analyze and wait for the saved result.]

Preparation note: input validation requires at least 12 word-pattern tokens. A submitted article under 40 classifier-input words can still receive language analysis and a preliminary estimate, but its classification is marked uncertain. The request text limit is 60,000 characters.

## 4. Explain TF-IDF and the classifier

[Point to the model name or How NLP works tab.]

“Machine-learning models need numerical input. TF-IDF converts the article into a sparse vector of word and phrase features.

“TF means term frequency: how often a feature occurs in this article. IDF means inverse document frequency: how uncommon that feature is across the training documents. The combination gives a numerical feature value. This value represents a text feature, not factual importance.

“My vectorizer uses unigrams and bigrams. A unigram is one word, such as ‘October.’ A bigram is two consecutive words, such as ‘on October’ or ‘on Monday.’ The vectorizer learns its vocabulary from the training partition, and reuses that fixed vocabulary for new articles.

“The linear SVM learns a weight for each feature from labeled examples. For a new article, it multiplies each feature value by its learned weight, adds those contributions, and includes an intercept. This produces a decision score.

“A separate sigmoid calibrator converts the decision score into two class estimates: credible and misleading. Calibration improves how the numerical estimates relate to outcomes on comparable benchmark data. It cannot guarantee that an unfamiliar article is correctly classified.”

Technical note: the active training setup allows up to 140,000 unigram/bigram features, uses sublinear term frequency, minimum document frequency 3, maximum document frequency 0.98, and balanced SVM class weights. Validation selected C=2. The classifier does not consume the displayed sentiment, entity labels, summary, or clickbait counts. It also does not use spaCy lemmas as its classification features. Common words remain eligible, which helps explain features such as “on” and “its.”

## 5. Explain the main prediction

[Show the top of the results report.]

“For the saved report matching these screenshots, the result is ‘Likely Credible.’ Its calibrated class estimates are approximately 95.61 percent credible and 4.39 percent misleading. The displayed model confidence is the larger of these two estimates.

“This means that the article’s features resemble examples assigned the real-news label in the training corpus. The 95.61 percent value describes the model’s classification estimate; it is not a measured probability that every statement in this article is true.

“The application therefore keeps ‘Not independently verified’ as a separate factual status.

“The confidence threshold is 65 percent. Inputs also need sufficient length and vocabulary overlap. If these checks fail, the application reports ‘Needs Further Verification,’ even if it can display a tentative class estimate.”

If you rerun a different or edited article, read the new displayed label and confidence. Do not promise that a selected sample will always receive a particular outcome after its text or model version changes. Length and vocabulary checks are basic adequacy checks, not a validated guarantee that an article belongs to the training domain.

## 6. Explain screenshot 2: Understand the content

[Scroll to Understand the content.]

### At a glance: extractive summary

“The first section helps the user understand the article quickly. This is an extractive summary: the system selects existing sentences from the article instead of generating new statements.

“It segments the article into sentences and considers up to the first 200. It removes duplicate sentence candidates and filters out very short candidates. A separate sentence-level TF-IDF representation helps rank sentences by similarity to the document’s average feature vector. The system selects up to three highly ranked sentences and displays them in their original order.

“Here, the article contains 59 sentences, so the summary considers the first 59 of 59 sentences. Original wording is preserved, but sentence importance is estimated rather than verified. A heading or question can also be selected, as we can see in this example.”

### Names and references: named-entity recognition

[Point to Sabeer Bhatia, Adani Enterprises, dates, and locations.]

“Named-entity recognition identifies text spans that look like people, organizations, places, dates, amounts, and other entity types. This uses the pretrained English spaCy model, en_core_web_sm.

“For example, Sabeer Bhatia is identified as a person and Adani Enterprises as an organization. These labels help the reader identify the participants and references in the article. They do not verify the identities or confirm the article’s claims.

“Entity recognition is imperfect. In this screenshot, ‘Hotmail’ is labeled as a place, and some surname references also receive unsuitable labels. These are observable limitations of the language model. The current system displays its predictions without a domain-specific correction layer.”

### Recurring topics

[Point to adani ×19, court ×15, and documentary ×11.]

“Recurring topics are frequent nouns and proper nouns grouped by their lemma, or base form. For example, ‘allegations’ can contribute to the base-form topic ‘allegation.’

“In this report, ‘adani’ appears 19 times, ‘court’ 15 times, and ‘documentary’ 11 times in these noun-based counts. This provides a quick view of repeated subjects. It is frequency analysis, not proof of importance, truth, or a separately trained topic model.”

## 7. Demonstrate tokens, lemmas, and grammar

[Expand Explore the NLP · tokens, lemmas & grammar.]

“Tokenization divides text into units such as words and punctuation. Lemmatization finds a base form, such as ‘allegations’ becoming ‘allegation.’ Part-of-speech tagging identifies grammatical roles, such as noun, verb, or adjective. Morphology adds grammatical properties, such as number or tense.

“Dependency parsing describes grammatical relationships. It can connect a subject or object to a verb and identify the main predicate, called the root.

“These annotations support the linguistic inspection features and help select candidate claims. They are separate from the fitted TF-IDF and SVM classifier.

“To keep the interface manageable, the token table shows up to 120 tokens. The dependency view shows up to 35 tokens from one representative sentence.”

If asked why token totals differ from the word count: spaCy tokens can include punctuation; the language snapshot’s word count uses a separate regular-expression word pattern.

## 8. Explain screenshot 1: Why did it get this result?

[Open Words that influenced it.]

“This panel explains which active features contributed to the model’s score. The backend returns up to 14 features with the largest absolute contributions.

“A green contribution moves the score toward the credible class. A red contribution moves it toward the misleading class. The bar length is relative to the largest contribution displayed here. It is not a probability, an accuracy percentage, or a measure of factual error.”

[Select October.]

“Here, ‘October’ has a positive contribution of approximately 0.647 calibrated log-odds units, so it pushes toward the misleading class. The interface shows an occurrence in the original article so we can read its context.

“This does not mean October is an incorrect word or that the date is false. It means this feature received a weight from the training data. It may reflect topic, source, time, or writing-style associations in that dataset. The current cue rules detect no specific language problem with this word.

“The excerpt helps inspect the feature, but the contribution comes from the article’s aggregated TF-IDF feature value. It is not a separate factual judgment about the highlighted occurrence.”

[Select said, then on Monday.]

“By comparison, ‘said’ contributes approximately minus 0.603 units and ‘on Monday’ approximately minus 0.402 units, both toward the credible class. The model has learned associations involving reporting language, but it has not established that using these phrases makes a statement true.

“Although ‘October’ has the largest individual displayed contribution and it is red, the final prediction combines every active feature with the intercept. The application does not decide by counting red and green bars or by choosing the strongest individual word.

“For this saved report, all feature contributions sum to about minus 4.645, and the combined intercept is about plus 1.565. The total calibrated log-odds is approximately minus 3.081. After the sigmoid transformation, this corresponds to about 4.39 percent for the misleading class and 95.61 percent for the credible class. The displayed 14 features are only part of that complete sum.”

[Expand See the technical contribution if asked.]

“The contribution formula is the TF-IDF value multiplied by the linear SVM coefficient and the calibration slope. These are direct contributions from the fitted linear model. This implementation does not use SHAP or LIME for the explanation.”

## 9. Explain language cues and screenshot 3

[Open Language cues, then scroll to Read between the lines.]

“The language-cue layer uses explicit word and phrase patterns. For example, ‘shocking’ can match an emotional-word rule, ‘you won’t believe’ can match a clickbait rule, and ‘guaranteed’ can match an absolute-certainty rule.

“These rules are independent of the SVM. They provide readable observations, but they do not calculate the classifier’s feature weights. A highlighted phrase can also occur inside a quotation, criticism, or denial, so matching the wording does not establish the author’s intention.

“In the screenshot example, no phrases matched the implemented emotional, clickbait, or certainty patterns. Therefore, this article has no highlights from those rules. That means no listed rule matched; it does not prove that the article is neutral, complete, or factually correct.”

[Point to A language snapshot.]

“The language snapshot contains 1,049 words and 59 sentences. Average sentence length is the word count divided by the sentence count: 1,049 divided by 59 is approximately 17.8 words per sentence.

“The sentiment balance is 1.00. This uses a small positive-and-negative word list, with the formula positive matches minus negative matches, divided by the larger of one and their sum.

“In this saved report, ‘good’ and ‘gain’ match the positive list once each, and no words match the negative list. Therefore, the score is two minus zero divided by two, which equals one.

“This is a useful example of the limitation: a score of one can result from only two matched words in a long article. It does not mean the article is entirely positive or trustworthy. The method does not interpret negation, sarcasm, quotation, or wider context as a contextual sentiment model would.

“Clickbait and emotional counts are both zero here. Subjectivity is not implemented in the current version.”

## 10. Explain candidate claims and external evidence

[Open Review the claims.]

“Candidate claims are exact sentence excerpts selected for human review. The selection rules look for sufficient length and signals such as numbers, factual-style predicates, or parsed subject–predicate structures. Questions and duplicate sentences are skipped, and the report includes up to six candidates.

“These are sentences worth checking, not automatically verified claims. Their status remains ‘Not verified.’”

[Show External evidence.]

“This report says ‘Evidence integration is not configured.’ The application has an optional Google Fact Check Tools search integration, but it requires backend enablement, credentials, and consent for the request.

“When configured and requested, it searches using the headline or a candidate claim and returns related fact-checks. The current implementation does not automatically establish that a returned source supports or contradicts the exact submitted claim. Related evidence remains inconclusive until reviewed.

“For this demonstration, the results are based on local NLP and model inference. No independent evidence-based verdict has been produced.”

## 11. Explain training and evaluation

[Open Model performance or Explore evaluation metrics.]

“The active classifier was trained on WELFake English news articles. The original corpus contains 72,134 rows. After filtering unsuitable bodies and removing exact or conflicting duplicates, the prepared dataset contains 60,544 articles.

“Similar articles are assigned to duplicate groups, and those groups are kept within a single partition. This reduces the risk of almost the same article appearing in both training and evaluation, although approximate grouping can miss paraphrases.

“The split contains 36,325 training articles, 6,054 validation articles, 6,055 calibration articles, and 12,110 test articles. Training fits the vocabulary and SVM. Validation selects the regularization setting. Calibration fits the score-to-probability mapping. The separate test set evaluates the selected model.”

| Partition | Articles | Purpose |
|---|---:|---|
| Training | 36,325 | Fit TF-IDF and SVM |
| Validation | 6,054 | Select C |
| Calibration | 6,055 | Fit sigmoid calibration |
| Test | 12,110 | Evaluate the selected model |

“On the full held-out article test set, accuracy is 96.31 percent. Misleading-class precision is 96.51 percent, recall is 94.99 percent, and F1 is 95.74 percent. These full-test figures include low-confidence articles.

“Accuracy measures overall agreement with dataset labels. Precision measures how often an article predicted as misleading has that dataset label. Recall measures how many misleading-labeled articles the system identifies. F1 balances precision and recall.

“These results describe this historical English-news benchmark. The partitions are duplicate-group-disjoint, but they are not source-held-out or time-held-out. Some dataset labels may reflect publisher categories rather than individual claim verification.

“Current Indian-news accuracy has not been measured. A separate diagnostic on 798 LIAR short political claims achieved 47.24 percent accuracy. That is a different task and domain, and the lower result demonstrates why the article benchmark score cannot be generalized to every input.”

If asked about the confusion matrix: rows are actual credible/misleading labels and columns are predicted credible/misleading labels. The counts are [[6634, 182], [265, 5029]]. The model correctly classified 11,663 of 12,110 test articles and made 447 errors.

If asked about numeric labels: the project explicitly maps the distributed CSV’s 0 to real and 1 to fake. The model card documents a discrepancy with the dataset webpage description and explains the count/source audit behind this interpretation.

## 12. Demonstrate persistence and close

[Reload the report. Open History and Dashboard. Optionally export or print.]

“This report has been stored with its article text, prediction, model version, linguistic insights, candidate claims, and evidence status. Reloading retrieves the saved report. History and dashboard views use records belonging to this browser’s anonymous session.

“The model version helps identify which artifact produced the result. Saved reports are not silently rescored after a model update. The application also provides report export and print-to-PDF options.

“To conclude, VeriFact AI implements the complete workflow from article input and preprocessing to supervised classification, transparent feature contributions, linguistic inspection, and saved reports. Its value is that users can understand what influenced a prediction and identify what still needs investigation.

“The present system supports credibility screening. Further work includes evaluation on current Indian news, stronger entity handling, contextual language analysis, multilingual support, and evidence-based assessment of individual claims.”

## Technical preparation: equations in plain language

Let x_i be an article’s TF-IDF feature value and w_i its fitted SVM coefficient.

```text
SVM decision score:
    f = sum(x_i × w_i) + b

Calibration, fitted on a separate partition:
    z = alpha × f + beta
    P(misleading) = 1 / (1 + exp(-z))
    P(credible) = 1 - P(misleading)

Displayed signed contribution:
    c_i = x_i × w_i × alpha

Complete calibrated log-odds:
    z = sum(all c_i) + (alpha × b + beta)

Displayed model confidence:
    max(P(credible), P(misleading))

Feature bar length:
    abs(c_i) / largest displayed abs(c_j)

Sentiment balance:
    (positive_matches - negative_matches)
    / max(1, positive_matches + negative_matches)
```

For this model’s interface, positive contributions point toward misleading and negative contributions toward credible. A feature’s sign describes a model association; it is not a factual rating of that word.

## Likely viva questions and short answers

**What exactly is your architecture?**

“A Next.js frontend calls a FastAPI backend through a same-origin proxy. The backend runs TF-IDF/SVM inference, trained spaCy annotations, separate language rules, optional evidence lookup, and SQLAlchemy persistence. It returns a structured report.”

**Where is machine learning used?**

“The supervised SVM is fitted on labeled article vectors. The sigmoid calibrator is fitted on separate scores. The linguistic annotations use a pretrained spaCy model. Explicit cue matching remains rule based.”

**Why use a linear SVM?**

“It suits sparse text vectors and provides direct additive feature explanations. It is a practical baseline with measured benchmark performance. This project has not established that it outperforms every transformer.”

**Are you using BERT, ChatGPT, or an LLM?**

“The active report uses TF-IDF and a calibrated linear SVM. Summaries are extractive. A transformer adapter exists as an extension point, but no trained transformer powers this demo.”

**Is this RAG?**

“The active workflow does not retrieve evidence to generate an evidence-grounded answer. Optional related fact-check search is a separate feature, and no automatic entailment verdict is implemented.”

**Are the explanations SHAP or LIME?**

“No. They are exact additive feature contributions to the calibrated linear model’s log-odds.”

**Does your summary use the same TF-IDF as the classifier?**

“No. Classification reuses a fitted training-corpus vectorizer. Summarization builds a separate sentence-level TF-IDF representation for the submitted article.”

**Do sentiment and clickbait counts cause the prediction?**

“No. The classifier uses article TF-IDF features. Those counts are separate report observations.”

**Why is October red while the article is Likely Credible?**

“It is one positive contribution toward misleading. All active features and the intercept determine the result; their combined score favors credible in this report.”

**Does red mean a factual error?**

“No. It shows the direction of a learned model contribution. The displayed context still needs evidence-based review.”

**Why is sentiment 1.00 in a report about a dispute?**

“Only ‘good’ and ‘gain’ match the small positive list, and no negative-list words match. The ratio is therefore one. The method does not understand the full situation or quoted context.”

**Why are some entities incorrect?**

“The pretrained general English entity model can misclassify unfamiliar names, abbreviations, or references. Domain evaluation and adaptation are future improvements.”

**Can this verify the court case or its dates?**

“No. It can identify references and candidate statements. Confirming those facts requires original documents and reliable sources.”

**How do you reduce data leakage?**

“Exact and conflicting duplicates are removed. Approximate duplicate groups stay within one partition. Vocabulary fitting, parameter selection, calibration, and testing use separate partitions. Source and temporal overlap remain limitations.”

**Does a 65 percent threshold mean 65 percent accuracy?**

“No. It is a decision policy based on the maximum class estimate. Accuracy is measured separately against held-out labels.”

**Does entering a new article train the model?**

“No. It performs inference with saved artifacts and stores a report. Training is an explicit offline process.”

**What is your contribution if libraries already provide the algorithms?**

“My contribution is the integrated application and reproducible workflow: data preparation and grouped evaluation, consistent inference preprocessing, calibrated classification, direct feature explanations, local NLP inspection, report persistence, and clear separation of predictions from evidence status.”

## Rehearsal checklist

1. Start the prepared project from its root with `./scripts/dev.sh` if the services are not already running. Open `http://127.0.0.1:3000` consistently in the same browser session. Do not retrain simply to run the demo.
2. Keep the full article available as text in case a publisher URL cannot be extracted.
3. Follow this order: Analyze → prediction → content summary → entities/topics → grammar → feature explanation → language cues/snapshot → claims → evidence status → metrics → history.
4. Practice the three most important distinctions: model confidence versus truth; feature contribution versus factual error; rule matches versus comprehensive language understanding.
5. Use the exact current report values. The matching saved report has 1,049 words, 59 sentences, 17.8 average sentence length, 1.00 lexical sentiment, and 95.61 percent credible-class confidence.
6. Prepare for the visible entity mistakes, the red October feature, and unconfigured evidence panel; explain each openly.

## Implementation references

- `docs/ARCHITECTURE.md`: architecture and request lifecycle.
- `docs/ARTICLE-MODEL.md`: active model card, evaluation, and limitations.
- `backend/training/articles.py`: preparation, splits, vectorizer, SVM selection, and calibration.
- `backend/artifacts/articles/metrics.json`: saved benchmark metrics.
- `backend/app/ml/article_classifier.py`: inference, contributions, and uncertainty policy.
- `backend/app/services/nlp.py`: spaCy analysis, summary, topics, and grammar.
- `backend/app/services/linguistics.py`: lexicons, cue rules, and candidate claims.
- `backend/app/services/analysis.py`: orchestration and persistence.
- `backend/app/services/evidence.py`: optional fact-check search.

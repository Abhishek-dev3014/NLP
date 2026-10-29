import Link from "next/link";
import {
  ArrowRight,
  AudioLines,
  BrainCircuit,
  Database,
  FileText,
  Fingerprint,
  Layers3,
  Link2,
  ScanText,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeading } from "@/components/common";
const pipeline = [
  {
    icon: ScanText,
    title: "Understand the language",
    text: "A trained spaCy English pipeline identifies tokens, base forms, parts of speech, named entities, and dependency relationships. You can inspect these annotations in every new report or the NLP lab.",
    example: "borrowed → borrow · VERB; London → GPE (place)",
  },
  {
    icon: FileText,
    title: "Extract the main sentences",
    text: "TF-IDF sentence vectors are ranked by similarity to a document centroid. Up to three original sentences form the extractive summary. Noun lemmas identify recurring topics. The first 200 sentences are considered.",
    example:
      "Original sentences → TF-IDF vectors → centrality ranking → original excerpts",
  },
  {
    icon: FileText,
    title: "Start with the article",
    text: "Submit English text, extract a publicly available article URL, or read a TXT/PDF document. Review extracted content before requesting analysis.",
    example: "Headline + content → validated text (12 words minimum)",
  },
  {
    icon: Sparkles,
    title: "Clean without erasing meaning",
    text: "Normalize Unicode, decode HTML entities, remove markup, and collapse whitespace. Preserve negation, named entities, and punctuation that may carry information.",
    example: "<p>The budget is NOT final.</p> → The budget is NOT final.",
  },
  {
    icon: ScanText,
    title: "Tokenize and preprocess",
    text: "The TF-IDF vectorizer identifies word tokens and word pairs. A shared cleaning function runs at training and inference. Stopwords are retained; stemming is not applied.",
    example:
      "“not approved today” → not · approved · today · not approved · approved today",
  },
  {
    icon: Layers3,
    title: "Turn language into TF-IDF features",
    text: "Term frequency represents use within the claim. Inverse document frequency lowers the weight of terms common across training examples. The fitted training vocabulary is reused during inference.",
    example:
      "TF-IDF(term, document) = sublinear TF × inverse document frequency",
  },
  {
    icon: BrainCircuit,
    title: "Run a trained linear classifier",
    text: "A linear Support Vector Machine learns a decision boundary from WELFake article bodies. Similar articles remain in the same data partition. A separate calibration set maps decision scores to class probabilities.",
    example:
      "P(fake-pattern class) = sigmoid(calibration slope × SVM decision + intercept)",
  },
  {
    icon: Fingerprint,
    title: "Explain the prediction",
    text: "Multiply each TF-IDF value by its SVM coefficient and calibration slope to explain the prediction. Show model confidence separately from factual verification, and mark short or ambiguous inputs uncertain.",
    example:
      "Contribution of “federal budget” = TF-IDF value × SVM coefficient × calibration slope",
  },
  {
    icon: Link2,
    title: "Look for evidence, optionally",
    text: "If configured and explicitly requested, query Google Fact Check Tools using a headline or candidate claim. Display only returned sources, with no automatic inference of support or contradiction.",
    example:
      "Model attribution ≠ linguistic heuristic ≠ external factual evidence",
  },
  {
    icon: Database,
    title: "Build a report you can revisit",
    text: "Persist the actual result, language observations, candidate claims, and evidence with SQLAlchemy. Reports are isolated by a signed anonymous browser session and can be deleted.",
    example:
      "Frontend → FastAPI → preprocessing → inference → database → report",
  },
];
const concepts = [
  [
    "Natural Language Processing",
    "Computational methods for analyzing human language. NLP can describe patterns; factual verification also requires reliable evidence.",
  ],
  [
    "Supervised learning",
    "The model learns associations from examples with known dataset labels, rather than from handwritten lists of suspicious words.",
  ],
  [
    "Training, validation & testing",
    "Training learns weights. Validation selects regularization. A separate calibration partition fits probabilities. The test partition provides final metrics; duplicate groups are kept apart.",
  ],
  [
    "Stopword removal",
    "Common words can be removed for some tasks, but we retain them here to preserve context and negation. A transformer must use its own compatible tokenizer.",
  ],
  [
    "Precision & recall",
    "Precision asks how often a misleading prediction matches the label. Recall asks how many misleading-labeled claims the model finds.",
  ],
  [
    "F1-score",
    "The harmonic mean of precision and recall: 2 × precision × recall / (precision + recall). It balances the two types of performance.",
  ],
  [
    "Confusion matrix",
    "A table of actual versus predicted labels. The diagonal counts correct classifications; off-diagonal cells expose specific errors.",
  ],
  [
    "Confidence & calibration",
    "The article model uses sigmoid calibration fitted on separate articles. This makes scores more interpretable on its benchmark, but does not guarantee calibration on current Indian news. Confidence is not a truth probability.",
  ],
];
export default function HowPage() {
  return (
    <div className="page-article">
      <PageHeading
        eyebrow="MODEL EXPLAINED"
        title="From words to insight. Every step, explained."
        description="A real NLP pipeline, without the mystery. Explore how VeriFact transforms article text into transparent, reviewable observations."
      />
      <div className="pipeline">
        {pipeline.map(({ icon: Icon, title, text, example }, index) => (
          <section className="pipeline-step" key={title}>
            <div className="pipeline-icon">
              <Icon size={21} />
            </div>
            <div className="panel panel-body">
              <div className="pipeline-number">
                STEP {String(index + 1).padStart(2, "0")}
              </div>
              <h2>{title}</h2>
              <p>{text}</p>
              <code>{example}</code>
            </div>
          </section>
        ))}
      </div>
      <section className="mt-12">
        <p className="eyebrow">THE CONCEPTS BEHIND THE CODE</p>
        <h2>Ready for a deeper conversation.</h2>
        <div className="concept-grid">
          {concepts.map(([title, text]) => (
            <article className="panel concept-card" key={title}>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
      <div className="transparency-note">
        <AudioLines size={17} />
        <p>
          Emotional words, urgency, and certainty are rule-based observations.
          Candidate claims are sentence-selection heuristics. Neither is the
          trained classifier, and neither establishes factual truth.
        </p>
      </div>
      <div className="flex gap-3 mt-8 flex-wrap">
        <Button asChild>
          <Link href="/analyze">
            Explore it yourself <ArrowRight size={15} />
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/nlp-lab">Open the interactive NLP lab</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/model-performance">See real evaluation results</Link>
        </Button>
      </div>
    </div>
  );
}

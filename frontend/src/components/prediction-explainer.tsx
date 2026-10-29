"use client";

import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Fingerprint,
  ScanText,
  Workflow,
} from "lucide-react";
import type { Analysis, Feature, Highlight } from "@/lib/types";

const cueExplanations: Record<
  string,
  { concept: string; concern: string; check: string }
> = {
  clickbait: {
    concept: "Rule-based phrase matching · regular expressions",
    concern:
      "This phrase tries to attract attention or create urgency. That can encourage readers to react before checking the evidence.",
    check:
      "Pause before sharing. Check the original report and whether its evidence supports the claim.",
  },
  emotional: {
    concept: "Lexical cue detection · regular expressions",
    concern:
      "This is emotionally charged wording. It can make a claim feel more dramatic without adding evidence for it.",
    check:
      "Read the factual statement without the emotional wording, then look for supporting evidence.",
  },
  certainty: {
    concept: "Certainty cue detection · lexical pattern matching",
    concern:
      "This wording expresses strong or absolute certainty. A confident tone can make a claim sound better established than the evidence warrants.",
    check:
      "Check whether the evidence justifies the certainty and whether important exceptions or limitations are missing.",
  },
};

function Context({
  text,
  term,
  highlights,
}: {
  text: string;
  term: string;
  highlights: Highlight[];
}) {
  const escaped = term
    .split(/\s+/)
    .map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("\\s+");
  const matches = [...text.matchAll(new RegExp(`\\b${escaped}\\b`, "gi"))];
  // Prefer an occurrence overlapping a real returned cue, so the excerpt and
  // contextual explanation refer to the same occurrence of the feature.
  const overlap = (m: RegExpMatchArray) =>
    highlights.find(
      (h) =>
        cueExplanations[h.kind] &&
        h.start >= 0 &&
        h.end <= text.length &&
        h.start < m.index! + m[0].length &&
        h.end > m.index!,
    );
  const match = matches.find((m) => overlap(m)) || matches[0];
  const cue = match ? overlap(match) : undefined;
  const explanation = cue ? cueExplanations[cue.kind] : undefined;
  const start = match ? Math.max(0, match.index! - 100) : 0;
  const end = match
    ? Math.min(text.length, match.index! + match[0].length + 140)
    : 0;
  return (
    <>
      {match ? (
        <blockquote className="explain-excerpt">
          {start > 0 && "…"}
          {text.slice(start, match.index)}
          <mark>{match[0]}</mark>
          {text.slice(match.index! + match[0].length, end)}
          {end < text.length && "…"}
        </blockquote>
      ) : (
        <p className="input-note">
          This feature occurs in the normalized model input. An exact excerpt is
          unavailable in the original text.
        </p>
      )}
      <div className="feature-concern">
        <h4>What is concerning here?</h4>
        {cue && explanation ? (
          <>
            <p className="matched-cue">
              Matched wording: <q>{text.slice(cue.start, cue.end)}</q>
            </p>
            <p>
              {cue.kind === "clickbait" &&
              text.slice(cue.start, cue.end).toLowerCase() === "share before"
                ? "“Share before” creates time pressure: it encourages circulation before the reader checks the claim. The concern is this appeal to urgency, not the word “share” on its own."
                : explanation.concern}
            </p>
            <h4>NLP concept used for this cue</h4>
            <p>
              {explanation.concept}. The system matched an existing language
              pattern in this excerpt.
            </p>
            <h4>How to check it</h4>
            <p>{explanation.check}</p>
            <p className="feature-context-limit">
              This phrase may be quoted, criticized, or denied in the article.
              The rule detects wording; it does not establish the author’s
              intent or prove the claim false.
            </p>
          </>
        ) : (
          <>
            <p>
              No specific language problem was detected for{" "}
              <strong>“{term}”</strong> by the implemented cue rules. It is not
              an incorrect word. Its model weight reflects a learned association
              with training labels, which may include dataset bias.
            </p>
            <p className="feature-context-limit">
              A red bar alone does not identify a factual error. Check the
              actual claim and its source.
            </p>
          </>
        )}
      </div>
    </>
  );
}

export function PredictionExplainer({ result }: { result: Analysis }) {
  const [view, setView] = useState("model");
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null);
  const features = [...result.prediction.features].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution),
  );
  const selected = features.find((f) => f.term === selectedTerm) || features[0];
  const maximum = Math.max(
    ...features.map((f) => Math.abs(f.contribution)),
    0.001,
  );
  const articleModel =
    result.prediction.assessment_scope === "article_screening";
  const leading = features
    .filter(
      (f) =>
        f.direction ===
        (result.prediction.probabilities &&
        result.prediction.probabilities.misleading >= 0.5
          ? "misleading"
          : "credible"),
    )
    .slice(0, 3);
  const uncertain =
    result.prediction.label === "Needs Further Verification" ||
    result.prediction.label === "Insufficient Evidence" ||
    (!articleModel && !result.prediction.in_domain);
  function featureButton(f: Feature) {
    return (
      <button
        key={f.term}
        type="button"
        className={`explain-feature ${f.direction}`}
        aria-pressed={selected?.term === f.term}
        onClick={() => setSelectedTerm(f.term)}
      >
        <span className="explain-feature-name">
          {f.direction === "misleading" ? (
            <ArrowUpRight size={16} />
          ) : (
            <ArrowDownLeft size={16} />
          )}
          <b>{f.term}</b>
        </span>
        <span className="explain-meter" aria-hidden="true">
          <i
            style={{ width: `${(Math.abs(f.contribution) / maximum) * 100}%` }}
          />
        </span>
        <span>
          {f.direction === "misleading"
            ? "Toward misleading"
            : "Toward credible"}
        </span>
      </button>
    );
  }
  return (
    <section
      className="panel explanation-studio"
      aria-labelledby="explanation-title"
      id="explanation"
    >
      <div className="explain-heading">
        <div>
          <span className="explain-eyebrow">
            <Fingerprint size={14} /> BEHIND THE PREDICTION
          </span>
          <h2 id="explanation-title">Why did it get this result?</h2>
          <p>Follow the language signals. See what influenced the model.</p>
        </div>
        <span className="method-tag">Explainable NLP</span>
      </div>
      <div className="explain-overview">
        <strong>
          {features.length === 0
            ? "Feature-level explanations are unavailable for this report."
            : uncertain
              ? "The result needs a closer look."
              : result.prediction.label === "Potentially Misleading"
                ? "The model found patterns associated with misleading articles."
                : "The model found patterns associated with credible articles."}
        </strong>
        <p>
          {leading.length ? (
            <>
              Among the strongest displayed signals toward the model’s
              higher-scoring class are{" "}
              {leading.map((f) => `“${f.term}”`).join(", ")}. These are learned
              associations; the words themselves do not establish whether a
              claim is true.
            </>
          ) : features.length ? (
            "None of the displayed features points toward the higher-scoring class. The full prediction also includes other features and the model’s intercept; this list is only a partial explanation."
          ) : (
            "No feature contributions are available for this report. The language review below can still help you inspect the article."
          )}
        </p>
        {uncertain && (
          <p>
            The application has not accepted a confident classification. Add
            context and check the source before drawing a conclusion.
          </p>
        )}
      </div>
      <div
        className="explain-switch"
        role="group"
        aria-label="Explanation view"
      >
        {[
          { id: "model", title: "Words that influenced it", icon: Fingerprint },
          { id: "language", title: "Language cues", icon: ScanText },
          { id: "method", title: "How NLP works", icon: Workflow },
        ].map(({ id, title, icon: Icon }) => (
          <button
            type="button"
            key={id}
            aria-pressed={view === id}
            aria-controls="explanation-content"
            onClick={() => setView(id)}
          >
            <Icon size={15} />
            {title}
          </button>
        ))}
      </div>
      <div id="explanation-content" className="explain-content">
        {view === "model" && (
          <>
            <p className="explain-help">
              Select a word or phrase to inspect its context. Longer bars mean a
              stronger contribution among the displayed features.
            </p>
            {selected ? (
              <div className="explain-workbench">
                <div
                  className="explain-feature-list"
                  aria-label="Model features"
                >
                  {features.map(featureButton)}
                </div>
                <div
                  className="explain-detail"
                  aria-live="polite"
                  aria-atomic="true"
                >
                  <span className="explain-eyebrow">
                    {selected.term.trim().split(/\s+/).length > 1
                      ? "BIGRAM · TWO-WORD FEATURE"
                      : "UNIGRAM · WORD FEATURE"}
                  </span>
                  <h3>“{selected.term}”</h3>
                  <span className={`explain-direction ${selected.direction}`}>
                    {selected.direction === "misleading"
                      ? "↑ Pushes toward misleading"
                      : "↓ Pushes toward credible"}
                  </span>
                  <Context
                    text={result.text}
                    term={selected.term}
                    highlights={result.highlights}
                  />
                  <h4>NLP concepts behind the model contribution</h4>
                  <p>
                    <strong>
                      {selected.term.trim().split(/\s+/).length > 1
                        ? "Bigram extraction"
                        : "Unigram extraction"}
                    </strong>{" "}
                    identifies this feature. <strong>TF-IDF</strong> assigns its
                    numerical value, and{" "}
                    <strong>
                      {articleModel
                        ? "Linear SVM attribution"
                        : "linear-model attribution"}
                    </strong>{" "}
                    explains how its learned weight moves the score toward the{" "}
                    <strong>{selected.direction}</strong> class. It is one
                    contribution to the complete article prediction. Language
                    cue rules are a separate observation; they do not calculate
                    this weight.
                  </p>
                  <h4>What you should check</h4>
                  <p>
                    Read the surrounding statement and compare it with the
                    original source. Ordinary names, dates, and reporting
                    phrases can carry dataset bias.
                  </p>
                  <details className="explain-math">
                    <summary>See the technical contribution</summary>
                    <p>
                      <strong>
                        {selected.contribution > 0 ? "+" : ""}
                        {selected.contribution.toFixed(3)}
                      </strong>{" "}
                      score units.{" "}
                      {result.prediction.attribution_method ||
                        "TF-IDF value multiplied by the learned linear coefficient."}{" "}
                      This value is not a percentage. Only the strongest
                      features are displayed.
                    </p>
                  </details>
                </div>
              </div>
            ) : (
              <p>No model feature contributions are available.</p>
            )}
          </>
        )}
        {view === "language" && (
          <>
            <p className="explain-help">
              These separate rule-based observations help you read critically.
              They are not inputs to the current article classifier and do not
              prove misinformation.
            </p>
            <div className="explain-cue-grid">
              {[
                {
                  kind: "emotional",
                  name: "Emotional wording",
                  concept: "Lexical pattern matching",
                  detail:
                    "Strong emotional words can influence a reader’s reaction. Check whether the article also provides evidence.",
                },
                {
                  kind: "clickbait",
                  name: "Attention & urgency",
                  concept: "Phrase matching with regex",
                  detail:
                    "Attention-seeking phrases encourage clicks or fast sharing. Inspect the claim before acting on the headline.",
                },
                {
                  kind: "certainty",
                  name: "Absolute claims",
                  concept: "Certainty cue detection",
                  detail:
                    "Words such as ‘always’ or ‘guaranteed’ leave little room for exceptions. Look for evidence supporting that certainty.",
                },
              ].map((cue) => {
                const hits = result.highlights.filter(
                  (h) => h.kind === cue.kind,
                );
                return (
                  <article className="explain-cue" key={cue.kind}>
                    <span className="explain-cue-count">
                      {hits.length}
                      <small> matches</small>
                    </span>
                    <h3>{cue.name}</h3>
                    <span className="method-tag">{cue.concept}</span>
                    <p>{cue.detail}</p>
                    {hits.length ? (
                      <ul>
                        {hits.slice(0, 3).map((h) => (
                          <li key={h.start}>
                            <q>{result.text.slice(h.start, h.end)}</q>
                            <span>{h.reason}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="input-note">
                        No matches found. This does not establish credibility.
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          </>
        )}
        {view === "method" && (
          <div className="explain-method">
            <ol>
              {[
                [
                  "Prepare the text",
                  articleModel
                    ? "Normalize article text and remove some source markers. The article classifier reads up to 2,500 words."
                    : "Normalize the text and turn it into the features expected by this saved report’s model.",
                ],
                [
                  "Represent the language · TF-IDF",
                  "Turn words and two-word phrases into numerical features. Terms receive weight based on their frequency in this article and rarity across training articles.",
                ],
                [
                  articleModel
                    ? "Learned decision · Linear SVM"
                    : "Learned decision · Linear classifier",
                  "Combine feature values with weights learned from labelled examples. Positive contributions move toward the misleading class; negative contributions move toward the credible class.",
                ],
                [
                  "Express uncertainty · Calibration",
                  result.prediction.calibrated
                    ? "A fitted calibration model converts the decision score to class estimates. Calibration on a benchmark does not guarantee accuracy on a new topic or region."
                    : "This saved report has uncalibrated confidence. Its numerical score should be interpreted with additional caution.",
                ],
              ].map(([title, detail], index) => (
                <li key={title}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>{title}</h3>
                    <p>{detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <aside>
              <h3>Grammar helps you investigate</h3>
              <p>
                <strong>NER</strong> finds names, places and dates.{" "}
                <strong>Dependency parsing</strong> identifies grammatical
                relationships. <strong>Extractive summarization</strong> selects
                existing sentences to help you scan the story.
              </p>
              <p>
                These tools describe the content. Factual verification requires
                checking claims against supporting evidence.
              </p>
              <a href="#content-inspection" className="section-link">
                Explore this article’s NLP analysis ↓
              </a>
            </aside>
          </div>
        )}
      </div>
      <footer className="explain-footer">
        <ScanText size={15} />
        <span>
          Model associations explain the prediction. Primary evidence is needed
          to establish factual accuracy.
        </span>
        <a href="#claims-review">
          Review the claims <ArrowUpRight size={14} />
        </a>
      </footer>
    </section>
  );
}

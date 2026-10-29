"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PredictionExplainer } from "./prediction-explainer";
import { NLPInspector } from "./nlp-inspector";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  BookOpenCheck,
  Check,
  CheckCheck,
  CircleAlert,
  Clipboard,
  Download,
  ExternalLink,
  FileSearch,
  Info,
  Layers3,
  Link2,
  ListChecks,
  Printer,
  ScanText,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Analysis, Highlight } from "@/lib/types";
import { assessmentClass, formatDate, percent } from "@/lib/utils";
import { ErrorState, LoadingSkeleton, PageHeading } from "./common";
import { Button } from "./ui/button";
function HighlightedArticle({
  text,
  highlights,
}: {
  text: string;
  highlights: Highlight[];
}) {
  const pieces: React.ReactNode[] = [];
  let cursor = 0;
  for (const [index, h] of highlights.entries()) {
    if (h.start < cursor) continue;
    pieces.push(text.slice(cursor, h.start));
    pieces.push(
      <mark
        className={h.kind}
        key={index}
        title={h.reason}
        aria-label={`${h.text}: ${h.reason}`}
        tabIndex={0}
      >
        {text.slice(h.start, h.end)}
      </mark>,
    );
    cursor = h.end;
  }
  pieces.push(text.slice(cursor));
  return <div className="article-reading">{pieces}</div>;
}
function downloadReport(analysis: Analysis) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(analysis, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `verifact-${analysis.id}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function Results({ id }: { id: string }) {
  const router = useRouter();
  const query = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => api.analysis(id),
  });
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  if (query.isPending) return <LoadingSkeleton />;
  if (query.isError)
    return (
      <ErrorState message={query.error.message} retry={() => query.refetch()} />
    );
  const result = query.data;
  const { prediction: p, insights: i } = result;
  const articleModel = p.assessment_scope === "article_screening";
  const hasPrediction = articleModel || p.in_domain;
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        `${result.headline}\n${result.prediction.label}\nNLP model confidence: ${percent(result.prediction.confidence)} (${result.prediction.calibrated ? "calibrated on its benchmark" : "uncalibrated"}; not a truth probability).\n${result.explanation}\n${result.evidence.message}\n${result.prediction.warnings.join("\n")}`,
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopyError(
        "Clipboard permission is unavailable. Save the JSON report or use Print instead.",
      );
    }
  }
  return (
    <div className="report-experience">
      <PageHeading
        eyebrow="A CLOSER LOOK, IN CONTEXT"
        title="Your analysis report"
        description={`Analyzed ${formatDate(result.created_at)} · ${i.word_count.toLocaleString()} words · ${result.input_type.toUpperCase()} input`}
        action={
          <div className="result-actions">
            <Button variant="outline" size="sm" onClick={copy}>
              {copied ? <Check size={13} /> : <Clipboard size={13} />}{" "}
              {copied ? "Copied" : "Copy summary"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadReport(result)}
            >
              <Download size={13} /> Save report
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer size={13} /> Print / PDF
            </Button>
          </div>
        }
      />
      {copyError && <ErrorState message={copyError} />}
      <section className="panel result-assessment">
        <div>
          <div className="report-meta">
            <FileSearch size={12} /> MODEL ASSESSMENT <span>·</span>
            <CheckCheck size={12} /> Saved to history
          </div>
          <h2 className={assessmentClass(p.label)}>
            {hasPrediction ? p.label : "Needs Further Verification"}
          </h2>
          <p className="report-title">{result.headline}</p>
          <p>
            {articleModel
              ? p.decision_reason
              : p.in_domain
                ? "The classifier identified language associated with its training labels. Review the feature explanations and investigate the claims before drawing a conclusion."
                : "This input is outside the model’s validated domain, or the model is unavailable. Language observations can guide your review; the classification should not be relied on."}
          </p>
          {result.source_url && (
            <a
              className="section-link mt-3"
              href={result.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open original source <ExternalLink size={11} />
            </a>
          )}
        </div>
        <div className="prediction-section">
          <h3>Model confidence</h3>
          <strong>
            {hasPrediction ? percent(p.confidence) : "Not available"}
          </strong>
          <p>
            {hasPrediction
              ? `Maximum class estimate · ${p.calibrated ? "Calibrated" : "Uncalibrated"}`
              : "Outside the classifier’s scope"}
          </p>
          {hasPrediction && p.probabilities && (
            <>
              <div
                className="prediction-bar"
                role="img"
                aria-label={`Credible class ${percent(p.probabilities.credible)}, misleading class ${percent(p.probabilities.misleading)}`}
              >
                <span
                  style={{
                    width: `${p.probabilities.credible * 100}%`,
                    background: "var(--emerald)",
                  }}
                />
                <span
                  style={{
                    width: `${p.probabilities.misleading * 100}%`,
                    background: "var(--coral)",
                  }}
                />
              </div>
              <div className="prediction-labels">
                <span className="emerald">
                  Credible class {percent(p.probabilities.credible)}
                </span>
                <span className="coral">
                  Misleading class {percent(p.probabilities.misleading)}
                </span>
              </div>
            </>
          )}
          <p>
            Confidence describes the model’s output, not the probability that
            this content is factually true.
          </p>
        </div>
      </section>
      {articleModel && (
        <div className="scope-note">
          <strong>Benchmark confidence, not verified truth</strong>
          <p>
            {p.evaluated_domain}. A high score can still be wrong when the
            article differs from the training data.
          </p>
        </div>
      )}
      {articleModel && (
        <div className="assessment-facts">
          <div>
            <span>Prediction</span>
            <strong>
              {p.label === "Needs Further Verification"
                ? "Uncertain"
                : p.probabilities && p.probabilities.misleading >= 0.5
                  ? "Fake / misleading pattern"
                  : "Real-news pattern"}
            </strong>
            <p>A learned article classification.</p>
          </div>
          <div>
            <span>Factual verification</span>
            <strong>Not independently verified</strong>
            <p>
              {result.evidence.items.length
                ? "Related sources need human review."
                : "No supporting or contradicting evidence has been checked."}
            </p>
          </div>
          <div>
            <span>What to do next</span>
            <strong>
              {p.label === "Potentially Misleading"
                ? "Verify before sharing"
                : "Check the key claims"}
            </strong>
            <p>Read the source, date, and primary evidence.</p>
          </div>
        </div>
      )}
      <div className="report-guide">
        <div>
          <span>01</span>
          <strong>Understand</strong>
          <p>Read the summary and identify the main claims.</p>
        </div>
        <div>
          <span>02</span>
          <strong>Inspect</strong>
          <p>Explore language patterns and model limitations.</p>
        </div>
        <div>
          <span>03</span>
          <strong>Verify</strong>
          <p>Check dates, sources, and original evidence.</p>
        </div>
      </div>
      <PredictionExplainer result={result} />
      <div id="content-inspection">
        <NLPInspector data={result.nlp} />
      </div>
      {!articleModel && p.decision_reason && (
        <div className="info-note mb-6">{p.decision_reason}</div>
      )}
      <div className="result-grid">
        <div className="result-stack">
          <section className="panel">
            <div className="panel-header">
              <h2>
                <ScanText size={15} /> Read between the lines
              </h2>
              <span className="method-tag">Linguistic heuristics</span>
            </div>
            <div className="panel-body">
              <HighlightedArticle
                text={result.text}
                highlights={result.highlights}
              />
              <div className="highlight-legend">
                <span className="coral">Emotional wording</span>
                <span style={{ color: "var(--accent)" }}>Clickbait cues</span>
                <span className="amber">Certainty cues</span>
              </div>
              {result.highlights.length === 0 && (
                <p className="input-note">
                  No phrases matched the implemented language patterns. That
                  does not establish factual credibility.
                </p>
              )}
            </div>
          </section>
          <section className="panel" id="claims-review">
            <div className="panel-header">
              <h2>
                <ListChecks size={15} /> Claims worth verifying
              </h2>
              <span className="method-tag">
                {result.claims.length} candidates
              </span>
            </div>
            {result.claims.length ? (
              result.claims.map((claim, index) => (
                <div className="claim-item" key={claim.start}>
                  <div className="claim-top">
                    <span>
                      CLAIM {String(index + 1).padStart(2, "0")} · CHARACTERS{" "}
                      {claim.start + 1}–{claim.end}
                    </span>
                    <span className="amber">{claim.status}</span>
                  </div>
                  <blockquote>{claim.text}</blockquote>
                  <p>{claim.reason}</p>
                  <a
                    className="section-link mt-3"
                    href={`https://www.google.com/search?q=${encodeURIComponent(claim.text.slice(0, 350))}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Search this claim online <ExternalLink size={12} />
                  </a>
                  {claim.text.split(/\s+/).length >= 12 && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() => {
                        sessionStorage.setItem("verifact-claim", claim.text);
                        router.push("/analyze");
                      }}
                    >
                      Analyze this claim <ArrowRight size={13} />
                    </Button>
                  )}
                </div>
              ))
            ) : (
              <div className="panel-body">
                <p className="report-explanation">
                  No candidate claims matched our sentence-selection rules.
                  Claim extraction is incomplete and does not replace human
                  review.
                </p>
              </div>
            )}
            <div className="info-note">
              <Info size={12} /> Candidates are exact excerpts selected by
              linguistic rules. No factual verification has been performed.
            </div>
          </section>
        </div>
        <div className="result-stack">
          <section className="panel">
            <div className="panel-header">
              <h2>
                <AudioLines size={15} /> A language snapshot
              </h2>
              <span className="panel-label">NLP insights</span>
            </div>
            <div className="insights-grid">
              {[
                {
                  label: "Words",
                  value: i.word_count,
                  note: "Token pattern count",
                },
                {
                  label: "Sentences",
                  value: i.sentence_count,
                  note: "Sentence segmentation",
                },
                {
                  label: "Avg. sentence length",
                  value: i.average_sentence_length,
                  note: "Words per sentence",
                },
                {
                  label: "Sentiment balance",
                  value: i.sentiment_score.toFixed(2),
                  note: "Lexicon heuristic · −1 to +1",
                },
                {
                  label: "Clickbait cues",
                  value: i.clickbait_indicator,
                  note: "Matched phrases",
                },
                {
                  label: "Emotional cues",
                  value: i.emotional_indicator,
                  note: "Matched words",
                },
              ].map((metric) => (
                <div className="insight-item" key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.note}</small>
                </div>
              ))}
            </div>
            <div className="info-note">
              <Info size={12} />
              {i.method}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header">
              <h2>
                <Link2 size={15} /> External evidence
              </h2>
              <span className="method-tag">Separate from NLP</span>
            </div>
            {result.evidence.items.length ? (
              result.evidence.items.map((e) => (
                <div className="evidence-item" key={e.url}>
                  <small>
                    {e.source_name}
                    {e.publication_date
                      ? ` · ${formatDate(e.publication_date)}`
                      : ""}
                  </small>
                  <a href={e.url} target="_blank" rel="noopener noreferrer">
                    {e.title}
                    <ArrowUpRight size={12} />
                  </a>
                  <p>{e.summary}</p>
                  <small className="amber">{e.status}</small>
                </div>
              ))
            ) : (
              <div className="evidence-empty">
                <BookOpenCheck size={25} />
                <strong>
                  {result.evidence.status === "unconfigured"
                    ? "Evidence integration is not configured"
                    : result.evidence.status === "disabled"
                      ? "External search was not requested"
                      : "No conclusive evidence available"}
                </strong>
                <p>{result.evidence.message}</p>
              </div>
            )}
          </section>
          <section className="panel">
            <div className="panel-header">
              <h2>
                <ShieldCheck size={15} /> Your next steps
              </h2>
            </div>
            <div className="panel-body">
              <ul className="recommendations">
                {result.recommendations.map((r) => (
                  <li key={r}>
                    <Check size={13} />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </section>
          <section className="panel">
            <div className="panel-header">
              <h2>
                <CircleAlert size={15} /> Keep the limits in view
              </h2>
            </div>
            <ul className="warning-list">
              {p.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
            <div className="info-note">
              <Layers3 size={12} />
              <span>
                {p.model_name}
                <br />
                <span className="font-mono text-[8px]">{p.model_version}</span>
                <br />
                <Link className="section-link mt-2" href="/model-performance">
                  Explore evaluation metrics <ArrowUpRight size={11} />
                </Link>
              </span>
            </div>
          </section>
        </div>
      </div>
      <div className="report-bottom">
        <div>
          <p className="success-message">
            <CheckCheck size={13} /> This report is saved in your session
            history.
          </p>
          <Link href="/history" className="section-link mt-2">
            View your research history <ArrowRight size={12} />
          </Link>
        </div>
        <Button asChild>
          <Link href="/analyze">
            Analyze another article <ArrowRight size={15} />
          </Link>
        </Button>
      </div>
    </div>
  );
}

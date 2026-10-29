"use client";
import { BookOpen, Braces, Network, Tags } from "lucide-react";
import type { NLPAnalysis } from "@/lib/types";
const entityNames: Record<string, string> = {
  PERSON: "Person",
  ORG: "Organization",
  GPE: "Place",
  DATE: "Date",
  MONEY: "Money",
  PERCENT: "Percentage",
  CARDINAL: "Number",
  NORP: "Group",
  LOC: "Location",
  EVENT: "Event",
};
export function NLPInspector({ data }: { data?: NLPAnalysis | null }) {
  if (!data) return null;
  if (!data.available) return <div className="info-note">{data.message}</div>;
  return (
    <section className="panel nlp-inspector">
      <div className="panel-header">
        <div>
          <h2>
            <BookOpen size={17} /> Understand the content
          </h2>
          <p>Key sentences, people, places, and topics</p>
        </div>
        <span className="method-tag">Local NLP</span>
      </div>
      <div className="panel-body">
        <h3 className="nlp-label">
          At a glance <span>Extractive summary</span>
        </h3>
        {data.summary?.length ? (
          <ol className="summary-list">
            {data.summary.map((s) => (
              <li key={s.start}>{s.text}</li>
            ))}
          </ol>
        ) : (
          <p>No sufficiently informative sentences were found for a summary.</p>
        )}
        <p className="input-note">{data.summary_scope}</p>
        <div className="nlp-two-col">
          <div>
            <h3 className="nlp-label">
              <Tags size={15} /> Names & references
            </h3>
            <div className="entity-list">
              {data.entities?.length ? (
                data.entities.map((e, i) => (
                  <span className="entity-chip" key={`${e.start}-${i}`}>
                    <b>{e.text}</b>
                    <small>{entityNames[e.label] || e.label}</small>
                  </span>
                ))
              ) : (
                <p>No named entities detected.</p>
              )}
            </div>
          </div>
          <div>
            <h3 className="nlp-label">Recurring topics</h3>
            <div className="entity-list">
              {data.topics?.map((t) => (
                <span className="topic-chip" key={t.term}>
                  {t.term} <small>×{t.count}</small>
                </span>
              ))}
            </div>
            <p className="input-note">
              Nouns grouped by their base form. Entity recognition can make
              mistakes.
            </p>
          </div>
        </div>
      </div>
      <details className="nlp-details">
        <summary>
          <Braces size={16} /> Explore the NLP · tokens, lemmas & grammar
        </summary>
        <div className="panel-body">
          <p className="input-note">
            Tokenization splits text into units. Lemmatization finds base forms.
            POS identifies grammatical roles. Showing up to 120 of{" "}
            {data.token_count} tokens.
          </p>
          <div className="nlp-table-wrap">
            <table className="nlp-table">
              <thead>
                <tr>
                  <th>Token</th>
                  <th>Base form</th>
                  <th>Part of speech</th>
                  <th>Morphology</th>
                </tr>
              </thead>
              <tbody>
                {data.tokens?.map((t) => (
                  <tr key={t.start}>
                    <td>{t.text}</td>
                    <td>{t.lemma}</td>
                    <td>{t.pos}</td>
                    <td>{t.morphology || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3 className="nlp-label mt-6">
            <Network size={16} /> Dependency parsing
          </h3>
          <p className="syntax-sentence">{data.dependency_sentence}</p>
          <p className="input-note">
            Each word points to its grammatical head. “ROOT” is the main
            predicate. Showing up to 35 tokens from one sentence.
          </p>
          <div className="dependency-list">
            {data.dependencies?.map((d) => (
              <span key={d.start}>
                <b>{d.text}</b> <em>{d.relation}</em> → {d.head}
              </span>
            ))}
          </div>
          <p className="input-note mt-4">
            {data.method} · {data.pipeline}
          </p>
        </div>
      </details>
    </section>
  );
}

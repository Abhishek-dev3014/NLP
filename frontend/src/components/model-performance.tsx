"use client";
import { ArticleEvaluation } from "./article-evaluation";
import { TrainingReview } from "./training-review";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  CircleAlert,
  FlaskConical,
  Info,
  Layers3,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDate, percent } from "@/lib/utils";
import { ErrorState, LoadingSkeleton, PageHeading } from "./common";
const explanations = {
  Accuracy: "Share of all held-out claims classified correctly.",
  Precision: "Of claims predicted misleading, the share labeled misleading.",
  Recall: "Of claims labeled misleading, the share the model identified.",
  "F1-score": "Harmonic mean of misleading-class precision and recall.",
  "ROC-AUC": "Ranking separation across all probability thresholds.",
};
export function ModelPerformance() {
  const query = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });
  if (query.isPending) return <LoadingSkeleton />;
  if (query.isError)
    return (
      <ErrorState message={query.error.message} retry={() => query.refetch()} />
    );
  const m = query.data;
  if (!m.available)
    return (
      <>
        <PageHeading
          eyebrow="TRANSPARENCY IS PART OF THE MODEL"
          title="Model performance"
          description="Actual evaluation results. Documented methodology. Clear limitations."
        />
        <div className="panel panel-body">
          <h2 className="text-xl mb-4">Evaluation unavailable</h2>
          <p className="text-sm">{m.message}</p>
          <pre className="mt-5 text-xs text-[var(--accent)] whitespace-pre-wrap">
            cd backend{"\n"}../.venv/bin/python -m training.download_articles
            {"\n"}
            ../.venv/bin/python -m training.articles
          </pre>
        </div>
      </>
    );
  return (
    <>
      <PageHeading
        eyebrow="TRANSPARENCY IS PART OF THE MODEL"
        title="Beyond the prediction"
        description="A clear view of the data, evaluation, and limits behind your NLP analysis."
      />
      <div className="panel model-overview">
        <div>
          <p className="eyebrow">ACTIVE CLASSIFIER</p>
          <h2>{m.model_name}</h2>
          <p>Text-only supervised learning · {m.dataset}</p>
          <div className="model-version">{m.version}</div>
        </div>
        <div>
          <span className="assessment-badge emerald">
            <span /> Evaluated on held-out data
          </span>
          <p className="mt-3">
            Artifact generated {formatDate(m.evaluated_at)}
          </p>
        </div>
      </div>
      <div className="metrics-grid">
        {[
          { name: "Accuracy", value: m.accuracy },
          { name: "Precision", value: m.precision },
          { name: "Recall", value: m.recall },
          { name: "F1-score", value: m.f1 },
          { name: "ROC-AUC", value: m.roc_auc },
        ].map((metric) => (
          <div
            className="panel metric-card"
            title={explanations[metric.name as keyof typeof explanations]}
            key={metric.name}
          >
            <p>{metric.name}</p>
            <strong>
              {metric.name === "ROC-AUC" || metric.name === "F1-score"
                ? metric.value.toFixed(3)
                : percent(metric.value)}
            </strong>
            <small>Holdout test · {m.split.test} claims</small>
          </div>
        ))}
      </div>
      {m.dataset.startsWith("WELFake") ? (
        <ArticleEvaluation model={m} />
      ) : (
        <TrainingReview model={m} />
      )}
      <div className="model-detail-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>
              <Layers3 size={15} /> Dataset & experimental setup
            </h2>
          </div>
          <div className="panel-body">
            <dl className="detail-list">
              {[
                ["Dataset", m.dataset],
                ["Retained examples", m.dataset_size.toLocaleString()],
                [
                  "Train / validation / calibration / test",
                  `${m.split.train} / ${m.split.validation} / ${m.split.calibration ?? "—"} / ${m.split.test}`,
                ],
                [
                  "Credible / misleading labels",
                  `${m.class_distribution.credible} / ${m.class_distribution.misleading}`,
                ],
                [
                  "Exact / near duplicates removed",
                  `${m.duplicates_removed.exact} / ${m.duplicates_removed.near}`,
                ],
                ["Random seed", String(m.seed)],
                ["Selected regularization C", String(m.selected_C)],
                [
                  "Calibration",
                  m.calibrated
                    ? "Sigmoid / Platt scaling"
                    : "Uncalibrated probabilities",
                ],
              ].map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <div className="split-bar">
              {[
                { value: m.split.train, color: "#a68af9" },
                { value: m.split.validation, color: "#80b8e8" },
                { value: m.split.calibration ?? 0, color: "#e0b879" },
                { value: m.split.test, color: "#6bc7ab" },
              ].map((s, index) => (
                <span
                  key={index}
                  style={{
                    width: `${(s.value / m.dataset_size) * 100}%`,
                    background: s.color,
                  }}
                />
              ))}
            </div>
            <p className="text-[9px] leading-relaxed">{m.split_method}</p>
            <a
              className="section-link mt-4"
              href={m.dataset_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Original dataset distribution <ArrowUpRight size={12} />
            </a>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Confusion matrix</h2>
              <p>Rows: actual label · Columns: predicted label</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="flex justify-around text-[9px] text-[var(--muted)]">
              <span>Predicted credible</span>
              <span>Predicted misleading</span>
            </div>
            <div className="confusion-grid">
              {m.confusion_matrix.flatMap((row, r) =>
                row.map((value, c) => (
                  <div
                    className={`confusion-cell ${r === c ? "diagonal" : ""}`}
                    key={`${r}-${c}`}
                  >
                    <strong>{value}</strong>
                    <small>
                      Actual {r === 0 ? "credible" : "misleading"} →{" "}
                      {c === 0 ? "credible" : "misleading"}
                    </small>
                  </div>
                )),
              )}
            </div>
            <p className="text-[9px] leading-relaxed mt-5">
              Every cell is calculated from holdout predictions. Off-diagonal
              values are misclassifications. These labels reflect the selected
              dataset task.
            </p>
          </div>
        </section>
      </div>
      <section className="panel mb-6">
        <div className="panel-header">
          <h2>
            <FlaskConical size={15} /> What the labels mean
          </h2>
        </div>
        <div className="panel-body">
          <div className="concept-grid mt-0!">
            {[
              {
                name: "Credible class",
                labels: m.label_mapping.credible,
                description: m.dataset.startsWith("WELFake")
                  ? "Inherited article labels from the merged WELFake corpus."
                  : "PolitiFact labels grouped for this binary learning task.",
              },
              {
                name: "Misleading class",
                labels: m.label_mapping.misleading,
                description: m.dataset.startsWith("WELFake")
                  ? "Inherited article labels from the merged WELFake corpus."
                  : "PolitiFact labels grouped for this binary learning task.",
              },
            ].map((l) => (
              <div key={l.name}>
                <h3 className="text-[12px] mb-2">{l.name}</h3>
                <p className="text-[11px]">
                  {l.labels.join(" + ")}
                  <br />
                  {l.description}
                </p>
              </div>
            ))}
          </div>
          <div className="info-note mt-5 rounded-lg">
            <Info size={12} /> Excluded labels:{" "}
            {m.label_mapping.excluded.join(", ")}. Different datasets and split
            methods are not directly comparable. “Likely Credible” describes the
            model’s class, not an independent verification.
          </div>
        </div>
      </section>
      <section className="panel">
        <div className="panel-header">
          <h2>
            <CircleAlert size={15} /> Known limitations
          </h2>
        </div>
        <ul className="warning-list">
          {m.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
      <div className="transparency-note">
        <Info size={16} />
        <div>
          <p>
            <strong className="text-[var(--text)]">
              Dataset use & attribution
            </strong>
            <br />
            {m.license_note}
          </p>
        </div>
      </div>
    </>
  );
}

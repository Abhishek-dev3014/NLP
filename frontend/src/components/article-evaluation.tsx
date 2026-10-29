"use client";
import { FlaskConical, ShieldCheck, TriangleAlert } from "lucide-react";
import type { ModelMetrics } from "@/lib/types";
import { percent } from "@/lib/utils";
export function ArticleEvaluation({ model: m }: { model: ModelMetrics }) {
  const all90 =
    m.accuracy >= 0.9 && m.precision >= 0.9 && m.recall >= 0.9 && m.f1 >= 0.9;
  return (
    <>
      <section className="panel mb-6">
        <div className="panel-header">
          <div>
            <h2>
              <ShieldCheck size={17} /> Full-article benchmark
            </h2>
            <p>All test articles count, including uncertain predictions</p>
          </div>
          <span className="method-tag">
            {all90
              ? "90% target reached on this benchmark"
              : "Measured results"}
          </span>
        </div>
        <div className="panel-body">
          <p className="report-explanation">
            This classifier was trained for complete news articles. Its
            accuracy, precision, recall, and F1 above come from{" "}
            {m.split.test.toLocaleString()} held-out articles, with duplicate
            groups kept apart. These results measure agreement with dataset
            labels; they do not guarantee accuracy on every news website.
          </p>
          <div className="lab-concepts">
            <span>Train · {m.split.train.toLocaleString()}</span>
            <span>Validate · {m.split.validation.toLocaleString()}</span>
            <span>Calibrate · {m.split.calibration?.toLocaleString()}</span>
            <span>Test · {m.split.test.toLocaleString()}</span>
          </div>
          <p className="input-note">{m.evaluation_note}</p>
          {m.data_audit && (
            <p className="input-note">
              {m.data_audit.grouping}{" "}
              {m.data_audit.near_grouped_rows.toLocaleString()} related rows
              share a group with another article.
            </p>
          )}
        </div>
      </section>
      {m.domain_stress && (
        <section className="panel mb-6">
          <div className="panel-header">
            <h2>
              <TriangleAlert size={17} /> Does that accuracy transfer to other
              news?
            </h2>
          </div>
          <div className="panel-body">
            <p className="report-explanation">
              A separate test on {m.domain_stress.count} short political claims
              reached{" "}
              <strong>{percent(m.domain_stress.accuracy)} accuracy</strong>.
              That is a different task from full-article screening and
              demonstrates why the article benchmark score must not be
              advertised as universal fact-checking accuracy.
            </p>
            <p className="input-note">
              {m.domain_stress.note} Current Indian news has not yet been
              independently evaluated.
            </p>
          </div>
        </section>
      )}
      <section className="panel mb-6">
        <div className="panel-header">
          <h2>
            <FlaskConical size={17} /> How the article model was selected
          </h2>
        </div>
        <div className="panel-body">
          <p className="report-explanation">
            TF-IDF word and phrase features feed a linear SVM. Regularization is
            tuned on validation articles. A separate calibration set maps its
            decision scores to probabilities. No test labels are used to choose
            a model or adjust the threshold.
          </p>
          <div className="nlp-table-wrap">
            <table className="nlp-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Validation accuracy</th>
                  <th>Validation macro-F1</th>
                </tr>
              </thead>
              <tbody>
                {m.validation_search?.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td>{percent(c.accuracy)}</td>
                    <td>{c.macro_f1.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details className="nlp-details mt-4">
            <summary>Calibration, label audit & previous experiments</summary>
            <div className="panel-body">
              <p className="report-explanation">
                {m.calibration?.method}. Test Brier score:{" "}
                {m.brier_score?.toFixed(4)} (lower is better). Expected
                calibration error: {m.calibration?.ece.toFixed(4)}.
              </p>
              <p className="input-note">{m.data_audit?.label_audit}</p>
              <p className="input-note">
                Earlier LIAR experiments used short claims and reached 66.3%
                overall accuracy. Their scores are not directly comparable with
                this article benchmark. MiniLM semantic features were tested in
                that earlier experiment with frozen encoder weights. This
                release trains and tunes a supervised SVM; it does not claim
                transformer fine-tuning.
              </p>
              <div className="nlp-table-wrap">
                <table className="nlp-table">
                  <thead>
                    <tr>
                      <th>Predicted fake probability</th>
                      <th>Observed fake frequency</th>
                      <th>Articles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {m.calibration?.reliability_bins.map((b, i) => (
                      <tr key={i}>
                        <td>{percent(b.predicted)}</td>
                        <td>{percent(b.observed)}</td>
                        <td>{b.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </details>
        </div>
      </section>
    </>
  );
}

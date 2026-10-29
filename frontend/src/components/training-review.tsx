"use client";
import { FlaskConical, ShieldCheck } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ModelMetrics } from "@/lib/types";
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
export function TrainingReview({ model }: { model: ModelMetrics }) {
  const e = model.experiment;
  const policy = model.confidence_policy;
  return (
    <>
      {policy && (
        <section className="panel mb-6">
          <div className="panel-header">
            <div>
              <h2>
                <ShieldCheck size={17} />{" "}
                {policy.evaluation_scope === "confidence_only"
                  ? "Confidence threshold evaluation"
                  : "When the model gives a verdict"}
              </h2>
              <p>Accuracy and coverage must be read together</p>
            </div>
            <span className="method-tag">
              {policy.evaluation_scope === "confidence_only"
                ? "Before scope filtering"
                : "Active policy"}
            </span>
          </div>
          <div className="panel-body">
            <div className="policy-metrics">
              <div>
                <strong>
                  {policy.test_accuracy == null
                    ? "—"
                    : pct(policy.test_accuracy)}
                </strong>
                <span>Accuracy on accepted claims</span>
              </div>
              <div>
                <strong>{pct(policy.test_coverage)}</strong>
                <span>Share of test claims accepted</span>
              </div>
              <div>
                <strong>
                  {policy.test_count} / {model.split.test}
                </strong>
                <span>Claims receiving a class label</span>
              </div>
            </div>
            <p className="input-note">
              The confidence threshold is {pct(policy.threshold)}. Conditional
              accuracy 95% interval:{" "}
              {policy.test_accuracy_interval.map(pct).join("–")}.{" "}
              {policy.evaluation_scope === "confidence_only"
                ? "This experiment evaluates only the confidence threshold, before scope filtering."
                : "Scope checks and uncertainty cause the remaining claims to be withheld or marked for further verification."}
            </p>
            <p className="input-note">{policy.note}</p>
          </div>
        </section>
      )}
      {e && (
        <section className="panel mb-6">
          <div className="panel-header">
            <div>
              <h2>
                <FlaskConical size={17} /> Training experiment
              </h2>
              <p>
                Six candidates compared on validation; one challenger evaluated
                on test
              </p>
            </div>
            <span className="method-tag">Challenger not deployed</span>
          </div>
          <div className="panel-body">
            <p className="report-explanation">
              The validation winner used word and character features with
              sigmoid calibration. It did not improve overall test accuracy, so
              the original classifier remains active. MiniLM embeddings were
              also tested; their encoder weights were frozen, not fine-tuned.
            </p>
            <div className="nlp-table-wrap">
              <table className="nlp-table">
                <thead>
                  <tr>
                    <th>Retrospective test · {model.split.test} claims</th>
                    <th>Active model</th>
                    <th>Calibrated challenger</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Accuracy · higher is better</td>
                    <td>{pct(model.accuracy)}</td>
                    <td>{pct(e.accuracy)}</td>
                  </tr>
                  <tr>
                    <td>Misleading-class F1 · higher is better</td>
                    <td>{model.f1.toFixed(3)}</td>
                    <td>{e.f1.toFixed(3)}</td>
                  </tr>
                  <tr>
                    <td>ROC-AUC · higher is better</td>
                    <td>{model.roc_auc.toFixed(3)}</td>
                    <td>{e.roc_auc.toFixed(3)}</td>
                  </tr>
                  <tr>
                    <td>Brier score · lower is better</td>
                    <td>{model.brier_score?.toFixed(4) ?? "—"}</td>
                    <td>{e.brier_score?.toFixed(4)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="input-note">
              The historical test set was already reported for the original
              model. This comparison is retrospective, not a new unseen
              benchmark. Thresholds and candidate selection use validation data;
              test data does not tune them.
            </p>
            <details className="nlp-details mt-4">
              <summary>Inspect candidate selection & calibration</summary>
              <div className="nlp-table-wrap mt-4">
                <table className="nlp-table">
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Validation accuracy</th>
                      <th>Validation macro-F1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {e.validation_search?.map((c) => (
                      <tr key={c.name}>
                        <td>{c.name}</td>
                        <td>{pct(c.accuracy)}</td>
                        <td>{c.macro_f1.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {e.calibration && (
                <>
                  <h3 className="nlp-label mt-6">
                    Challenger reliability diagram
                  </h3>
                  <p className="input-note">
                    Predicted misleading-class probability versus observed label
                    frequency. Closer to the diagonal means better calibration;
                    this does not measure factual truth. {e.calibration.method}.
                  </p>
                  <div
                    style={{ height: 260 }}
                    role="img"
                    aria-label="Challenger reliability chart; numeric bin data follows"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={e.calibration.reliability_bins}
                        margin={{ top: 15, right: 20, bottom: 25, left: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="var(--border)"
                        />
                        <XAxis
                          dataKey="predicted"
                          type="number"
                          domain={[0, 1]}
                          tickFormatter={(v) => `${Math.round(v * 100)}%`}
                          label={{
                            value: "Predicted probability",
                            position: "insideBottom",
                            offset: -18,
                          }}
                        />
                        <YAxis
                          domain={[0, 1]}
                          tickFormatter={(v) => `${Math.round(v * 100)}%`}
                        />
                        <Tooltip
                          formatter={(v) =>
                            typeof v === "number" ? pct(v) : v
                          }
                        />
                        <ReferenceLine
                          segment={[
                            { x: 0, y: 0 },
                            { x: 1, y: 1 },
                          ]}
                          stroke="var(--muted)"
                          strokeDasharray="4 4"
                        />
                        <Line
                          dataKey="observed"
                          name="Observed frequency"
                          stroke="var(--accent)"
                          strokeWidth={3}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="nlp-table-wrap">
                    <table className="nlp-table">
                      <thead>
                        <tr>
                          <th>Mean prediction</th>
                          <th>Observed frequency</th>
                          <th>Claims</th>
                        </tr>
                      </thead>
                      <tbody>
                        {e.calibration.reliability_bins.map((b, i) => (
                          <tr key={i}>
                            <td>{pct(b.predicted)}</td>
                            <td>{pct(b.observed)}</td>
                            <td>{b.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </details>
          </div>
        </section>
      )}
    </>
  );
}

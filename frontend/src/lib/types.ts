export type Assessment =
  | "Likely Credible"
  | "Potentially Misleading"
  | "Needs Further Verification"
  | "Insufficient Evidence";
export interface Feature {
  term: string;
  contribution: number;
  direction: "misleading" | "credible";
}
export interface Prediction {
  label: Assessment;
  confidence: number | null;
  probabilities: { credible: number; misleading: number } | null;
  model_name: string;
  model_version: string;
  calibrated: boolean;
  in_domain: boolean;
  features: Feature[];
  warnings: string[];
  vocabulary_coverage: number | null;
  assessment_scope?: string | null;
  factual_status?: string | null;
  evaluated_domain?: string | null;
  analyzed_words?: number | null;
  confidence_threshold?: number | null;
  decision_reason?: string | null;
  attribution_method?: string | null;
  score_breakdown?: Record<string, number> | null;
}
export interface Insights {
  word_count: number;
  character_count: number;
  sentence_count: number;
  average_sentence_length: number;
  sentiment_score: number;
  subjectivity_score: number | null;
  clickbait_indicator: number;
  emotional_indicator: number;
  certainty_indicator: number;
  method: string;
}
export interface Highlight {
  start: number;
  end: number;
  text: string;
  kind: string;
  reason: string;
}
export interface Claim {
  text: string;
  start: number;
  end: number;
  reason: string;
  status: string;
}
export interface Evidence {
  source_name: string;
  title: string;
  url: string;
  publication_date: string | null;
  summary: string;
  status: string;
}
export interface Analysis {
  id: string;
  headline: string;
  text: string;
  input_type: string;
  source_url: string | null;
  created_at: string;
  prediction: Prediction;
  insights: Insights;
  highlights: Highlight[];
  claims: Claim[];
  evidence: { status: string; message: string; items: Evidence[] };
  explanation: string;
  recommendations: string[];
  nlp?: NLPAnalysis | null;
}
export interface ArticleInput {
  headline?: string;
  text: string;
  input_type?: "text" | "url" | "file";
  source_url?: string | null;
  allow_external_evidence?: boolean;
}
export interface AnalysisList {
  items: Analysis[];
  total: number;
  page: number;
  page_size: number;
}
export interface DashboardStats {
  total: number;
  distribution: { name: string; value: number }[];
  activity: { date: string; count: number; confidence: number | null }[];
  indicators: { name: string; value: number }[];
  recent: Analysis[];
}
export interface ModelMetrics {
  available: boolean;
  experiment?: ModelMetrics | null;
  macro_f1?: number;
  brier_score?: number;
  encoder?: { name: string; fine_tuned_here: boolean } | null;
  validation_search?: {
    name: string;
    macro_f1: number;
    accuracy: number;
    roc_auc: number;
  }[];
  confidence_policy?: {
    evaluation_scope?: "confidence_only" | "scope_and_confidence";
    threshold: number;
    test_count: number;
    test_coverage: number;
    test_accuracy: number | null;
    test_accuracy_interval: [number, number];
    note: string;
  };
  calibration?: {
    method: string;
    brier_before: number;
    brier_after: number;
    ece: number;
    reliability_bins: { count: number; predicted: number; observed: number }[];
  };
  message?: string;
  model_name: string;
  version: string;
  dataset: string;
  dataset_url: string;
  dataset_size: number;
  class_distribution: { credible: number; misleading: number };
  split: {
    train: number;
    validation: number;
    calibration?: number;
    test: number;
  };
  evaluation_note?: string;
  data_audit?: {
    grouping: string;
    near_grouped_rows: number;
    label_audit: string;
  };
  domain_stress?: { count: number; accuracy: number; note: string };
  split_method: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  confusion_matrix: number[][];
  calibrated: boolean;
  limitations: string[];
  evaluated_at: string;
  license_note: string;
  label_mapping: {
    credible: string[];
    misleading: string[];
    excluded: string[];
  };
  duplicates_removed: { exact: number; near: number };
  selected_C: number;
  seed: number;
}

export interface NLPAnalysis {
  available: boolean;
  message?: string;
  pipeline?: string;
  method?: string;
  summary_scope?: string;
  summary?: { text: string; start: number; end: number }[];
  entities?: { text: string; label: string; start: number; end: number }[];
  topics?: { term: string; count: number }[];
  tokens?: {
    text: string;
    lemma: string;
    pos: string;
    morphology: string;
    start: number;
    end: number;
  }[];
  token_count?: number;
  dependencies?: {
    text: string;
    relation: string;
    head: string;
    start: number;
    head_start: number;
  }[];
  dependency_sentence?: string;
}

from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.ml.preprocessing import clean_text, tokens


class TextInput(BaseModel):
    headline: str = Field(default="", max_length=300)
    text: str = Field(min_length=40, max_length=60000)
    input_type: Literal["text", "url", "file"] = "text"
    source_url: str | None = Field(default=None, max_length=2000)
    allow_external_evidence: bool = False

    @field_validator("source_url")
    @classmethod
    def valid_source_url(cls, value):
        if value is not None:
            from urllib.parse import urlsplit

            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "Source URL must be a public HTTP(S) URL without credentials."
                )
        return value

    @field_validator("text")
    @classmethod
    def valid_text(cls, text: str) -> str:
        text = clean_text(text)
        if len(tokens(text)) < 12:
            raise ValueError(
                "Please provide at least 12 words for meaningful language analysis."
            )
        return text


class URLInput(BaseModel):
    url: str = Field(min_length=10, max_length=2000)
    allow_external_evidence: bool = False


class Feature(BaseModel):
    term: str
    contribution: float
    direction: str


class Prediction(BaseModel):
    label: str
    confidence: float | None
    probabilities: dict[str, float] | None
    model_name: str
    model_version: str
    calibrated: bool
    in_domain: bool
    features: list[Feature]
    warnings: list[str]
    assessment_scope: str | None = None
    factual_status: str | None = None
    evaluated_domain: str | None = None
    analyzed_words: int | None = None
    vocabulary_coverage: float | None = None
    confidence_threshold: float | None = None
    decision_reason: str | None = None
    attribution_method: str | None = None
    score_breakdown: dict[str, float] | None = None


class Insights(BaseModel):
    word_count: int
    character_count: int
    sentence_count: int
    average_sentence_length: float
    sentiment_score: float
    subjectivity_score: float | None
    clickbait_indicator: int
    emotional_indicator: int
    certainty_indicator: int
    method: str


class Highlight(BaseModel):
    start: int
    end: int
    text: str
    kind: str
    reason: str


class Claim(BaseModel):
    text: str
    start: int
    end: int
    reason: str
    status: str


class Evidence(BaseModel):
    source_name: str
    title: str
    url: str
    publication_date: str | None
    summary: str
    status: str


class EvidenceResult(BaseModel):
    status: str
    message: str
    items: list[Evidence]


class AnalysisReport(BaseModel):
    id: str
    headline: str
    text: str
    input_type: str
    source_url: str | None
    created_at: str
    prediction: Prediction
    insights: Insights
    highlights: list[Highlight]
    claims: list[Claim]
    evidence: EvidenceResult
    explanation: str
    recommendations: list[str]
    nlp: dict | None = None


class AnalysisList(BaseModel):
    items: list[AnalysisReport]
    total: int
    page: int
    page_size: int

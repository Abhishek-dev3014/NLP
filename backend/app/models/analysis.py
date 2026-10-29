from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Float, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    headline: Mapped[str] = mapped_column(String(300))
    article_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    input_type: Mapped[str] = mapped_column(String(16))
    predicted_label: Mapped[str] = mapped_column(String(40))
    prediction_confidence: Mapped[float | None] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    report: Mapped[dict] = mapped_column(JSON)
    insights: Mapped["AnalysisInsight"] = relationship(cascade="all, delete-orphan")
    claims: Mapped[list["ExtractedClaim"]] = relationship(cascade="all, delete-orphan")
    __table_args__ = (Index("ix_analyses_session_date", "session_id", "created_at"),)


class AnalysisInsight(Base):
    __tablename__ = "analysis_insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), unique=True
    )
    sentiment_score: Mapped[float] = mapped_column(Float)
    subjectivity_score: Mapped[float | None] = mapped_column(Float)
    word_count: Mapped[int]
    sentence_count: Mapped[int]
    clickbait_indicator: Mapped[int]
    explanation: Mapped[dict] = mapped_column(JSON)


class ExtractedClaim(Base):
    __tablename__ = "extracted_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE")
    )
    claim_text: Mapped[str] = mapped_column(Text)
    claim_position: Mapped[int]
    verification_status: Mapped[str] = mapped_column(String(50))
    evidence: Mapped[list["EvidenceSource"]] = relationship(
        cascade="all, delete-orphan"
    )


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("extracted_claims.id", ondelete="CASCADE")
    )
    source_title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(200))
    publication_date: Mapped[str | None] = mapped_column(String(100))
    evidence_status: Mapped[str] = mapped_column(String(100))
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

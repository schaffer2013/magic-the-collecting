from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    machine_validated = "machine_validated"
    human_review_required = "human_review_required"
    human_validated = "human_validated"
    rejected = "rejected"


class ValidationSource(str, enum.Enum):
    machine = "machine"
    human = "human"


class VerificationState(str, enum.Enum):
    unverified = "unverified"
    verified = "verified"


class Collection(Base):
    __tablename__ = "collections"

    collection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    cards: Mapped[list["CollectionCard"]] = relationship(back_populates="collection")


class RegistrationJob(Base):
    __tablename__ = "registration_jobs"
    __table_args__ = (
        UniqueConstraint("sorter_run_id", "sorter_card_seq", name="uq_sorter_card_event"),
    )

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sorter_run_id: Mapped[str] = mapped_column(String(120), nullable=False)
    sorter_card_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.collection_id"), nullable=False)
    raw_image_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_pile: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_pile: Mapped[str] = mapped_column(String(120), nullable=False)
    sorter_expected_scryfall_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sorter_recognition_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_recognition_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    collection_cards: Mapped[list["CollectionCard"]] = relationship(back_populates="job")


class CollectionCard(Base):
    __tablename__ = "collection_cards"

    collection_card_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.collection_id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("registration_jobs.job_id"), nullable=True)
    verification_state: Mapped[VerificationState] = mapped_column(
        Enum(VerificationState),
        default=VerificationState.unverified,
        nullable=False,
    )
    raw_image_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scryfall_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    set_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    collector_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    foil: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    language: Mapped[str | None] = mapped_column(String(30), nullable=True)
    validation_source: Mapped[ValidationSource | None] = mapped_column(Enum(ValidationSource), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="cards")
    job: Mapped[RegistrationJob | None] = relationship(back_populates="collection_cards")

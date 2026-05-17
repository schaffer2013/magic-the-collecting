from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CardState(str, enum.Enum):
    unprocessed = "unprocessed"
    machine_recognized = "machine_recognized"
    human_verified = "human_verified"


class ValidationSource(str, enum.Enum):
    human = "human"


class Finish(str, enum.Enum):
    nonfoil = "nonfoil"
    foil = "foil"
    etched = "etched"
    glossy = "glossy"


class ReviewDecisionKind(str, enum.Enum):
    exactly_correct = "exactly_correct"
    right_card_wrong_printing = "right_card_wrong_printing"
    wrong_card = "wrong_card"
    unreadable = "unreadable"


class Collection(Base):
    __tablename__ = "collections"

    collection_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    cards: Mapped[list["CollectionCard"]] = relationship(back_populates="collection")
    unverified_cards: Mapped[list["UnverifiedCard"]] = relationship(back_populates="collection")


class DuplicateImageHash(Base):
    __tablename__ = "duplicate_image_hashes"
    __table_args__ = (UniqueConstraint("collection_id", "image_hash", name="uq_collection_image_hash"),)

    duplicate_image_hash_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.collection_id"), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UnverifiedCard(Base):
    __tablename__ = "unverified_cards"

    unverified_card_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.collection_id"), nullable=False)
    card_state: Mapped[CardState] = mapped_column(
        Enum(CardState), default=CardState.unprocessed, nullable=False
    )
    raw_image_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    overlay_image_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recognition_image_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_image_media_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bounding_box: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_scryfall_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    machine_candidate_scryfall_ids: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    machine_confidence: Mapped[float | None] = mapped_column(nullable=True)
    machine_debug_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    machine_review_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    machine_recognized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inducted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="unverified_cards")
    collection_card: Mapped["CollectionCard | None"] = relationship(back_populates="source_unverified_card")


class CollectionCard(Base):
    __tablename__ = "collection_cards"

    collection_card_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.collection_id"), nullable=False)
    source_unverified_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("unverified_cards.unverified_card_id"), unique=True, nullable=True
    )
    scryfall_id: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    set_code: Mapped[str] = mapped_column(String(30), nullable=False)
    collector_number: Mapped[str] = mapped_column(String(50), nullable=False)
    finish: Mapped[Finish] = mapped_column(Enum(Finish), nullable=False)
    validation_source: Mapped[ValidationSource] = mapped_column(Enum(ValidationSource), nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="cards")
    source_unverified_card: Mapped[UnverifiedCard | None] = relationship(back_populates="collection_card")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    review_decision_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    unverified_card_id: Mapped[str] = mapped_column(
        ForeignKey("unverified_cards.unverified_card_id"), nullable=False
    )
    decision_kind: Mapped[ReviewDecisionKind] = mapped_column(Enum(ReviewDecisionKind), nullable=False)
    final_scryfall_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

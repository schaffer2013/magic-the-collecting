from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .catalog import get_card_metadata
from .config import settings
from .models import CardState, CollectionCard, DuplicateImageHash, Finish, UnverifiedCard, ValidationSource, utcnow


def raw_image_url(card: UnverifiedCard) -> str:
    return f"/unverified-cards/{card.unverified_card_id}/raw-image"


def candidate_ids(card: UnverifiedCard) -> list[str]:
    return json.loads(card.machine_candidate_scryfall_ids or "[]")


def create_unverified_card(
    db: Session,
    *,
    collection_id: str,
    image_bytes: bytes,
    suffix: str,
    media_type: str | None,
    expected_scryfall_id: str | None,
) -> UnverifiedCard:
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cutoff = utcnow() - timedelta(seconds=settings.duplicate_hash_ttl_seconds)
    db.execute(delete(DuplicateImageHash).where(DuplicateImageHash.created_at < cutoff))
    existing = db.scalar(
        select(DuplicateImageHash).where(
            DuplicateImageHash.collection_id == collection_id,
            DuplicateImageHash.image_hash == image_hash,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="duplicate image recently submitted to this collection")

    settings.raw_image_dir.mkdir(parents=True, exist_ok=True)
    path = settings.raw_image_dir / f"{uuid4()}{suffix or '.bin'}"
    path.write_bytes(image_bytes)
    card = UnverifiedCard(
        collection_id=collection_id,
        raw_image_uri=str(path),
        raw_image_media_type=media_type,
        expected_scryfall_id=expected_scryfall_id,
    )
    db.add(DuplicateImageHash(collection_id=collection_id, image_hash=image_hash))
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def process_next_unprocessed_card(db: Session) -> UnverifiedCard | None:
    card = db.scalar(
        select(UnverifiedCard)
        .where(UnverifiedCard.card_state == CardState.unprocessed)
        .order_by(UnverifiedCard.inducted_at)
        .limit(1)
    )
    if card is None:
        return None
    card.card_state = CardState.machine_recognized
    candidates = [card.expected_scryfall_id] if card.expected_scryfall_id else []
    card.machine_candidate_scryfall_ids = json.dumps(candidates)
    card.machine_recognized_at = utcnow()
    db.commit()
    db.refresh(card)
    return card


def verify_unverified_card(db: Session, card: UnverifiedCard, *, scryfall_id: str, finish: Finish) -> CollectionCard:
    if card.card_state == CardState.human_verified and card.collection_card is not None:
        raise HTTPException(status_code=409, detail="unverified card already verified")
    metadata = get_card_metadata(scryfall_id)
    card.card_state = CardState.human_verified
    card.verified_at = utcnow()
    collection_card = CollectionCard(
        collection_id=card.collection_id,
        source_unverified_card_id=card.unverified_card_id,
        scryfall_id=metadata.scryfall_id,
        name=metadata.name,
        set_code=metadata.set_code,
        collector_number=metadata.collector_number,
        finish=finish,
        validation_source=ValidationSource.human,
        validated_at=utcnow(),
    )
    db.add(collection_card)
    db.commit()
    db.refresh(collection_card)
    return collection_card

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .models import CardState, DuplicateImageHash, UnverifiedCard, utcnow


def cleanup_duplicate_hashes(db: Session) -> int:
    cutoff = utcnow() - timedelta(seconds=settings.duplicate_hash_ttl_seconds)
    result = db.execute(delete(DuplicateImageHash).where(DuplicateImageHash.created_at < cutoff))
    db.commit()
    return result.rowcount or 0


def cleanup_verified_raw_images(db: Session) -> int:
    cutoff = utcnow() - timedelta(hours=settings.raw_image_min_retention_hours)
    cards = db.scalars(
        select(UnverifiedCard).where(
            UnverifiedCard.card_state == CardState.human_verified,
            UnverifiedCard.verified_at.is_not(None),
            UnverifiedCard.verified_at < cutoff,
        )
    ).all()
    deleted = 0
    for card in cards:
        path = Path(card.raw_image_uri)
        if path.exists():
            path.unlink()
            deleted += 1
    return deleted

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardMetadata:
    scryfall_id: str
    name: str
    set_code: str
    collector_number: str


def get_card_metadata(scryfall_id: str) -> CardMetadata:
    # Recognition/card-catalog integration is intentionally replaceable.
    # Until the Scryfall-backed catalog arrives, preserve the verified ID and
    # supply stable placeholders so downstream collection records remain valid.
    return CardMetadata(
        scryfall_id=scryfall_id,
        name=f"Scryfall card {scryfall_id}",
        set_code="unknown",
        collector_number="unknown",
    )

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import scrython


@dataclass(frozen=True)
class CardMetadata:
    scryfall_id: str
    name: str
    set_code: str
    collector_number: str
    image_uri: str | None = None
    lang: str | None = None


@lru_cache(maxsize=2048)
def get_card_metadata(scryfall_id: str) -> CardMetadata:
    card = scrython.cards.ById(id=scryfall_id)
    image_uris = getattr(card, "image_uris", None)
    image_uri = image_uris.get("normal") if isinstance(image_uris, dict) else None
    return CardMetadata(
        scryfall_id=card.card_id,
        name=card.name,
        set_code=card.set,
        collector_number=card.collector_number,
        image_uri=image_uri,
        lang=card.lang,
    )


def search_cards(query: str, limit: int = 10) -> list[CardMetadata]:
    result = scrython.cards.Search(q=query, unique="prints")
    cards = []
    for payload in result.data[:limit]:
        image_uris = payload.image_uris if hasattr(payload, "image_uris") else None
        cards.append(
            CardMetadata(
                scryfall_id=payload.card_id,
                name=payload.name,
                set_code=payload.set,
                collector_number=payload.collector_number,
                image_uri=image_uris.get("normal") if isinstance(image_uris, dict) else None,
                lang=payload.lang,
            )
        )
    return cards

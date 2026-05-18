from __future__ import annotations

import time
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
    time.sleep(0.1)  # Scryfall rate limit
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


def search_cards(
    query: str,
    *,
    set_code: str | None = None,
    collector_number: str | None = None,
    lang: str | None = None,
    limit: int = 25,
) -> list[CardMetadata]:
    filters = [query]
    if set_code:
        filters.append(f"set:{set_code}")
    if collector_number:
        filters.append(f"cn:{collector_number}")
    if lang:
        filters.append(f"lang:{lang}")
    time.sleep(0.1)  # Scryfall rate limit
    result = scrython.cards.Search(q=" ".join(filters), unique="prints")
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


@lru_cache(maxsize=512)
def autocomplete_card_names(query: str) -> list[str]:
    time.sleep(0.1)  # Scryfall rate limit
    result = scrython.cards.Autocomplete(q=query)
    return list(result.data[:20])

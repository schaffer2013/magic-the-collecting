from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from .catalog import get_card_metadata
from .models import CollectionCard

MOXFIELD_DECK_API = "https://api2.moxfield.com/v3/decks/all/{deck_id}"
MOXFIELD_USER_AGENT = "MTG-Collection/0.2 (+local collection comparison)"
BOARD_FIELDS = ("commanders", "companions", "mainboard", "sideboard", "maybeboard")


class MoxfieldError(RuntimeError):
    pass


@dataclass(frozen=True)
class MoxfieldDeckCard:
    name: str
    quantity: int
    oracle_id: str | None
    scryfall_id: str | None
    board: str


@dataclass(frozen=True)
class MoxfieldDeck:
    deck_id: str
    name: str | None
    cards: list[MoxfieldDeckCard]


@dataclass(frozen=True)
class DeckCardAvailability:
    name: str
    oracle_id: str
    requested_quantity: int
    owned_quantity: int
    missing_quantity: int


@dataclass(frozen=True)
class DeckAvailability:
    collection_id: str
    deck_url: str
    deck_id: str
    deck_name: str | None
    requested_card_count: int
    owned_card_count: int
    missing_card_count: int
    cards: list[DeckCardAvailability]


def parse_moxfield_deck_id(deck_url: str) -> str:
    candidate = deck_url.strip()
    if not candidate:
        raise ValueError("deck_url is required")
    parsed = urlparse(candidate)
    if not parsed.scheme and "/" not in candidate:
        return candidate
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "decks":
        return parts[1]
    raise ValueError("deck_url must be a Moxfield deck URL")


def fetch_moxfield_deck(deck_url: str) -> MoxfieldDeck:
    deck_id = parse_moxfield_deck_id(deck_url)
    request = Request(
        MOXFIELD_DECK_API.format(deck_id=deck_id),
        headers={
            "Accept": "application/json",
            "User-Agent": MOXFIELD_USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise MoxfieldError("Moxfield deck not found") from exc
        raise MoxfieldError(f"Moxfield returned HTTP {exc.code}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise MoxfieldError("Moxfield deck could not be fetched") from exc
    return parse_moxfield_deck_payload(deck_id, payload)


def parse_moxfield_deck_payload(deck_id: str, payload: dict) -> MoxfieldDeck:
    cards: list[MoxfieldDeckCard] = []
    boards_payload = payload.get("boards")
    if isinstance(boards_payload, dict):
        for board, board_payload in boards_payload.items():
            if not isinstance(board_payload, dict):
                continue
            for entry in _iter_board_entries(board_payload.get("cards")):
                parsed = _parse_deck_card_entry(entry, str(board))
                if parsed is not None:
                    cards.append(parsed)
    for board in BOARD_FIELDS:
        for entry in _iter_board_entries(payload.get(board)):
            parsed = _parse_deck_card_entry(entry, board)
            if parsed is not None:
                cards.append(parsed)
    return MoxfieldDeck(deck_id=deck_id, name=payload.get("name"), cards=cards)


def compare_collection_to_moxfield_deck(db: Session, collection_id: str, deck_url: str) -> DeckAvailability:
    deck = fetch_moxfield_deck(deck_url)
    requested_by_oracle: dict[str, DeckCardAvailability] = {}
    for card in deck.cards:
        oracle_id = card.oracle_id or _oracle_id_for_scryfall_id(card.scryfall_id)
        if oracle_id is None:
            continue
        existing = requested_by_oracle.get(oracle_id)
        if existing is None:
            requested_by_oracle[oracle_id] = DeckCardAvailability(
                name=card.name,
                oracle_id=oracle_id,
                requested_quantity=card.quantity,
                owned_quantity=0,
                missing_quantity=card.quantity,
            )
        else:
            requested_by_oracle[oracle_id] = DeckCardAvailability(
                name=existing.name,
                oracle_id=oracle_id,
                requested_quantity=existing.requested_quantity + card.quantity,
                owned_quantity=0,
                missing_quantity=existing.requested_quantity + card.quantity,
            )

    owned_by_oracle: dict[str, int] = {}
    owned_cards = db.scalars(select(CollectionCard).where(CollectionCard.collection_id == collection_id)).all()
    for owned in owned_cards:
        oracle_id = _oracle_id_for_scryfall_id(owned.scryfall_id)
        if oracle_id is not None:
            owned_by_oracle[oracle_id] = owned_by_oracle.get(oracle_id, 0) + 1

    cards = []
    for requested in requested_by_oracle.values():
        owned_quantity = owned_by_oracle.get(requested.oracle_id, 0)
        cards.append(
            DeckCardAvailability(
                name=requested.name,
                oracle_id=requested.oracle_id,
                requested_quantity=requested.requested_quantity,
                owned_quantity=owned_quantity,
                missing_quantity=max(0, requested.requested_quantity - owned_quantity),
            )
        )
    cards.sort(key=lambda item: (item.missing_quantity == 0, item.name.casefold()))
    return DeckAvailability(
        collection_id=collection_id,
        deck_url=deck_url,
        deck_id=deck.deck_id,
        deck_name=deck.name,
        requested_card_count=sum(card.requested_quantity for card in cards),
        owned_card_count=sum(min(card.owned_quantity, card.requested_quantity) for card in cards),
        missing_card_count=sum(card.missing_quantity for card in cards),
        cards=cards,
    )


def _parse_deck_card_entry(entry: dict, board: str) -> MoxfieldDeckCard | None:
    card_payload = entry.get("card") if isinstance(entry.get("card"), dict) else entry
    quantity = _coerce_quantity(entry.get("quantity", card_payload.get("quantity", 1)))
    oracle_id = _first_string(card_payload, ("oracle_id", "oracleId"))
    scryfall_id = _first_string(card_payload, ("scryfall_id", "scryfallId", "id"))
    name = _first_string(card_payload, ("name", "cardName")) or _first_string(entry, ("name", "cardName"))
    if name is None or quantity <= 0:
        return None
    return MoxfieldDeckCard(
        name=name,
        quantity=quantity,
        oracle_id=oracle_id,
        scryfall_id=scryfall_id,
        board=board,
    )


def _coerce_quantity(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def _iter_board_entries(board_payload: object):
    if isinstance(board_payload, dict):
        yield from (entry for entry in board_payload.values() if isinstance(entry, dict))
    elif isinstance(board_payload, list):
        yield from (entry for entry in board_payload if isinstance(entry, dict))


def _first_string(payload: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _oracle_id_for_scryfall_id(scryfall_id: str | None) -> str | None:
    if not scryfall_id:
        return None
    metadata = get_card_metadata(scryfall_id)
    return metadata.oracle_id or metadata.scryfall_id

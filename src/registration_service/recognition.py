from __future__ import annotations

from functools import lru_cache

from card_engine.adapters.sortingmachine import SortingMachineRecognizer
from card_engine.config import EngineConfig
from card_engine.operational_modes import ExpectedCard

from .config import settings
from .models import UnverifiedCard


@lru_cache(maxsize=1)
def get_recognizer() -> SortingMachineRecognizer:
    config = EngineConfig(
        catalog_path=str(settings.fuzzy_enigma_catalog_path),
        candidate_count=5,
        recognition_deadline_seconds=20.0,
    )
    recognizer = SortingMachineRecognizer(config=config, auto_track_results=False)
    recognizer.warm_up()
    return recognizer


def recognize_unverified_card(card: UnverifiedCard):
    expected = (
        ExpectedCard(scryfall_id=card.expected_scryfall_id, name="")
        if card.expected_scryfall_id
        else None
    )
    return get_recognizer().recognize_top_card(
        card.recognition_image_uri,
        mode="reevaluation" if expected else "greenfield",
        expected_card=expected,
        detailed=True,
    )

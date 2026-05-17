from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import CardState, Finish, ValidationSource


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_id: str
    name: str
    description: str | None
    created_at: datetime


class CollectionSummaryRead(BaseModel):
    collection_id: str
    unprocessed_count: int
    machine_recognized_count: int
    human_verified_unverified_count: int
    trusted_collection_card_count: int


class UnverifiedCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unverified_card_id: str
    collection_id: str
    card_state: CardState
    raw_image_url: str
    expected_scryfall_id: str | None
    machine_candidate_scryfall_ids: list[str]
    inducted_at: datetime


class ReviewCardRead(UnverifiedCardRead):
    pass


class HumanVerificationCreate(BaseModel):
    final_scryfall_id: str
    finish: Finish


class CollectionCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_card_id: str
    collection_id: str
    source_unverified_card_id: str | None
    scryfall_id: str
    name: str
    set_code: str
    collector_number: str
    finish: Finish
    validation_source: ValidationSource
    validated_at: datetime


class TransferCreate(BaseModel):
    target_collection_id: str


class BatchTransferCreate(TransferCreate):
    collection_card_ids: list[str]


class TransferFailure(BaseModel):
    collection_card_id: str
    reason: str

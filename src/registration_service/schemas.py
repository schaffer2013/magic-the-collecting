from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import CardState, JobStatus, ValidationSource


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_id: int
    name: str
    description: str | None
    created_at: datetime


class RegistrationJobCreate(BaseModel):
    sorter_run_id: str
    sorter_card_seq: int
    collection_id: int
    captured_at: datetime
    source_pile: str
    destination_pile: str
    sorter_expected_scryfall_id: str | None = None
    sorter_recognition_payload: str | None = None


class RegistrationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    sorter_run_id: str
    sorter_card_seq: int
    collection_id: int
    raw_image_uri: str
    captured_at: datetime
    source_pile: str
    destination_pile: str
    sorter_expected_scryfall_id: str | None
    sorter_recognition_payload: str | None
    service_recognition_payload: str | None
    status: JobStatus
    created_at: datetime
    updated_at: datetime


class CollectionCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_card_id: int
    collection_id: int
    source_unverified_card_id: int | None
    job_id: int | None
    scryfall_id: str
    name: str
    set_code: str
    collector_number: str
    foil: bool | None
    language: str | None
    validation_source: ValidationSource
    validated_at: datetime


class UnverifiedCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unverified_card_id: int
    collection_id: int
    job_id: int | None
    card_state: CardState
    raw_image_uri: str | None
    expected_scryfall_id: str | None
    machine_candidate_scryfall_ids: str | None
    created_at: datetime


class ReviewCardRead(BaseModel):
    unverified_card_id: int
    collection_id: int
    job_id: int | None
    card_state: CardState
    raw_image_url: str
    expected_scryfall_id: str | None
    machine_candidate_scryfall_ids: list[str]


class HumanVerificationCreate(BaseModel):
    final_scryfall_id: str
    name: str
    set_code: str
    collector_number: str
    foil: bool | None = None
    language: str | None = None

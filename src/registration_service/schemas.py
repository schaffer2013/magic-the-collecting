from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import JobStatus, ValidationSource, VerificationState


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
    job_id: int | None
    verification_state: VerificationState
    raw_image_uri: str | None
    scryfall_id: str | None
    name: str | None
    set_code: str | None
    collector_number: str | None
    foil: bool | None
    language: str | None
    validation_source: ValidationSource | None
    validated_at: datetime | None

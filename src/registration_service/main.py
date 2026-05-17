from __future__ import annotations

import csv
import io
import json
import random
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import CardState, Collection, CollectionCard, RegistrationJob, UnverifiedCard, ValidationSource
from .schemas import (
    CollectionCardRead,
    CollectionCreate,
    CollectionRead,
    HumanVerificationCreate,
    RegistrationJobCreate,
    RegistrationJobRead,
    ReviewCardRead,
    UnverifiedCardRead,
)

RAW_IMAGE_DIR = Path("data/raw-images")

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="MTG Registration Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/collections", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)) -> Collection:
    collection = Collection(name=payload.name, description=payload.description)
    db.add(collection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="collection name already exists") from exc
    db.refresh(collection)
    return collection


@app.get("/collections", response_model=list[CollectionRead])
def list_collections(db: Session = Depends(get_db)) -> list[Collection]:
    return list(db.scalars(select(Collection).order_by(Collection.collection_id)))


@app.post("/registration-jobs", response_model=RegistrationJobRead, status_code=status.HTTP_201_CREATED)
async def create_registration_job(
    response: Response,
    sorter_run_id: str = Form(...),
    sorter_card_seq: int = Form(...),
    collection_id: int = Form(...),
    captured_at: str = Form(...),
    source_pile: str = Form(...),
    destination_pile: str = Form(...),
    sorter_expected_scryfall_id: str | None = Form(None),
    sorter_recognition_payload: str | None = Form(None),
    raw_image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RegistrationJob:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")

    payload = RegistrationJobCreate(
        sorter_run_id=sorter_run_id,
        sorter_card_seq=sorter_card_seq,
        collection_id=collection_id,
        captured_at=captured_at,
        source_pile=source_pile,
        destination_pile=destination_pile,
        sorter_expected_scryfall_id=sorter_expected_scryfall_id,
        sorter_recognition_payload=sorter_recognition_payload,
    )

    existing = db.scalar(
        select(RegistrationJob).where(
            RegistrationJob.sorter_run_id == payload.sorter_run_id,
            RegistrationJob.sorter_card_seq == payload.sorter_card_seq,
        )
    )
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    RAW_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(raw_image.filename or "").suffix or ".bin"
    raw_image_path = RAW_IMAGE_DIR / f"{uuid4()}{suffix}"
    raw_image_path.write_bytes(await raw_image.read())

    job = RegistrationJob(raw_image_uri=str(raw_image_path), **payload.model_dump())
    db.add(job)
    db.flush()
    db.add(
        UnverifiedCard(
            collection_id=collection_id,
            job_id=job.job_id,
            raw_image_uri=str(raw_image_path),
            expected_scryfall_id=sorter_expected_scryfall_id,
        )
    )
    db.commit()
    db.refresh(job)
    return job


@app.get("/registration-jobs/{job_id}", response_model=RegistrationJobRead)
def get_registration_job(job_id: int, db: Session = Depends(get_db)) -> RegistrationJob:
    job = db.get(RegistrationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="registration job not found")
    return job


@app.get("/collections/{collection_id}/cards", response_model=list[CollectionCardRead])
def list_collection_cards(
    collection_id: int,
    db: Session = Depends(get_db),
) -> list[CollectionCard]:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    query = select(CollectionCard).where(CollectionCard.collection_id == collection_id)
    return list(db.scalars(query.order_by(CollectionCard.collection_card_id)))


@app.get("/collections/{collection_id}/unverified-cards", response_model=list[UnverifiedCardRead])
def list_unverified_cards(
    collection_id: int,
    card_state: CardState | None = Query(None),
    db: Session = Depends(get_db),
) -> list[UnverifiedCard]:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    query = select(UnverifiedCard).where(UnverifiedCard.collection_id == collection_id)
    if card_state is not None:
        query = query.where(UnverifiedCard.card_state == card_state)
    return list(db.scalars(query.order_by(UnverifiedCard.unverified_card_id)))


@app.get("/review-cards/next", response_model=ReviewCardRead)
def get_next_review_card(
    strategy: str = Query("oldest", pattern="^(oldest|newest|random)$"),
    db: Session = Depends(get_db),
) -> ReviewCardRead:
    cards = list(
        db.scalars(
            select(UnverifiedCard).where(UnverifiedCard.card_state != CardState.human_verified)
        )
    )
    if not cards:
        raise HTTPException(status_code=404, detail="no cards awaiting human verification")

    if strategy == "oldest":
        card = min(cards, key=lambda item: item.unverified_card_id)
    elif strategy == "newest":
        card = max(cards, key=lambda item: item.unverified_card_id)
    else:
        card = random.choice(cards)

    candidate_ids = json.loads(card.machine_candidate_scryfall_ids or "[]")
    return ReviewCardRead(
        unverified_card_id=card.unverified_card_id,
        collection_id=card.collection_id,
        job_id=card.job_id,
        card_state=card.card_state,
        raw_image_url=f"/unverified-cards/{card.unverified_card_id}/raw-image",
        expected_scryfall_id=card.expected_scryfall_id,
        machine_candidate_scryfall_ids=candidate_ids,
    )


@app.get("/unverified-cards/{unverified_card_id}/raw-image")
def get_unverified_card_raw_image(unverified_card_id: int, db: Session = Depends(get_db)) -> FileResponse:
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None or card.raw_image_uri is None:
        raise HTTPException(status_code=404, detail="raw image not found")
    image_path = Path(card.raw_image_uri)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="raw image not found")
    return FileResponse(image_path)


@app.post("/unverified-cards/{unverified_card_id}/verify", response_model=CollectionCardRead)
def human_verify_unverified_card(
    unverified_card_id: int,
    payload: HumanVerificationCreate,
    db: Session = Depends(get_db),
) -> CollectionCard:
    unverified_card = db.get(UnverifiedCard, unverified_card_id)
    if unverified_card is None:
        raise HTTPException(status_code=404, detail="unverified card not found")

    from .models import utcnow

    unverified_card.card_state = CardState.human_verified
    card = CollectionCard(
        collection_id=unverified_card.collection_id,
        source_unverified_card_id=unverified_card.unverified_card_id,
        job_id=unverified_card.job_id,
        scryfall_id=payload.final_scryfall_id,
        name=payload.name,
        set_code=payload.set_code,
        collector_number=payload.collector_number,
        foil=payload.foil,
        language=payload.language,
        validation_source=ValidationSource.human,
        validated_at=utcnow(),
    )
    db.add(card)
    if unverified_card.job is not None:
        from .models import JobStatus

        unverified_card.job.status = JobStatus.human_validated
    db.commit()
    db.refresh(card)
    return card


@app.get("/collections/{collection_id}/export.csv")
def export_collection_csv(collection_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")

    cards = list(
        db.scalars(
            select(CollectionCard)
            .where(CollectionCard.collection_id == collection_id)
            .order_by(CollectionCard.collection_card_id)
        )
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "collection_card_id",
            "collection_id",
            "job_id",
            "source_unverified_card_id",
            "scryfall_id",
            "name",
            "set_code",
            "collector_number",
            "foil",
            "language",
            "validation_source",
            "validated_at",
        ]
    )
    for card in cards:
        writer.writerow(
            [
                card.collection_card_id,
                card.collection_id,
                card.job_id or "",
                card.source_unverified_card_id or "",
                card.scryfall_id,
                card.name,
                card.set_code,
                card.collector_number,
                "" if card.foil is None else card.foil,
                card.language or "",
                card.validation_source.value,
                card.validated_at.isoformat(),
            ]
        )

    buffer.seek(0)
    filename = f'collection-{collection.collection_id}.csv'
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

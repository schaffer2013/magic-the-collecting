from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Collection, CollectionCard, RegistrationJob, VerificationState
from .schemas import (
    CollectionCardRead,
    CollectionCreate,
    CollectionRead,
    RegistrationJobCreate,
    RegistrationJobRead,
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
        CollectionCard(
            collection_id=collection_id,
            job_id=job.job_id,
            raw_image_uri=str(raw_image_path),
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
    verification_state: VerificationState | None = Query(None),
    db: Session = Depends(get_db),
) -> list[CollectionCard]:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    query = select(CollectionCard).where(CollectionCard.collection_id == collection_id)
    if verification_state is not None:
        query = query.where(CollectionCard.verification_state == verification_state)
    return list(db.scalars(query.order_by(CollectionCard.collection_card_id)))


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
            "verification_state",
            "raw_image_uri",
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
                card.verification_state.value,
                card.raw_image_uri or "",
                card.scryfall_id or "",
                card.name or "",
                card.set_code or "",
                card.collector_number or "",
                "" if card.foil is None else card.foil,
                card.language or "",
                card.validation_source.value if card.validation_source else "",
                card.validated_at.isoformat() if card.validated_at else "",
            ]
        )

    buffer.seek(0)
    filename = f'collection-{collection.collection_id}.csv'
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

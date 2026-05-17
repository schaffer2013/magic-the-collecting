from __future__ import annotations

import csv
import io
import random
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .images import parse_bounding_box
from .models import CardState, Collection, CollectionCard, UnverifiedCard
from .models import ReviewDecision, ReviewDecisionKind
from .schemas import (
    BatchTransferCreate,
    CollectionCardRead,
    CollectionCreate,
    CollectionRead,
    CollectionSummaryRead,
    HumanVerificationCreate,
    ReviewDecisionCreate,
    CardSearchResult,
    ReviewCardRead,
    TransferCreate,
    UnverifiedCardRead,
)
from .services import candidate_ids, create_unverified_card, raw_image_url, verify_unverified_card
from .catalog import get_card_metadata, search_cards
from .config import settings

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Magic: The Collecting", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")


def unverified_read(card: UnverifiedCard) -> UnverifiedCardRead:
    import json

    return UnverifiedCardRead(
        unverified_card_id=card.unverified_card_id,
        collection_id=card.collection_id,
        card_state=card.card_state,
        raw_image_url=raw_image_url(card),
        overlay_image_url=(
            f"/unverified-cards/{card.unverified_card_id}/overlay-image" if card.overlay_image_uri else None
        ),
        recognition_image_url=f"/unverified-cards/{card.unverified_card_id}/recognition-image",
        bounding_box=json.loads(card.bounding_box) if card.bounding_box else None,
        expected_scryfall_id=card.expected_scryfall_id,
        machine_candidate_scryfall_ids=candidate_ids(card),
        machine_confidence=card.machine_confidence,
        machine_review_reason=card.machine_review_reason,
        inducted_at=card.inducted_at,
    )


def summary_for_collection(db: Session, collection_id: str) -> CollectionSummaryRead:
    counts = dict(
        db.execute(
            select(UnverifiedCard.card_state, func.count())
            .where(UnverifiedCard.collection_id == collection_id)
            .group_by(UnverifiedCard.card_state)
        ).all()
    )
    trusted_count = db.scalar(
        select(func.count()).select_from(CollectionCard).where(CollectionCard.collection_id == collection_id)
    )
    return CollectionSummaryRead(
        collection_id=collection_id,
        unprocessed_count=counts.get(CardState.unprocessed, 0),
        machine_recognized_count=counts.get(CardState.machine_recognized, 0),
        human_verified_unverified_count=counts.get(CardState.human_verified, 0),
        trusted_collection_card_count=trusted_count or 0,
    )


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
def list_collections(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Collection]:
    return list(db.scalars(select(Collection).order_by(Collection.created_at).limit(limit).offset(offset)))


@app.get("/collections/{collection_id}/summary", response_model=CollectionSummaryRead)
def get_collection_summary(collection_id: str, db: Session = Depends(get_db)) -> CollectionSummaryRead:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    return summary_for_collection(db, collection_id)


@app.post(
    "/collections/{collection_id}/unverified-cards",
    response_model=UnverifiedCardRead,
    status_code=status.HTTP_201_CREATED,
)
async def intake_unverified_card(
    collection_id: str,
    raw_image: UploadFile = File(...),
    sorter_expected_scryfall_id: str | None = Form(None),
    bounding_box: str | None = Form(None),
    db: Session = Depends(get_db),
) -> UnverifiedCardRead:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    image_bytes = await raw_image.read()
    if raw_image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="unsupported image media type")
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="raw image exceeds maximum upload size")
    try:
        parsed_bounding_box = parse_bounding_box(bounding_box)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    card = create_unverified_card(
        db,
        collection_id=collection_id,
        image_bytes=image_bytes,
        suffix=Path(raw_image.filename or "").suffix,
        media_type=raw_image.content_type,
        expected_scryfall_id=sorter_expected_scryfall_id,
        bounding_box=parsed_bounding_box,
    )
    return unverified_read(card)


@app.get("/collections/{collection_id}/unverified-cards", response_model=list[UnverifiedCardRead])
def list_unverified_cards(
    collection_id: str,
    card_state: CardState | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[UnverifiedCardRead]:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    query = select(UnverifiedCard).where(UnverifiedCard.collection_id == collection_id)
    if card_state is not None:
        query = query.where(UnverifiedCard.card_state == card_state)
    cards = db.scalars(query.order_by(UnverifiedCard.inducted_at).limit(limit).offset(offset)).all()
    return [unverified_read(card) for card in cards]


@app.get("/collections/{collection_id}/review-cards/next", response_model=ReviewCardRead)
def get_next_review_card(
    collection_id: str,
    strategy: str = Query("oldest", pattern="^(oldest|newest|random)$"),
    db: Session = Depends(get_db),
) -> ReviewCardRead:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    cards = list(
        db.scalars(
            select(UnverifiedCard).where(
                UnverifiedCard.collection_id == collection_id,
                UnverifiedCard.card_state == CardState.machine_recognized,
                ~exists().where(ReviewDecision.unverified_card_id == UnverifiedCard.unverified_card_id),
            )
        )
    )
    if not cards:
        raise HTTPException(status_code=404, detail="no cards awaiting human verification")
    if strategy == "oldest":
        card = min(cards, key=lambda item: item.inducted_at)
    elif strategy == "newest":
        card = max(cards, key=lambda item: item.inducted_at)
    else:
        card = random.choice(cards)
    return ReviewCardRead(**unverified_read(card).model_dump())


@app.get("/unverified-cards/{unverified_card_id}/raw-image")
def get_unverified_raw_image(unverified_card_id: str, db: Session = Depends(get_db)) -> FileResponse:
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None or not Path(card.raw_image_uri).exists():
        raise HTTPException(status_code=404, detail="raw image not found")
    return FileResponse(card.raw_image_uri, media_type=card.raw_image_media_type)


@app.get("/unverified-cards/{unverified_card_id}/overlay-image")
def get_unverified_overlay_image(unverified_card_id: str, db: Session = Depends(get_db)) -> FileResponse:
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None or card.overlay_image_uri is None or not Path(card.overlay_image_uri).exists():
        raise HTTPException(status_code=404, detail="overlay image not found")
    return FileResponse(card.overlay_image_uri, media_type="image/png")


@app.get("/unverified-cards/{unverified_card_id}/recognition-image")
def get_unverified_recognition_image(unverified_card_id: str, db: Session = Depends(get_db)) -> FileResponse:
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None or not Path(card.recognition_image_uri).exists():
        raise HTTPException(status_code=404, detail="recognition image not found")
    return FileResponse(card.recognition_image_uri, media_type="image/png")


@app.post("/unverified-cards/{unverified_card_id}/verify", response_model=CollectionCardRead)
def verify_card(
    unverified_card_id: str,
    payload: HumanVerificationCreate,
    db: Session = Depends(get_db),
) -> CollectionCard:
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="unverified card not found")
    return verify_unverified_card(db, card, scryfall_id=payload.final_scryfall_id, finish=payload.finish)


@app.post("/unverified-cards/{unverified_card_id}/decision")
def create_review_decision(
    unverified_card_id: str,
    payload: ReviewDecisionCreate,
    db: Session = Depends(get_db),
):
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="unverified card not found")
    if db.scalar(select(ReviewDecision).where(ReviewDecision.unverified_card_id == unverified_card_id)) is not None:
        raise HTTPException(status_code=409, detail="unverified card already has a review decision")
    if payload.decision_kind != ReviewDecisionKind.unreadable and (
        payload.final_scryfall_id is None or payload.finish is None
    ):
        raise HTTPException(status_code=422, detail="final_scryfall_id and finish are required")
    decision = ReviewDecision(
        unverified_card_id=unverified_card_id,
        decision_kind=payload.decision_kind,
        final_scryfall_id=payload.final_scryfall_id,
        notes=payload.notes,
    )
    db.add(decision)
    collection_card = None
    if payload.decision_kind != ReviewDecisionKind.unreadable:
        collection_card = verify_unverified_card(
            db, card, scryfall_id=payload.final_scryfall_id, finish=payload.finish
        )
    else:
        db.commit()
    return {
        "decision_kind": payload.decision_kind,
        "collection_card": CollectionCardRead.model_validate(collection_card) if collection_card else None,
    }


@app.get("/cards/search", response_model=list[CardSearchResult])
def search_card_printings(q: str = Query(..., min_length=1)) -> list[CardSearchResult]:
    return [CardSearchResult(**metadata.__dict__) for metadata in search_cards(q)]


@app.get("/collections/{collection_id}/cards", response_model=list[CollectionCardRead])
def list_collection_cards(
    collection_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[CollectionCard]:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    return list(
        db.scalars(
            select(CollectionCard)
            .where(CollectionCard.collection_id == collection_id)
            .order_by(CollectionCard.validated_at)
            .limit(limit)
            .offset(offset)
        )
    )


@app.post("/collection-cards/{collection_card_id}/transfer", response_model=CollectionCardRead)
def transfer_card(
    collection_card_id: str,
    payload: TransferCreate,
    db: Session = Depends(get_db),
) -> CollectionCard:
    card = db.get(CollectionCard, collection_card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="collection card not found")
    if db.get(Collection, payload.target_collection_id) is None:
        raise HTTPException(status_code=404, detail="target collection not found")
    card.collection_id = payload.target_collection_id
    db.commit()
    db.refresh(card)
    return card


@app.post("/collection-cards/transfer", response_model=list[CollectionCardRead])
def transfer_cards(payload: BatchTransferCreate, db: Session = Depends(get_db)) -> list[CollectionCard]:
    failures = []
    if db.get(Collection, payload.target_collection_id) is None:
        failures.extend(
            {"collection_card_id": card_id, "reason": "target collection not found"}
            for card_id in payload.collection_card_ids
        )
    cards_by_id = {
        card.collection_card_id: card
        for card in db.scalars(
            select(CollectionCard).where(CollectionCard.collection_card_id.in_(payload.collection_card_ids))
        )
    }
    failures.extend(
        {"collection_card_id": card_id, "reason": "collection card not found"}
        for card_id in payload.collection_card_ids
        if card_id not in cards_by_id
    )
    if failures:
        raise HTTPException(status_code=409, detail={"message": "batch transfer could not be completed", "failures": failures})
    for card in cards_by_id.values():
        card.collection_id = payload.target_collection_id
    db.commit()
    return [cards_by_id[card_id] for card_id in payload.collection_card_ids]


@app.get("/collections/{collection_id}/export.csv")
def export_cards(collection_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    cards = list(
        db.scalars(
            select(CollectionCard)
            .where(CollectionCard.collection_id == collection_id)
            .order_by(CollectionCard.validated_at)
        )
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "collection_card_id",
            "collection_id",
            "source_unverified_card_id",
            "scryfall_id",
            "name",
            "set_code",
            "collector_number",
            "finish",
            "validation_source",
            "validated_at",
        ]
    )
    for card in cards:
        writer.writerow(
            [
                card.collection_card_id,
                card.collection_id,
                card.source_unverified_card_id or "",
                card.scryfall_id,
                card.name,
                card.set_code,
                card.collector_number,
                card.finish.value,
                card.validation_source.value,
                card.validated_at.isoformat(),
            ]
        )
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")


@app.get("/collections/{collection_id}/unverified-cards/export.csv")
def export_unverified_cards(collection_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")
    cards = [
        unverified_read(card)
        for card in db.scalars(
            select(UnverifiedCard)
            .where(UnverifiedCard.collection_id == collection_id)
            .order_by(UnverifiedCard.inducted_at)
        )
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "unverified_card_id",
            "collection_id",
            "card_state",
            "raw_image_uri",
            "expected_scryfall_id",
            "machine_candidate_scryfall_ids",
            "inducted_at",
        ]
    )
    for card in cards:
        writer.writerow(
            [
                card.unverified_card_id,
                card.collection_id,
                card.card_state.value,
                card.raw_image_url,
                card.expected_scryfall_id or "",
                ",".join(card.machine_candidate_scryfall_ids),
                card.inducted_at.isoformat(),
            ]
        )
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")


@app.get("/", response_class=HTMLResponse)
def ui_collections(request: Request, db: Session = Depends(get_db)):
    collections = list_collections(500, 0, db)
    summaries = {collection.collection_id: summary_for_collection(db, collection.collection_id) for collection in collections}
    return templates.TemplateResponse(
        request,
        "collections.html",
        {"collections": collections, "summaries": summaries},
    )


@app.get("/ui/collections/{collection_id}", response_class=HTMLResponse)
def ui_collection_detail(collection_id: str, request: Request, db: Session = Depends(get_db)):
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    return templates.TemplateResponse(
        request,
        "collection_detail.html",
        {
            "collection": collection,
            "summary": summary_for_collection(db, collection_id),
            "cards": list_collection_cards(collection_id, 500, 0, db),
        },
    )


@app.get("/ui/collections/{collection_id}/queue", response_class=HTMLResponse)
def ui_queue(collection_id: str, request: Request, db: Session = Depends(get_db)):
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    cards = list_unverified_cards(collection_id, CardState.machine_recognized, 500, 0, db)
    return templates.TemplateResponse(request, "queue.html", {"collection": collection, "cards": cards})


@app.get("/ui/collections/{collection_id}/review/next")
def ui_next_review(
    collection_id: str,
    strategy: str = Query("oldest", pattern="^(oldest|newest|random)$"),
    db: Session = Depends(get_db),
):
    card = get_next_review_card(collection_id, strategy, db)
    return RedirectResponse(url=f"/ui/unverified-cards/{card.unverified_card_id}/review", status_code=303)


@app.get("/ui/register", response_class=HTMLResponse)
def ui_register(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "register.html", {"collections": list_collections(500, 0, db)})


@app.get("/ui/unverified-cards/{unverified_card_id}/review", response_class=HTMLResponse)
def ui_review(unverified_card_id: str, request: Request, db: Session = Depends(get_db)):
    card = db.get(UnverifiedCard, unverified_card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="unverified card not found")
    reference = None
    if card.expected_scryfall_id:
        try:
            reference = get_card_metadata(card.expected_scryfall_id)
        except Exception:
            reference = None
    return templates.TemplateResponse(
        request,
        "review.html",
        {"card": unverified_read(card), "collection": card.collection, "reference": reference},
    )

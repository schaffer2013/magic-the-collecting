from __future__ import annotations

from registration_service.maintenance import cleanup_verified_raw_images
from registration_service.models import CardState, CollectionCard, Finish, UnverifiedCard, ValidationSource, utcnow
from registration_service.config import settings
from registration_service.services import process_next_unprocessed_card


def create_collection(client, name="Main"):
    return client.post("/collections", json={"name": name}).json()


def intake(client, collection_id, image=b"image-bytes", expected=None):
    data = {}
    if expected:
        data["sorter_expected_scryfall_id"] = expected
    return client.post(
        f"/collections/{collection_id}/unverified-cards",
        data=data,
        files={"raw_image": ("card.jpg", image, "image/jpeg")},
    )


def test_bounding_box_creates_overlay_and_recognition_images(client):
    api, _ = client
    from io import BytesIO
    from PIL import Image

    collection = create_collection(api)
    image = Image.new("RGB", (100, 160), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = api.post(
        f"/collections/{collection['collection_id']}/unverified-cards",
        data={"bounding_box": "[[10,10],[90,10],[90,150],[10,150]]"},
        files={"raw_image": ("card.png", buffer.getvalue(), "image/png")},
    )
    payload = response.json()
    assert response.status_code == 201
    assert payload["overlay_image_url"]
    assert payload["recognition_image_url"]
    assert api.get(payload["overlay_image_url"]).status_code == 200
    assert api.get(payload["recognition_image_url"]).status_code == 200


def test_health(client):
    api, _ = client
    assert api.get("/health").json() == {"status": "ok"}


def test_tests_use_isolated_test_environment(client):
    _, _ = client
    assert settings.app_env == "test"
    assert "raw-images" in str(settings.raw_image_dir)


def test_intake_summary_and_duplicate_conflict(client):
    api, _ = client
    collection = create_collection(api)
    first = intake(api, collection["collection_id"])
    duplicate = intake(api, collection["collection_id"])
    assert first.status_code == 201
    assert first.json()["card_state"] == "unprocessed"
    assert duplicate.status_code == 409
    summary = api.get(f"/collections/{collection['collection_id']}/summary").json()
    assert summary["unprocessed_count"] == 1
    assert summary["trusted_collection_card_count"] == 0


def test_duplicate_hashes_are_collection_scoped(client):
    api, _ = client
    main = create_collection(api, "Main")
    trade = create_collection(api, "Trade")
    assert intake(api, main["collection_id"]).status_code == 201
    assert intake(api, trade["collection_id"]).status_code == 201


def test_worker_moves_one_card_to_machine_recognized(client):
    api, Session = client
    collection = create_collection(api)
    intake(api, collection["collection_id"], expected="expected-id")
    with Session() as db:
        processed = process_next_unprocessed_card(db)
        assert processed is not None
        assert processed.card_state == CardState.machine_recognized
    ready = api.get(
        f"/collections/{collection['collection_id']}/unverified-cards",
        params={"card_state": "machine_recognized"},
    ).json()
    assert ready[0]["machine_candidate_scryfall_ids"] == ["expected-id"]
    assert ready[0]["machine_confidence"] == 0.91


def test_review_queue_is_collection_scoped_and_machine_only(client):
    api, Session = client
    main = create_collection(api, "Main")
    trade = create_collection(api, "Trade")
    intake(api, main["collection_id"], image=b"main")
    intake(api, trade["collection_id"], image=b"trade")
    with Session() as db:
        process_next_unprocessed_card(db)
    assert api.get(f"/collections/{main['collection_id']}/review-cards/next").status_code == 200
    assert api.get(f"/collections/{trade['collection_id']}/review-cards/next").status_code == 404


def test_verification_creates_trusted_card(client):
    api, Session = client
    collection = create_collection(api)
    card = intake(api, collection["collection_id"]).json()
    with Session() as db:
        process_next_unprocessed_card(db)
    verified = api.post(
        f"/unverified-cards/{card['unverified_card_id']}/verify",
        json={"final_scryfall_id": "verified-id", "finish": "nonfoil"},
    )
    assert verified.status_code == 200
    assert verified.json()["source_unverified_card_id"] == card["unverified_card_id"]
    cards = api.get(f"/collections/{collection['collection_id']}/cards").json()
    assert len(cards) == 1


def test_transfers_are_atomic_and_report_all_failures(client):
    api, Session = client
    source = create_collection(api, "Source")
    target = create_collection(api, "Target")
    with Session() as db:
        card = CollectionCard(
            collection_id=source["collection_id"],
            scryfall_id="id",
            name="Name",
            set_code="set",
            collector_number="1",
            finish=Finish.nonfoil,
            validation_source=ValidationSource.human,
            validated_at=utcnow(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        card_id = card.collection_card_id
    failed = api.post(
        "/collection-cards/transfer",
        json={"collection_card_ids": [card_id, "missing"], "target_collection_id": target["collection_id"]},
    )
    assert failed.status_code == 409
    assert failed.json()["detail"]["failures"][0]["collection_card_id"] == "missing"
    assert api.get(f"/collections/{source['collection_id']}/cards").json()[0]["collection_card_id"] == card_id


def test_exports_and_ui_smoke(client):
    api, Session = client
    collection = create_collection(api)
    unverified = intake(api, collection["collection_id"]).json()
    with Session() as db:
        process_next_unprocessed_card(db)
    api.post(
        f"/unverified-cards/{unverified['unverified_card_id']}/verify",
        json={"final_scryfall_id": "verified-id", "finish": "foil"},
    )
    assert "collection_card_id" in api.get(f"/collections/{collection['collection_id']}/export.csv").text
    assert "unverified_card_id" in api.get(
        f"/collections/{collection['collection_id']}/unverified-cards/export.csv"
    ).text
    assert api.get("/").status_code == 200
    assert api.get("/ui/register").status_code == 200
    assert api.get(f"/ui/collections/{collection['collection_id']}").status_code == 200
    assert api.get(f"/ui/collections/{collection['collection_id']}/queue").status_code == 200


def test_review_ui_next_redirect_and_page(client):
    api, Session = client
    collection = create_collection(api)
    intake(api, collection["collection_id"], image=b"review-ui")
    with Session() as db:
        process_next_unprocessed_card(db)
    response = api.get(
        f"/ui/collections/{collection['collection_id']}/review/next",
        params={"strategy": "oldest"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = api.get(response.headers["location"])
    assert page.status_code == 200
    assert "Human verify" in page.text


def test_verified_image_cleanup_respects_age(client):
    api, Session = client
    collection = create_collection(api)
    card_payload = intake(api, collection["collection_id"], image=b"cleanup-image").json()
    from datetime import timedelta
    from pathlib import Path

    with Session() as db:
        card = db.get(UnverifiedCard, card_payload["unverified_card_id"])
        card.card_state = CardState.human_verified
        card.verified_at = utcnow() - timedelta(hours=25)
        db.commit()
        path = Path(card.raw_image_uri)
        assert path.exists()
        deleted = cleanup_verified_raw_images(db)
    assert deleted == 1
    assert not path.exists()

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _submit_job(client, collection_id: int, sequence: int = 1):
    return client.post(
        "/registration-jobs",
        data={
            "sorter_run_id": "run-1",
            "sorter_card_seq": str(sequence),
            "collection_id": str(collection_id),
            "captured_at": "2026-05-17T19:00:00Z",
            "source_pile": "A1",
            "destination_pile": "B1",
        },
        files={"raw_image": ("card.jpg", b"image-bytes", "image/jpeg")},
    )


def test_submission_creates_unverified_card_but_not_collection_card(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    response = _submit_job(client, collection["collection_id"])
    assert response.status_code == 201

    cards = client.get(f"/collections/{collection['collection_id']}/cards").json()
    assert cards == []
    unverified_cards = client.get(
        f"/collections/{collection['collection_id']}/unverified-cards"
    ).json()
    assert len(unverified_cards) == 1
    assert unverified_cards[0]["card_state"] == "unprocessed"
    assert unverified_cards[0]["raw_image_uri"]

    export = client.get(f"/collections/{collection['collection_id']}/export.csv")
    assert export.status_code == 200
    lines = export.text.strip().splitlines()
    assert len(lines) == 1
    assert "source_unverified_card_id" in lines[0]


def test_multiple_collections_are_supported(client):
    main = client.post("/collections", json={"name": "Main"}).json()
    trade = client.post("/collections", json={"name": "Trade"}).json()

    collections = client.get("/collections").json()
    assert [collection["collection_id"] for collection in collections] == [
        main["collection_id"],
        trade["collection_id"],
    ]


def test_registration_job_submission_is_idempotent(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    first = _submit_job(client, collection["collection_id"])
    second = _submit_job(client, collection["collection_id"])

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"]


def test_unverified_cards_can_be_filtered_by_card_state(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    _submit_job(client, collection["collection_id"])

    unprocessed = client.get(
        f"/collections/{collection['collection_id']}/unverified-cards",
        params={"card_state": "unprocessed"},
    )
    verified = client.get(
        f"/collections/{collection['collection_id']}/unverified-cards",
        params={"card_state": "human_verified"},
    )

    assert len(unprocessed.json()) == 1
    assert verified.json() == []


def test_review_card_endpoint_returns_raw_image_and_expected_identity(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    response = client.post(
        "/registration-jobs",
        data={
            "sorter_run_id": "run-1",
            "sorter_card_seq": "1",
            "collection_id": str(collection["collection_id"]),
            "captured_at": "2026-05-17T19:00:00Z",
            "source_pile": "A1",
            "destination_pile": "B1",
            "sorter_expected_scryfall_id": "expected-id",
        },
        files={"raw_image": ("card.jpg", b"image-bytes", "image/jpeg")},
    )
    assert response.status_code == 201

    review_card = client.get("/review-cards/next", params={"strategy": "oldest"}).json()
    assert review_card["collection_id"] == collection["collection_id"]
    assert review_card["expected_scryfall_id"] == "expected-id"

    image_response = client.get(review_card["raw_image_url"])
    assert image_response.status_code == 200
    assert image_response.content == b"image-bytes"


def test_human_verify_promotes_card_to_human_verified(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    _submit_job(client, collection["collection_id"])
    card = client.get("/review-cards/next").json()

    response = client.post(
        f"/unverified-cards/{card['unverified_card_id']}/verify",
        json={
            "final_scryfall_id": "verified-id",
            "name": "Llanowar Elves",
            "set_code": "7ed",
            "collector_number": "253",
            "foil": False,
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert response.json()["scryfall_id"] == "verified-id"
    assert response.json()["source_unverified_card_id"] == card["unverified_card_id"]

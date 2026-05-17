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


def test_submission_creates_unverified_collection_card_and_exports_it(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    response = _submit_job(client, collection["collection_id"])
    assert response.status_code == 201

    cards = client.get(f"/collections/{collection['collection_id']}/cards").json()
    assert len(cards) == 1
    assert cards[0]["verification_state"] == "unverified"
    assert cards[0]["scryfall_id"] is None
    assert cards[0]["raw_image_uri"]

    export = client.get(f"/collections/{collection['collection_id']}/export.csv")
    assert export.status_code == 200
    lines = export.text.strip().splitlines()
    assert len(lines) == 2
    assert "verification_state" in lines[0]
    assert "unverified" in lines[1]


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


def test_collection_cards_can_be_filtered_by_verification_state(client):
    collection = client.post("/collections", json={"name": "Main"}).json()
    _submit_job(client, collection["collection_id"])

    unverified = client.get(
        f"/collections/{collection['collection_id']}/cards",
        params={"verification_state": "unverified"},
    )
    verified = client.get(
        f"/collections/{collection['collection_id']}/cards",
        params={"verification_state": "verified"},
    )

    assert len(unverified.json()) == 1
    assert verified.json() == []

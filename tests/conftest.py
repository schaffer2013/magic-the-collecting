from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from registration_service import main
from registration_service.config import settings
from registration_service.database import Base, build_engine, get_db
from registration_service.catalog import CardMetadata
from card_engine.models import Candidate


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    original_raw_dir = settings.raw_image_dir
    original_app_env = settings.app_env
    settings.raw_image_dir = tmp_path / "raw-images"
    settings.app_env = "test"

    class FakeRecognitionResult:
        confidence = 0.91
        review_reason = None
        debug = {"fake": True}
        top_k_candidates = [
            Candidate(
                name="Expected",
                score=0.91,
                scryfall_id="expected-id",
                set_code="tst",
                collector_number="1",
            )
        ]

    monkeypatch.setattr(
        "registration_service.recognition.recognize_unverified_card",
        lambda card: FakeRecognitionResult(),
    )
    monkeypatch.setattr(
        "registration_service.services.get_card_metadata",
        lambda scryfall_id: CardMetadata(
            scryfall_id=scryfall_id,
            name="Known Card",
            set_code="tst",
            collector_number="1",
        ),
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client, TestingSessionLocal
    main.app.dependency_overrides.clear()
    settings.raw_image_dir = original_raw_dir
    settings.app_env = original_app_env

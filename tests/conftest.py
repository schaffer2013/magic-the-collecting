from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from registration_service.database import Base, build_engine, get_db
from registration_service import main


@pytest.fixture()
def client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = build_engine(database_url)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    main.RAW_IMAGE_DIR = tmp_path / "raw-images"

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()

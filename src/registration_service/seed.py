from __future__ import annotations

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import Collection


def seed_default_collection() -> None:
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(Collection).where(Collection.name == "General Collection")) is None:
            db.add(Collection(name="General Collection", description="Default collection"))
            db.commit()


if __name__ == "__main__":
    seed_default_collection()

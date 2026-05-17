from __future__ import annotations

import time

from .database import SessionLocal
from .services import process_next_unprocessed_card


def run_worker_forever(poll_seconds: float = 1.0) -> None:
    while True:
        with SessionLocal() as db:
            process_next_unprocessed_card(db)
        time.sleep(poll_seconds)

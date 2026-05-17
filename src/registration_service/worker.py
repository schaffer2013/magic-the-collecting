from __future__ import annotations

import time

from .database import SessionLocal
from .maintenance import cleanup_duplicate_hashes, cleanup_verified_raw_images
from .services import process_next_unprocessed_card


def run_worker_forever(poll_seconds: float = 1.0) -> None:
    last_cleanup = 0.0
    while True:
        with SessionLocal() as db:
            process_next_unprocessed_card(db)
            now = time.monotonic()
            if now - last_cleanup >= 3600:
                cleanup_duplicate_hashes(db)
                cleanup_verified_raw_images(db)
                last_cleanup = now
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker_forever()

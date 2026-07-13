from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from .database import engine

logger = logging.getLogger(__name__)

ALEMBIC_LOCK_ID = 716802827


def alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    return config


@contextmanager
def migration_lock() -> Iterator[None]:
    if engine.dialect.name != "postgresql":
        yield
        return

    with engine.connect() as connection:
        logger.info("Waiting for database migration lock")
        connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": ALEMBIC_LOCK_ID})
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": ALEMBIC_LOCK_ID})
            logger.info("Released database migration lock")


def database_tables(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def ensure_database_schema() -> None:
    config = alembic_config()
    with migration_lock():
        with engine.connect() as connection:
            tables = database_tables(connection)

        if not tables:
            logger.info("No database tables found; running Alembic migrations")
            command.upgrade(config, "head")
            return

        if "alembic_version" not in tables:
            logger.warning(
                "Existing schema has no Alembic version table; stamping current schema as head without dropping data"
            )
            command.stamp(config, "head")
            return

        logger.info("Running Alembic migrations")
        command.upgrade(config, "head")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    ensure_database_schema()


if __name__ == "__main__":
    main()

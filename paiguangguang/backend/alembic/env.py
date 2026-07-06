from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import create_engine, pool

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db import models as _models  # noqa: F401,E402
from app.db.base import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    should_close = bool(config.attributes.get("close_connection"))
    connectable = None
    if connection is None:
        connectable = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
        connection = connectable.connect()

    try:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
    finally:
        if should_close and connection is not None:
            connection.close()
        elif connectable is not None:
            connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Pull DB path from application settings so there is a single source of truth.
from backend.config import get_settings

# This is the Alembic Config object.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Wire the DB URL from backend.config into Alembic at runtime.
# SQLITE_PATH is a bare filename ("kisanos.db"), so we prefix it.
_settings = get_settings()
_db_path = _settings.SQLITE_PATH
if not _db_path.startswith("sqlite"):
    _db_path = f"sqlite:///{_db_path}"
config.set_main_option("sqlalchemy.url", _db_path)

# No declarative metadata — migrations are written by hand (SQLite reflection
# is unreliable, so --autogenerate is intentionally unused).
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
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
    """Run migrations in 'online' mode (apply directly to the DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

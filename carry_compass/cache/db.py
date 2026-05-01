from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

prices = Table(
    "prices",
    metadata,
    Column("ticker", String(32), nullable=False),
    Column("date", Date, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float, nullable=False),
    Column("adj_close", Float),
    Column("volume", Float),
    Column("inserted_at", DateTime, nullable=False),
    UniqueConstraint("ticker", "date", name="uq_prices_ticker_date"),
    Index("ix_prices_ticker_date", "ticker", "date"),
)

fetch_log = Table(
    "fetch_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ticker", String(32), nullable=False),
    Column("fetched_at", DateTime, nullable=False),
    Column("rows", Integer, nullable=False),
    Column("status", String(16), nullable=False),
    Column("error_msg", String(512)),
    CheckConstraint("status in ('ok', 'empty', 'error')", name="ck_fetch_log_status"),
)


def make_engine(sqlite_path: Path) -> Engine:
    """Create a SQLite engine and initialize cache tables.

    Args:
        sqlite_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine with cache metadata created.
    """
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)
    metadata.create_all(engine)
    return engine

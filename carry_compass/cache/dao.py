from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert

from carry_compass.cache.db import fetch_log, make_engine, prices
from carry_compass.utils.time import to_utc_naive

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def _f(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return to_utc_naive(pd.Timestamp(value)).date()


class PriceCache:
    """SQLite-backed OHLCV cache keyed by ticker and date."""

    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.engine = make_engine(self.sqlite_path)

    def upsert_prices(self, ticker: str, df: pd.DataFrame) -> int:
        """Insert or update canonical price rows for one ticker.

        Args:
            ticker: Yahoo ticker key.
            df: Date-indexed OHLCV frame.

        Returns:
            Number of rows affected by SQLite upsert.
        """
        if df.empty:
            return 0

        canonical = df.rename(columns={column: column.lower().replace(" ", "_") for column in df.columns})
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows = []
        for idx, row in canonical.iterrows():
            close = _f(row.get("close"))
            if close is None:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "date": _date(idx),
                    "open": _f(row.get("open")),
                    "high": _f(row.get("high")),
                    "low": _f(row.get("low")),
                    "close": close,
                    "adj_close": _f(row.get("adj_close")),
                    "volume": _f(row.get("volume")),
                    "inserted_at": now,
                }
            )

        if not rows:
            return 0

        stmt = insert(prices).values(rows)
        update_columns = {
            column.name: getattr(stmt.excluded, column.name)
            for column in prices.c
            if column.name not in {"ticker", "date"}
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "date"],
            set_=update_columns,
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
        return result.rowcount or 0

    def read_prices(
        self,
        ticker: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
    ) -> pd.DataFrame:
        """Read cached prices for one ticker and optional date range.

        Args:
            ticker: Yahoo ticker key.
            start: Optional inclusive start date.
            end: Optional inclusive end date.

        Returns:
            Date-indexed canonical OHLCV frame, empty if no rows match.
        """
        stmt = select(
            prices.c.date,
            prices.c.open,
            prices.c.high,
            prices.c.low,
            prices.c.close,
            prices.c.adj_close,
            prices.c.volume,
        ).where(prices.c.ticker == ticker)
        if start is not None:
            stmt = stmt.where(prices.c.date >= _date(start))
        if end is not None:
            stmt = stmt.where(prices.c.date <= _date(end))
        stmt = stmt.order_by(prices.c.date)

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        if not rows:
            empty = pd.DataFrame(columns=PRICE_COLUMNS)
            empty.index = pd.DatetimeIndex([], name="date")
            return empty

        frame = pd.DataFrame(rows)
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date")[PRICE_COLUMNS]

    def last_date(self, ticker: str) -> date | None:
        """Return the latest cached date for a ticker.

        Args:
            ticker: Yahoo ticker key.

        Returns:
            Latest date in cache, or None when the ticker has no rows.
        """
        stmt = select(func.max(prices.c.date)).where(prices.c.ticker == ticker)
        with self.engine.connect() as conn:
            return conn.execute(stmt).scalar_one_or_none()

    def log_fetch(self, ticker: str, rows: int, status: str, error: str | None = None) -> None:
        """Append an operational fetch-log row.

        Args:
            ticker: Yahoo ticker key.
            rows: Number of downloaded rows.
            status: Short status label such as ok, empty or error.
            error: Optional error message, truncated before storage.
        """
        stmt = fetch_log.insert().values(
            ticker=ticker,
            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            rows=rows,
            status=status,
            error_msg=error[:512] if error else None,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def stats(self) -> pd.DataFrame:
        """Summarize cache coverage by ticker.

        Returns:
            DataFrame with ticker, row count, first date and last date columns.
        """
        stmt = (
            select(
                prices.c.ticker,
                func.count().label("rows"),
                func.min(prices.c.date).label("first"),
                func.max(prices.c.date).label("last"),
            )
            .group_by(prices.c.ticker)
            .order_by(prices.c.ticker)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return pd.DataFrame(rows, columns=["ticker", "rows", "first", "last"])

    def purge(self, ticker: str | None = None) -> int:
        """Delete cached price rows.

        Args:
            ticker: Optional ticker to purge; if None, all price rows are deleted.

        Returns:
            Number of deleted rows.
        """
        stmt = delete(prices)
        if ticker is not None:
            stmt = stmt.where(prices.c.ticker == ticker)
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
        return result.rowcount or 0

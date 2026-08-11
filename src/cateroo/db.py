"""SQLite database layer for meals."""

import datetime
import sqlite3
from types import TracebackType

from cateroo.parser import Meal

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    menu_number TEXT NOT NULL,
    title TEXT NOT NULL,
    ingredients TEXT
);
"""


class Database:
    """SQLite database for storing meals."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def upsert_meal(self, meal: Meal) -> None:
        """Insert or replace a meal keyed by date."""
        self._conn.execute(
            """INSERT OR REPLACE INTO meals
               (date, menu_number, title, ingredients)
               VALUES (?, ?, ?, ?)""",
            (
                meal.date.isoformat(),
                meal.menu_number,
                meal.title,
                meal.ingredients,
            ),
        )
        self._conn.commit()

    def get_all_meals(self) -> list[Meal]:
        """Return all meals ordered by date."""
        cursor = self._conn.execute(
            "SELECT date, menu_number, title, ingredients FROM meals ORDER BY date"
        )
        return [
            Meal(
                date=datetime.date.fromisoformat(row[0]),
                menu_number=row[1],
                title=row[2],
                ingredients=row[3] or "",
            )
            for row in cursor.fetchall()
        ]

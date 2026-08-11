"""Tests for cateroo.db module."""

import datetime
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cateroo.db import Database
from cateroo.parser import Meal


class TestDatabaseInit:
    """Tests for Database initialization and schema creation."""

    def test_creates_tables_on_init(self) -> None:
        with Database(":memory:") as db:
            assert db.get_all_meals() == []

    def test_creating_database_twice_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "test.db")
            with Database(path) as db1:
                db1.upsert_meal(
                    Meal(
                        date=datetime.date(2026, 8, 10),
                        menu_number="cateroo #1",
                        title="TEST",
                        ingredients="stuff",
                    )
                )
            with Database(path) as db2:
                assert len(db2.get_all_meals()) == 1

    def test_context_manager_closes_connection(self) -> None:
        with Database(":memory:") as db:
            assert db.get_all_meals() == []
        with pytest.raises(sqlite3.ProgrammingError):
            db.get_all_meals()


class TestUpsertMeal:
    """Tests for upsert_meal and get_all_meals."""

    def test_upsert_stores_meal(self) -> None:
        with Database(":memory:") as db:
            meal = Meal(
                date=datetime.date(2026, 8, 10),
                menu_number="cateroo #2",
                title="FALAFELBÄLLCHEN",
                ingredients="Rote Bete | Reis",
            )
            db.upsert_meal(meal)
            meals = db.get_all_meals()
            assert len(meals) == 1
            assert meals[0].date == datetime.date(2026, 8, 10)
            assert meals[0].title == "FALAFELBÄLLCHEN"

    def test_upsert_updates_existing_date(self) -> None:
        with Database(":memory:") as db:
            meal1 = Meal(
                date=datetime.date(2026, 8, 10),
                menu_number="cateroo #2",
                title="OLD MEAL",
                ingredients="Old stuff",
            )
            db.upsert_meal(meal1)

            meal2 = Meal(
                date=datetime.date(2026, 8, 10),
                menu_number="cateroo #5",
                title="NEW MEAL",
                ingredients="New stuff",
            )
            db.upsert_meal(meal2)

            meals = db.get_all_meals()
            assert len(meals) == 1
            assert meals[0].title == "NEW MEAL"
            assert meals[0].menu_number == "cateroo #5"

    def test_get_all_meals_returns_sorted_by_date(self) -> None:
        with Database(":memory:") as db:
            dates = [
                datetime.date(2026, 8, 24),
                datetime.date(2026, 8, 10),
                datetime.date(2026, 8, 17),
            ]
            for i, d in enumerate(dates):
                db.upsert_meal(
                    Meal(
                        date=d,
                        menu_number=f"cateroo #{i}",
                        title=f"Meal {i}",
                        ingredients="stuff",
                    )
                )
            meals = db.get_all_meals()
            assert [m.date for m in meals] == sorted(dates)

    def test_get_all_meals_empty_db(self) -> None:
        with Database(":memory:") as db:
            meals = db.get_all_meals()
            assert meals == []

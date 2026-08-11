"""Tests for cateroo.ics module."""

import datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar

from cateroo.ics import generate_ics
from cateroo.parser import Meal

BERLIN = ZoneInfo("Europe/Berlin")


class TestGenerateIcs:
    """Tests for generate_ics function."""

    def _sample_meals(self) -> list[Meal]:
        return [
            Meal(
                date=datetime.date(2026, 8, 10),
                menu_number="cateroo #2",
                title="FALAFELBÄLLCHEN *VEGAN*",
                ingredients="Rote Bete | Schwarzer Reis",
            ),
            Meal(
                date=datetime.date(2026, 8, 11),
                menu_number="cateroo #5",
                title="SALATBOWL",
                ingredients="Glasnudeln | Erdnuss-Crunch",
            ),
        ]

    def test_returns_bytes(self) -> None:
        result = generate_ics(self._sample_meals())
        assert isinstance(result, bytes)

    def test_contains_vcalendar(self) -> None:
        result = generate_ics(self._sample_meals())
        cal = Calendar.from_ical(result)
        assert str(cal.get("PRODID")) == "-//Cateroo//Meal Calendar//EN"
        assert str(cal.get("X-WR-CALNAME")) == "Cateroo Lunch"

    def test_contains_all_events(self) -> None:
        result = generate_ics(self._sample_meals())
        cal = Calendar.from_ical(result)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 2

    def test_event_uid_format(self) -> None:
        result = generate_ics(self._sample_meals()[:1])
        cal = Calendar.from_ical(result)
        event = next(c for c in cal.walk() if c.name == "VEVENT")
        assert str(event.get("UID")) == "lunch-2026-08-10@cateroo.ulf.jaehrig.de"

    def test_event_summary(self) -> None:
        result = generate_ics(self._sample_meals()[:1])
        cal = Calendar.from_ical(result)
        event = next(c for c in cal.walk() if c.name == "VEVENT")
        assert str(event.get("SUMMARY")) == "Lunch: FALAFELBÄLLCHEN *VEGAN*"

    def test_event_dtstart(self) -> None:
        result = generate_ics(self._sample_meals()[:1])
        cal = Calendar.from_ical(result)
        event = next(c for c in cal.walk() if c.name == "VEVENT")
        expected = datetime.datetime(2026, 8, 10, 12, 0, tzinfo=BERLIN)
        assert event.get("DTSTART").dt == expected

    def test_event_dtend(self) -> None:
        result = generate_ics(self._sample_meals()[:1])
        cal = Calendar.from_ical(result)
        event = next(c for c in cal.walk() if c.name == "VEVENT")
        expected = datetime.datetime(2026, 8, 10, 13, 0, tzinfo=BERLIN)
        assert event.get("DTEND").dt == expected

    def test_event_description(self) -> None:
        result = generate_ics(self._sample_meals()[:1])
        cal = Calendar.from_ical(result)
        event = next(c for c in cal.walk() if c.name == "VEVENT")
        desc = str(event.get("DESCRIPTION"))
        assert "cateroo #2" in desc
        assert "Rote Bete | Schwarzer Reis" in desc

    def test_empty_meals(self) -> None:
        result = generate_ics([])
        cal = Calendar.from_ical(result)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert events == []

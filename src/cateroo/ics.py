"""ICS file generation for meal events."""

import datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from cateroo.parser import Meal

TIMEZONE = ZoneInfo("Europe/Berlin")
UID_DOMAIN = "cateroo.ulf.jaehrig.de"


def generate_ics(meals: list[Meal]) -> bytes:
    """Generate a complete .ics file containing all meals as events.

    Returns serialized iCalendar bytes with one VEVENT per meal.
    """
    cal = Calendar()
    cal.add("prodid", "-//Cateroo//Meal Calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Cateroo Lunch")

    for meal in meals:
        event = Event()
        event.add("uid", f"lunch-{meal.date.isoformat()}@{UID_DOMAIN}")
        event.add("summary", f"Lunch: {meal.title}")
        event.add("description", f"{meal.menu_number}\n{meal.ingredients}")
        event.add(
            "dtstart",
            datetime.datetime(
                meal.date.year,
                meal.date.month,
                meal.date.day,
                12,
                0,
                tzinfo=TIMEZONE,
            ),
        )
        event.add(
            "dtend",
            datetime.datetime(
                meal.date.year,
                meal.date.month,
                meal.date.day,
                13,
                0,
                tzinfo=TIMEZONE,
            ),
        )
        event.add("dtstamp", datetime.datetime.now(tz=datetime.UTC))
        cal.add_component(event)

    return cal.to_ical()

"""Main entry point for the Cateroo application."""

import datetime
import logging
import sys
from pathlib import Path

from cateroo.api_client import CaterooApiClient
from cateroo.config import load_config
from cateroo.db import Database
from cateroo.ics import generate_ics
from cateroo.parser import Meal, parse_gastro_text

logger = logging.getLogger(__name__)

# Look ahead 4 weeks for bookings
LOOKAHEAD_WEEKS = 4


def main() -> None:
    """Run the Cateroo API-to-ICS pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config = load_config()

    # Login to Cateroo portal
    api = CaterooApiClient(config)
    try:
        api.login()
    except (OSError, RuntimeError):
        logger.exception("Failed to login to Cateroo portal")
        sys.exit(1)

    logger.info("Logged in to Cateroo portal")

    # Calculate date range: today to 4 weeks ahead
    today = datetime.date.today()
    end_date = today + datetime.timedelta(weeks=LOOKAHEAD_WEEKS)
    von = today.isoformat()
    bis = end_date.isoformat()

    # Get bookings (what you ordered)
    bookings = api.get_bookings(von, bis)
    logger.info("Found %d booking(s) in range %s to %s", len(bookings), von, bis)

    if not bookings:
        logger.info("No bookings found, nothing to do")
        return

    # Get menu offers to resolve meal details
    menu_map = api.get_menu_offer(von, bis)
    logger.info("Loaded menu offers for %d date/menu combinations", len(menu_map))

    # Process bookings into meals
    with Database(config.db_path) as db:
        for booking in bookings:
            key = f"{booking.date}|{booking.menu_number}"
            gastro_text = menu_map.get(key)

            title, ingredients = parse_gastro_text(gastro_text)
            if not title:
                title = booking.menu_number

            meal = Meal(
                date=datetime.date.fromisoformat(booking.date),
                menu_number=booking.menu_number,
                title=title,
                ingredients=ingredients,
            )
            db.upsert_meal(meal)
            logger.info("Upserted meal: %s - %s", booking.date, title)

        # Generate .ics file from all meals in DB
        all_meals = db.get_all_meals()

    ics_data = generate_ics(all_meals)
    output_path = Path(config.ics_output_path)
    output_path.write_bytes(ics_data)
    logger.info("Wrote %d meal(s) to %s", len(all_meals), output_path)

    logger.info("Done")

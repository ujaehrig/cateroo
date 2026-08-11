"""HTTP API client for the Cateroo ordering portal."""

import json
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Tag

from cateroo.config import Config

BASE_PATH = "/Vorbesteller"
LOGIN_PATH = f"{BASE_PATH}/Default.aspx"
BOOKINGS_PATH = f"{BASE_PATH}/BestellHistorie.aspx/getBestellTableJSON"
MENU_PATH = f"{BASE_PATH}/OrderForm.aspx/MenuOffer"


@dataclass
class Booking:
    """A single booking from the order history."""

    date: str  # ISO format YYYY-MM-DD (from bestfuer DD.MM.YYYY)
    menu_number: str  # e.g. "cateroo #2"
    quantity: int  # anz field (1 = ordered, 0 = cancelled)


class CaterooApiClient:
    """Client for the Cateroo essenbestellen.net portal API."""

    def __init__(self, config: Config) -> None:
        self._base_url = config.cateroo_url
        self._username = config.cateroo_user
        self._password = config.cateroo_password
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Cateroo-Calendar/1.0"})

    def login(self) -> None:
        """Authenticate and obtain session cookies.

        Fetches the login page to get ASP.NET hidden fields,
        then POSTs credentials to get the .ASPXAUTH cookie.
        """
        login_url = f"{self._base_url}{LOGIN_PATH}"

        # GET login page to extract hidden form fields
        resp = self._session.get(login_url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        form_data = self._extract_form_fields(soup)

        # Remove extra submit buttons (only LoginButton should be sent)
        form_data.pop("LoginButton2", None)

        # Add credentials
        form_data["Login1$UserName"] = self._username
        form_data["Login1$Password"] = self._password
        form_data["Login1$LoginButton"] = "Anmelden"

        # POST login (allow redirects to follow auth redirect)
        self._session.post(login_url, data=form_data)

        if ".ASPXAUTH" not in self._session.cookies.get_dict():
            msg = "Login failed: no .ASPXAUTH cookie received"
            raise RuntimeError(msg)

    def get_bookings(self, von_datum: str, bis_datum: str) -> list[Booking]:
        """Get order history for a date range.

        Args:
            von_datum: Start date in YYYY-MM-DD format.
            bis_datum: End date in YYYY-MM-DD format.

        Returns:
            List of Booking objects for orders with quantity > 0.
        """
        url = f"{self._base_url}{BOOKINGS_PATH}"
        payload = {"inVonDatum": von_datum, "inBisDatum": bis_datum}

        resp = self._session.post(url, json=payload)
        resp.raise_for_status()

        outer = resp.json()
        parameter = json.loads(json.loads(outer["d"])["parameter"])
        buchungen = parameter.get("buchungen", [])

        bookings: list[Booking] = []
        for b in buchungen:
            quantity = int(b["anz"])
            if quantity < 1:
                continue
            # Convert DD.MM.YYYY to YYYY-MM-DD
            parts = b["bestfuer"].split(".")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            bookings.append(
                Booking(
                    date=iso_date,
                    menu_number=b["menue"],
                    quantity=quantity,
                )
            )

        return bookings

    def get_menu_offer(self, von_datum: str, bis_datum: str) -> dict[str, str | None]:
        """Get menu offers for a date range.

        Args:
            von_datum: Start date in YYYY-MM-DD format.
            bis_datum: End date in YYYY-MM-DD format.

        Returns:
            Dict mapping (date, menu_number) key "YYYY-MM-DD|menu_name"
            to gastro_text HTML string (or None if not available).
        """
        url = f"{self._base_url}{MENU_PATH}"
        payload = {
            "vonDatum": von_datum,
            "bisDatum": bis_datum,
            "idx_splan": 0,
        }

        resp = self._session.post(url, json=payload)
        resp.raise_for_status()

        outer = resp.json()
        parameter = json.loads(json.loads(outer["d"])["parameter"])
        day_offers = parameter.get("dayoffer", [])

        menu_map: dict[str, str | None] = {}
        for day in day_offers:
            datum = day["datum"]  # YYYY-MM-DD
            for menu in day.get("menus", []):
                if not menu.get("is_active"):
                    continue
                name = menu.get("name_menulinie", "")
                gastro_text = menu.get("gastro_text")
                key = f"{datum}|{name}"
                menu_map[key] = gastro_text

        return menu_map

    def _extract_form_fields(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract hidden form fields from the login page."""
        fields: dict[str, str] = {}
        for inp in soup.find_all("input"):
            if not isinstance(inp, Tag):  # pragma: no cover
                continue
            name = inp.get("name")
            value = inp.get("value", "")
            if isinstance(name, str) and name:
                fields[name] = value if isinstance(value, str) else ""
        return fields

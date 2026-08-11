"""HTML email parser for Cateroo order confirmations."""

import datetime
import email
import email.policy
from dataclasses import dataclass
from email.message import EmailMessage

from bs4 import BeautifulSoup, Tag


@dataclass
class Meal:
    """A single ordered meal extracted from a Cateroo confirmation email."""

    date: datetime.date
    menu_number: str
    title: str
    ingredients: str

    def __post_init__(self) -> None:
        self.menu_number = self.menu_number.strip()
        self.title = self.title.strip()
        self.ingredients = self.ingredients.strip()


def extract_html_body(raw: bytes) -> str:
    """Extract the HTML body from raw email bytes.

    Parses the MIME structure and returns the decoded HTML part.
    Returns empty string if no HTML part is found.
    """
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    assert isinstance(msg, EmailMessage)

    content_type = msg.get_content_type()

    # Single-part email
    if not msg.is_multipart():
        if content_type == "text/html":
            body = msg.get_content()
            return body if isinstance(body, str) else ""
        return ""

    # Multipart: walk parts and find text/html
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            body = part.get_content()
            return body if isinstance(body, str) else ""

    return ""


def _find_meal_table(soup: BeautifulSoup) -> Tag | None:
    """Find the meal order table in the HTML.

    Looks for a table whose thead contains 'Datum' header.
    Selects the most deeply nested one (the actual data table,
    not the wrapper layout tables).
    """
    candidates: list[Tag] = []
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if not isinstance(thead, Tag):
            continue
        if "Datum" in thead.get_text():
            candidates.append(table)

    # Return the last (most deeply nested) candidate
    return candidates[-1] if candidates else None


def _parse_date(date_text: str) -> datetime.date:
    """Parse date from format 'Mo, DD.MM.YYYY' to datetime.date."""
    # Strip day name prefix like 'Mo, ' or 'Di, '
    parts = date_text.split(", ", 1)
    date_str = parts[1] if len(parts) == 2 else parts[0]
    return datetime.datetime.strptime(date_str, "%d.%m.%Y").date()


def _parse_menu_cell(td: Tag) -> tuple[str, str, str]:
    """Extract menu_number, title, and ingredients from the Menü cell.

    Returns (menu_number, title, ingredients).
    """
    bolds = td.find_all("b", recursive=True)
    menu_number = bolds[0].get_text(strip=True) if bolds else ""

    # Title: find the first bold after menu_number that isn't a sub-category
    title = ""
    for b in bolds[1:]:
        text = b.get_text(strip=True)
        if text and not text.startswith("*"):
            title = text
            break
    # If all remaining bolds start with *, take the last one anyway
    if not title and len(bolds) > 1:
        title = bolds[-1].get_text(strip=True)

    # Ingredients: first div without a <b> and not an allergen region
    ingredients = ""
    for div in td.find_all("div", recursive=False):
        class_str = " ".join(div.get_attribute_list("class"))
        if "alergen" in class_str:
            continue
        if div.find("b"):
            continue
        text = div.get_text(strip=True)
        if text:
            ingredients = text
            break

    return menu_number, title, ingredients


def _find_menu_td(row: Tag) -> Tag | None:
    """Find the Menü table cell in a row by data-label attribute."""
    for td in row.find_all("td"):
        label = td.get("data-label")
        if isinstance(label, str) and "Men" in label:
            return td
    return None


def parse_meals(html: str) -> list[Meal]:
    """Parse meals from the HTML body of a Cateroo order email.

    Returns a list of Meal objects extracted from the order table.
    Returns empty list if no meal table is found.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    table = _find_meal_table(soup)
    if table is None:
        return []

    tbody = table.find("tbody")
    if not isinstance(tbody, Tag):
        return []

    meals: list[Meal] = []
    for row in tbody.find_all("tr", recursive=False):
        datum_td = row.find("td", attrs={"data-label": "Datum"})
        if not isinstance(datum_td, Tag):
            continue

        menu_td = _find_menu_td(row)
        if menu_td is None:
            continue

        date_text = datum_td.get_text(strip=True)
        date = _parse_date(date_text)
        menu_number, title, ingredients = _parse_menu_cell(menu_td)

        meals.append(
            Meal(
                date=date,
                menu_number=menu_number,
                title=title,
                ingredients=ingredients,
            )
        )

    return meals


def parse_email(raw: bytes) -> list[Meal]:
    """Parse meals from raw email bytes.

    Convenience function that combines extract_html_body and parse_meals.
    Returns empty list if no HTML body or no meal table is found.
    """
    html = extract_html_body(raw)
    if not html:
        return []
    return parse_meals(html)


def parse_gastro_text(html: str | None) -> tuple[str, str]:
    """Parse title and ingredients from a gastro_text HTML snippet.

    The gastro_text field from the MenuOffer API contains HTML like:
        <div><b>*feelgoodfood*</b></div>
        <div><b>FALAFELBÄLLCHEN *VEGAN*</b></div>
        <div>Rote Bete | Schwarzer Reis | ...</div>

    Returns (title, ingredients). Returns ("", "") if html is None or empty.
    """
    if not html:
        return ("", "")

    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    if not isinstance(body, Tag):  # pragma: no cover
        return ("", "")

    # Find title: first bold text that isn't a *category* prefix
    title = ""
    for b in body.find_all("b"):
        text = b.get_text(strip=True)
        if text and not text.startswith("*"):
            title = text
            break
    # Fallback: if all bolds start with *, take the last one
    if not title:
        all_bolds = body.find_all("b")
        if all_bolds:
            title = all_bolds[-1].get_text(strip=True)

    # Find ingredients: text content that isn't in a <b> and isn't allergen
    ingredients = ""
    # Strategy: get all text nodes from non-allergen, non-bold elements
    for element in body.find_all(["div", "p"]):
        if not isinstance(element, Tag):  # pragma: no cover
            continue
        class_str = " ".join(element.get_attribute_list("class"))
        if "alergen" in class_str:
            continue
        if element.find("b"):
            continue
        text = element.get_text(strip=True)
        if text:
            ingredients = text
            break

    # Fallback: check for bare text outside divs (some gastro_texts
    # have ingredients as loose text nodes after a <div><b>...</b></div>)
    if not ingredients:
        for text_node in body.stripped_strings:
            # Skip if it matches a bold text we already captured
            bolds_text = {b.get_text(strip=True) for b in body.find_all("b")}
            if text_node in bolds_text:
                continue
            # Skip &nbsp; artifacts
            if text_node.strip() in ("", "\xa0"):  # pragma: no cover
                continue
            ingredients = text_node
            break

    # Clean up: remove leading/trailing nbsp, normalize whitespace
    ingredients = ingredients.replace("\xa0", " ").strip()
    # Collapse internal newlines
    ingredients = " ".join(ingredients.split())

    return (title, ingredients)

"""Tests for cateroo.parser module."""

import datetime
from pathlib import Path

from cateroo.parser import (
    Meal,
    extract_html_body,
    parse_email,
    parse_gastro_text,
    parse_meals,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestMeal:
    """Tests for the Meal dataclass."""

    def test_construction(self) -> None:
        meal = Meal(
            date=datetime.date(2026, 8, 10),
            menu_number="cateroo #2",
            title="FALAFELBÄLLCHEN *VEGAN*",
            ingredients="Rote Bete | Schwarzer Reis | Zitronen-Soja-Dip",
        )
        assert meal.date == datetime.date(2026, 8, 10)
        assert meal.menu_number == "cateroo #2"
        assert meal.title == "FALAFELBÄLLCHEN *VEGAN*"
        assert meal.ingredients == "Rote Bete | Schwarzer Reis | Zitronen-Soja-Dip"

    def test_strips_whitespace_from_strings(self) -> None:
        meal = Meal(
            date=datetime.date(2026, 8, 10),
            menu_number="  cateroo #2  ",
            title="  SALATBOWL  ",
            ingredients="  Glasnudeln | Erdnuss  ",
        )
        assert meal.menu_number == "cateroo #2"
        assert meal.title == "SALATBOWL"
        assert meal.ingredients == "Glasnudeln | Erdnuss"

    def test_empty_ingredients(self) -> None:
        meal = Meal(
            date=datetime.date(2026, 8, 10),
            menu_number="cateroo #4",
            title="HÄHNCHEN",
            ingredients="",
        )
        assert meal.ingredients == ""


class TestExtractHtmlBody:
    """Tests for extract_html_body function."""

    def test_extracts_html_from_multipart_email(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        assert "<table" in html
        assert "data-label" in html
        assert "FALAFELBÄLLCHEN" in html or "FALAFELB" in html

    def test_returns_empty_string_for_plain_text_only(self) -> None:
        plain_email = (
            b"From: test@example.com\r\n"
            b"To: cateroo@ulf.jaehrig.de\r\n"
            b"Subject: Test\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"This is just plain text.\r\n"
        )
        html = extract_html_body(plain_email)
        assert html == ""

    def test_handles_single_part_html_email(self) -> None:
        html_email = (
            b"From: test@example.com\r\n"
            b"To: cateroo@ulf.jaehrig.de\r\n"
            b"Subject: Test\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"\r\n"
            b"<html><body><p>Hello</p></body></html>\r\n"
        )
        html = extract_html_body(html_email)
        assert "<p>Hello</p>" in html

    def test_returns_empty_for_multipart_without_html(self) -> None:
        multipart_no_html = (
            b"From: test@example.com\r\n"
            b"To: cateroo@ulf.jaehrig.de\r\n"
            b"Subject: Test\r\n"
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/mixed; boundary=boundary123\r\n"
            b"\r\n"
            b"--boundary123\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Just plain text.\r\n"
            b"--boundary123\r\n"
            b"Content-Type: application/pdf\r\n"
            b"Content-Disposition: attachment; filename=doc.pdf\r\n"
            b"\r\n"
            b"fakepdfcontent\r\n"
            b"--boundary123--\r\n"
        )
        html = extract_html_body(multipart_no_html)
        assert html == ""


class TestParseMeals:
    """Tests for parse_meals function."""

    def test_extracts_five_meals_from_sample(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert len(meals) == 5

    def test_first_meal_date(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert meals[0].date == datetime.date(2026, 8, 10)

    def test_first_meal_menu_number(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert meals[0].menu_number == "cateroo #2"

    def test_first_meal_title(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert meals[0].title == "FALAFELBÄLLCHEN *VEGAN*"

    def test_first_meal_ingredients(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        expected = "Rote Bete | Schwarzer Reis | Zitronen-Soja-Dip | Curry-Aubergine"
        assert meals[0].ingredients == expected

    def test_all_dates_correct(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        expected_dates = [
            datetime.date(2026, 8, 10),
            datetime.date(2026, 8, 11),
            datetime.date(2026, 8, 17),
            datetime.date(2026, 8, 18),
            datetime.date(2026, 8, 24),
        ]
        assert [m.date for m in meals] == expected_dates

    def test_last_meal_title(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert meals[4].title == "GEBRATENE HÄHNCHENSTREIFEN IN TOMATENSAUCE"

    def test_last_meal_ingredients(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        html = extract_html_body(raw)
        meals = parse_meals(html)
        assert meals[4].ingredients == (
            "Gefüllte Pasta | Ofenzucchini | Mediterrane Kräuter"
        )

    def test_returns_empty_list_for_html_without_table(self) -> None:
        html = "<html><body><p>No meals here</p></body></html>"
        meals = parse_meals(html)
        assert meals == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        meals = parse_meals("")
        assert meals == []

    def test_table_without_tbody_returns_empty(self) -> None:
        html = """<html><body>
        <table><thead><tr><th>Datum</th></tr></thead></table>
        </body></html>"""
        meals = parse_meals(html)
        assert meals == []

    def test_row_without_datum_cell_is_skipped(self) -> None:
        html = """<html><body>
        <table><thead><tr><th>Datum</th></tr></thead>
        <tbody><tr><td>no data-label</td></tr></tbody>
        </table></body></html>"""
        meals = parse_meals(html)
        assert meals == []

    def test_menu_with_only_star_prefixed_bolds_uses_last(self) -> None:
        html = """<html><body>
        <table><thead><tr><th>Datum</th></tr></thead>
        <tbody><tr>
            <td data-label="Datum">Mo, 01.09.2026</td>
            <td data-label="Menü">
                <b>cateroo #9</b><br>
                <b>*special*</b>
                <div>Some ingredients</div>
            </td>
        </tr></tbody>
        </table></body></html>"""
        meals = parse_meals(html)
        assert len(meals) == 1
        assert meals[0].title == "*special*"

    def test_allergen_div_is_skipped(self) -> None:
        html = """<html><body>
        <table><thead><tr><th>Datum</th></tr></thead>
        <tbody><tr>
            <td data-label="Datum">Di, 02.09.2026</td>
            <td data-label="Menü">
                <b>cateroo #1</b><br>
                <b>TESTMEAL</b>
                <div class="x_essalergenregion">allergen info</div>
                <div>Real ingredients here</div>
            </td>
        </tr></tbody>
        </table></body></html>"""
        meals = parse_meals(html)
        assert len(meals) == 1
        assert meals[0].ingredients == "Real ingredients here"


class TestParseEmail:
    """Tests for parse_email convenience function."""

    def test_parses_full_eml_file(self) -> None:
        raw = (FIXTURES_DIR / "sample_order.eml").read_bytes()
        meals = parse_email(raw)
        assert len(meals) == 5
        assert meals[0].date == datetime.date(2026, 8, 10)
        assert meals[0].title == "FALAFELBÄLLCHEN *VEGAN*"

    def test_returns_empty_for_plain_text_email(self) -> None:
        plain_email = (
            b"From: test@example.com\r\n"
            b"Subject: No HTML\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Just text, no meals.\r\n"
        )
        meals = parse_email(plain_email)
        assert meals == []

    def test_table_without_thead_is_skipped(self) -> None:
        html = """<html><body>
        <table><tbody><tr><td>no thead</td></tr></tbody></table>
        <table><thead><tr><th>Datum</th></tr></thead>
        <tbody><tr>
            <td data-label="Datum">Fr, 05.09.2026</td>
            <td data-label="Menü"><b>cateroo #1</b><b>MEAL</b>
            <div>Stuff</div></td>
        </tr></tbody></table>
        </body></html>"""
        meals = parse_meals(html)
        assert len(meals) == 1
        assert meals[0].title == "MEAL"

    def test_row_with_datum_but_no_menu_is_skipped(self) -> None:
        html = """<html><body>
        <table><thead><tr><th>Datum</th></tr></thead>
        <tbody><tr>
            <td data-label="Datum">Mo, 01.09.2026</td>
            <td data-label="Preis">0,00</td>
        </tr></tbody>
        </table></body></html>"""
        meals = parse_meals(html)
        assert meals == []


class TestParseGastroText:
    """Tests for parse_gastro_text function."""

    def test_standard_format_with_category(self) -> None:
        html = (
            "<div><b>*feelgoodfood*</b></div>"
            "<div><b>FALAFELBÄLLCHEN *VEGAN*</b></div>"
            "<div>Rote Bete | Schwarzer Reis | Zitronen-Soja-Dip</div>"
            '<div class="essalergenregion">allergens</div>'
        )
        title, ingredients = parse_gastro_text(html)
        assert title == "FALAFELBÄLLCHEN *VEGAN*"
        assert ingredients == "Rote Bete | Schwarzer Reis | Zitronen-Soja-Dip"

    def test_simple_bold_title_with_div_ingredients(self) -> None:
        html = "<b>SALATBOWL</b><div>Glasnudeln | Erdnuss-Crunch | Asia-Rettich</div>"
        title, ingredients = parse_gastro_text(html)
        assert title == "SALATBOWL"
        assert ingredients == "Glasnudeln | Erdnuss-Crunch | Asia-Rettich"

    def test_paragraph_format(self) -> None:
        html = "<p><b>FLEISCHKÜCHLE VOM RIND</b></p><p>Jus | Spätzle | Grüne Bohnen</p>"
        title, ingredients = parse_gastro_text(html)
        assert title == "FLEISCHKÜCHLE VOM RIND"
        assert ingredients == "Jus | Spätzle | Grüne Bohnen"

    def test_loose_text_ingredients(self) -> None:
        html = (
            "<div><b>PFANNENGYROS *HÄHNCHEN*</b></div>"
            "<div>Bulgur | Zaziki | Peperoni | Ajvar&nbsp;</div>"
        )
        title, ingredients = parse_gastro_text(html)
        assert title == "PFANNENGYROS *HÄHNCHEN*"
        assert ingredients == "Bulgur | Zaziki | Peperoni | Ajvar"

    def test_returns_empty_for_none(self) -> None:
        title, ingredients = parse_gastro_text(None)
        assert title == ""
        assert ingredients == ""

    def test_returns_empty_for_empty_string(self) -> None:
        title, ingredients = parse_gastro_text("")
        assert title == ""
        assert ingredients == ""

    def test_only_star_prefixed_bolds_uses_last(self) -> None:
        html = "<div><b>*special*</b></div>"
        title, _ingredients = parse_gastro_text(html)
        assert title == "*special*"

    def test_ingredients_with_newlines_collapsed(self) -> None:
        html = (
            "<div><b>SALATBOWL</b></div>"
            "<div>Glasnudeln mit Thai-Beef-Salat | Erdnuss-Crunch\n"
            " | Asia-Rettich | eingelegte gelbe Karotte</div>"
        )
        _title, ingredients = parse_gastro_text(html)
        assert "Erdnuss-Crunch | Asia-Rettich" in ingredients
        assert "\n" not in ingredients

    def test_bare_text_ingredients_outside_divs(self) -> None:
        # Real API pattern: ingredients as bare text after a div
        html = (
            "<div><b>MEDITERRANE HÄHNCHENWÜRFEL</b></div>"
            "&nbsp;Mais | Paprika | Parboiled Reis"
        )
        title, ingredients = parse_gastro_text(html)
        assert title == "MEDITERRANE HÄHNCHENWÜRFEL"
        assert "Mais | Paprika | Parboiled Reis" in ingredients

    def test_allergen_div_skipped(self) -> None:
        html = (
            '<div class="essalergenregion">allergen badges</div>'
            "<div><b>TESTMEAL</b></div>"
            "<div>Ingredients here</div>"
        )
        title, ingredients = parse_gastro_text(html)
        assert title == "TESTMEAL"
        assert ingredients == "Ingredients here"

    def test_nbsp_only_text_nodes_skipped(self) -> None:
        html = (
            "<div><b>MEAL TITLE</b></div>"
            "\xa0"
            '<div contenteditable="false"></div>'
            "Real ingredients here"
        )
        title, ingredients = parse_gastro_text(html)
        assert title == "MEAL TITLE"
        assert ingredients == "Real ingredients here"

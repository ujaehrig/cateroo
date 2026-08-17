"""Tests for cateroo.api_client module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cateroo.api_client import Booking, CaterooApiClient
from cateroo.config import Config


def _config() -> Config:
    return Config(
        cateroo_url="https://example.com",
        cateroo_user="user@test.com",
        cateroo_password="pass123",
        ics_output_path="./test.ics",
        db_path=":memory:",
        r2_bucket="my-bucket",
        r2_endpoint_url="https://abc.r2.cloudflarestorage.com",
        r2_access_key_id="fake-access-key",
        r2_secret_access_key="fake-secret-key",
        r2_object_key="cateroo.ics",
    )


class TestLogin:
    """Tests for CaterooApiClient.login."""

    @patch("cateroo.api_client.requests.Session")
    def test_login_extracts_form_fields_and_posts(
        self, mock_session_cls: MagicMock
    ) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # GET returns HTML with hidden fields
        login_html = """<html><body><form>
            <input name="__VIEWSTATE" value="abc123" />
            <input name="__EVENTVALIDATION" value="def456" />
            <input name="Login1$UserName" value="" />
            <input name="Login1$Password" value="" />
            <input name="LoginButton2" type="submit" value="" />
        </form></body></html>"""
        get_resp = MagicMock()
        get_resp.text = login_html
        get_resp.raise_for_status = MagicMock()

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()

        mock_session.get.return_value = get_resp
        mock_session.post.return_value = post_resp
        mock_session.cookies.get_dict.return_value = {
            ".ASPXAUTH": "token123",
            "ASP.NET_SessionId": "sess123",
        }

        client = CaterooApiClient(_config())
        client.login()

        # Verify POST was called with credentials but NOT LoginButton2
        call_kwargs = mock_session.post.call_args
        form_data = call_kwargs[1]["data"]
        assert form_data["Login1$UserName"] == "user@test.com"
        assert form_data["Login1$Password"] == "pass123"
        assert form_data["__VIEWSTATE"] == "abc123"
        assert "LoginButton2" not in form_data

    @patch("cateroo.api_client.requests.Session")
    def test_login_raises_on_missing_auth_cookie(
        self, mock_session_cls: MagicMock
    ) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_resp = MagicMock()
        get_resp.text = "<html><body><form></form></body></html>"
        get_resp.raise_for_status = MagicMock()

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()

        mock_session.get.return_value = get_resp
        mock_session.post.return_value = post_resp
        mock_session.cookies.get_dict.return_value = {}

        client = CaterooApiClient(_config())
        with pytest.raises(RuntimeError, match="Login failed"):
            client.login()


class TestGetBookings:
    """Tests for CaterooApiClient.get_bookings."""

    @patch("cateroo.api_client.requests.Session")
    def test_parses_bookings(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        parameter = json.dumps(
            {
                "buchungen": [
                    {
                        "bestfuer": "10.08.2026",
                        "menue": "cateroo #2",
                        "anz": 1,
                    },
                    {
                        "bestfuer": "11.08.2026",
                        "menue": "cateroo #5",
                        "anz": 1,
                    },
                    {
                        "bestfuer": "04.08.2026",
                        "menue": "cateroo #3",
                        "anz": 0,
                    },
                ]
            }
        )
        response_body = {"d": json.dumps({"success": True, "parameter": parameter})}
        resp = MagicMock()
        resp.json.return_value = response_body
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client = CaterooApiClient(_config())
        bookings = client.get_bookings("2026-08-01", "2026-08-11")

        assert len(bookings) == 2
        assert bookings[0] == Booking(
            date="2026-08-10", menu_number="cateroo #2", quantity=1
        )
        assert bookings[1] == Booking(
            date="2026-08-11", menu_number="cateroo #5", quantity=1
        )

    @patch("cateroo.api_client.requests.Session")
    def test_skips_cancelled_bookings(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        parameter = json.dumps(
            {"buchungen": [{"bestfuer": "10.08.2026", "menue": "cateroo #2", "anz": 0}]}
        )
        response_body = {"d": json.dumps({"success": True, "parameter": parameter})}
        resp = MagicMock()
        resp.json.return_value = response_body
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client = CaterooApiClient(_config())
        bookings = client.get_bookings("2026-08-01", "2026-08-11")

        assert bookings == []


class TestGetMenuOffer:
    """Tests for CaterooApiClient.get_menu_offer."""

    @patch("cateroo.api_client.requests.Session")
    def test_parses_menu_offer(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        parameter = json.dumps(
            {
                "dayoffer": [
                    {
                        "datum": "2026-08-10",
                        "menus": [
                            {
                                "name_menulinie": "cateroo #2",
                                "is_active": True,
                                "gastro_text": "<b>FALAFEL</b><div>Reis</div>",
                            },
                            {
                                "name_menulinie": "cateroo #7",
                                "is_active": False,
                                "gastro_text": None,
                            },
                        ],
                    }
                ]
            }
        )
        response_body = {"d": json.dumps({"success": True, "parameter": parameter})}
        resp = MagicMock()
        resp.json.return_value = response_body
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client = CaterooApiClient(_config())
        menu_map = client.get_menu_offer("2026-08-10", "2026-08-16")

        assert "2026-08-10|cateroo #2" in menu_map
        assert menu_map["2026-08-10|cateroo #2"] == "<b>FALAFEL</b><div>Reis</div>"
        # Inactive menus are excluded
        assert "2026-08-10|cateroo #7" not in menu_map

    @patch("cateroo.api_client.requests.Session")
    def test_handles_null_gastro_text(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        parameter = json.dumps(
            {
                "dayoffer": [
                    {
                        "datum": "2026-08-10",
                        "menus": [
                            {
                                "name_menulinie": "cateroo #1",
                                "is_active": True,
                                "gastro_text": None,
                            }
                        ],
                    }
                ]
            }
        )
        response_body = {"d": json.dumps({"success": True, "parameter": parameter})}
        resp = MagicMock()
        resp.json.return_value = response_body
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client = CaterooApiClient(_config())
        menu_map = client.get_menu_offer("2026-08-10", "2026-08-16")

        assert menu_map["2026-08-10|cateroo #1"] is None

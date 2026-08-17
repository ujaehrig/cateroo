"""Tests for cateroo.main module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from icalendar import Calendar

from cateroo.api_client import Booking
from cateroo.config import Config
from cateroo.main import main


def _config(ics_path: str = "/tmp/test_cateroo.ics") -> Config:
    return Config(
        cateroo_url="https://example.com",
        cateroo_user="user@test.com",
        cateroo_password="pass123",
        ics_output_path=ics_path,
        db_path=":memory:",
        r2_bucket="my-bucket",
        r2_endpoint_url="https://abc.r2.cloudflarestorage.com",
        r2_access_key_id="fake-access-key",
        r2_secret_access_key="fake-secret-key",
        r2_object_key="cateroo.ics",
    )


class TestMain:
    """Tests for main orchestration function."""

    @patch("cateroo.main.upload_to_r2")
    @patch("cateroo.main.CaterooApiClient")
    @patch("cateroo.main.load_config")
    def test_processes_bookings_and_writes_ics(
        self,
        mock_load_config: MagicMock,
        mock_api_cls: MagicMock,
        mock_upload: MagicMock,
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ics", delete=False) as f:
            ics_path = f.name

        mock_load_config.return_value = _config(ics_path)

        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_bookings.return_value = [
            Booking(date="2026-08-10", menu_number="cateroo #2", quantity=1),
            Booking(date="2026-08-11", menu_number="cateroo #5", quantity=1),
        ]
        mock_api.get_menu_offer.return_value = {
            "2026-08-10|cateroo #2": "<b>FALAFEL</b><div>Reis | Dip</div>",
            "2026-08-11|cateroo #5": "<b>SALATBOWL</b><div>Glasnudeln</div>",
        }

        main()

        # Verify .ics file was written
        ics_data = Path(ics_path).read_bytes()
        cal = Calendar.from_ical(ics_data)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 2
        summaries = {str(e.get("SUMMARY")) for e in events}
        assert "Lunch: FALAFEL" in summaries
        assert "Lunch: SALATBOWL" in summaries

        # Verify R2 upload was called with the ICS data
        mock_upload.assert_called_once_with(mock_load_config.return_value, ics_data)

        Path(ics_path).unlink()

    @patch("cateroo.main.upload_to_r2")
    @patch("cateroo.main.CaterooApiClient")
    @patch("cateroo.main.load_config")
    def test_no_bookings_exits_early(
        self,
        mock_load_config: MagicMock,
        mock_api_cls: MagicMock,
        mock_upload: MagicMock,
    ) -> None:
        mock_load_config.return_value = _config()

        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_bookings.return_value = []

        main()

        mock_api.get_menu_offer.assert_not_called()
        mock_upload.assert_not_called()

    @patch("cateroo.main.upload_to_r2")
    @patch("cateroo.main.CaterooApiClient")
    @patch("cateroo.main.load_config")
    def test_login_failure_exits_nonzero(
        self,
        mock_load_config: MagicMock,
        mock_api_cls: MagicMock,
        mock_upload: MagicMock,
    ) -> None:
        mock_load_config.return_value = _config()

        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_api.login.side_effect = RuntimeError("Login failed")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        mock_upload.assert_not_called()

    @patch("cateroo.main.upload_to_r2")
    @patch("cateroo.main.CaterooApiClient")
    @patch("cateroo.main.load_config")
    def test_missing_gastro_text_uses_menu_number(
        self,
        mock_load_config: MagicMock,
        mock_api_cls: MagicMock,
        mock_upload: MagicMock,
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ics", delete=False) as f:
            ics_path = f.name

        mock_load_config.return_value = _config(ics_path)

        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_bookings.return_value = [
            Booking(date="2026-08-10", menu_number="cateroo #8", quantity=1),
        ]
        mock_api.get_menu_offer.return_value = {}

        main()

        ics_data = Path(ics_path).read_bytes()
        cal = Calendar.from_ical(ics_data)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 1
        assert str(events[0].get("SUMMARY")) == "Lunch: cateroo #8"

        mock_upload.assert_called_once()

        Path(ics_path).unlink()

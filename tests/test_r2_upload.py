"""Tests for cateroo.r2_upload module."""

from unittest.mock import MagicMock, patch

from cateroo.config import Config
from cateroo.r2_upload import upload_to_r2


def _config() -> Config:
    return Config(
        cateroo_url="https://example.com",
        cateroo_user="user@test.com",
        cateroo_password="pass123",
        ics_output_path="/tmp/test.ics",
        db_path=":memory:",
        r2_bucket="my-bucket",
        r2_endpoint_url="https://abc123.r2.cloudflarestorage.com",
        r2_access_key_id="fake-access-key",
        r2_secret_access_key="fake-secret-key",
        r2_object_key="cateroo.ics",
    )


class TestUploadToR2:
    """Tests for upload_to_r2 function."""

    @patch("cateroo.r2_upload.boto3.client")
    def test_uploads_ics_data_with_correct_params(
        self,
        mock_boto3_client: MagicMock,
    ) -> None:
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        config = _config()
        ics_data = b"BEGIN:VCALENDAR\nEND:VCALENDAR"

        upload_to_r2(config, ics_data)

        mock_boto3_client.assert_called_once_with(
            "s3",
            endpoint_url="https://abc123.r2.cloudflarestorage.com",
            aws_access_key_id="fake-access-key",
            aws_secret_access_key="fake-secret-key",
        )
        mock_s3.put_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="cateroo.ics",
            Body=ics_data,
            ContentType="text/calendar",
        )

    @patch("cateroo.r2_upload.boto3.client")
    def test_uses_custom_object_key(
        self,
        mock_boto3_client: MagicMock,
    ) -> None:
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        config = Config(
            cateroo_url="https://example.com",
            cateroo_user="user@test.com",
            cateroo_password="pass123",
            ics_output_path="/tmp/test.ics",
            db_path=":memory:",
            r2_bucket="my-bucket",
            r2_endpoint_url="https://abc123.r2.cloudflarestorage.com",
            r2_access_key_id="fake-access-key",
            r2_secret_access_key="fake-secret-key",
            r2_object_key="calendar/lunch.ics",
        )
        ics_data = b"BEGIN:VCALENDAR\nEND:VCALENDAR"

        upload_to_r2(config, ics_data)

        mock_s3.put_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="calendar/lunch.ics",
            Body=ics_data,
            ContentType="text/calendar",
        )

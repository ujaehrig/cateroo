"""Upload ICS file to Cloudflare R2 storage."""

import logging

import boto3

from cateroo.config import Config

logger = logging.getLogger(__name__)


def upload_to_r2(config: Config, ics_data: bytes) -> None:
    """Upload ICS bytes to Cloudflare R2.

    Uses the S3-compatible API with the configured endpoint,
    credentials, bucket, and object key.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=config.r2_endpoint_url,
        aws_access_key_id=config.r2_access_key_id,
        aws_secret_access_key=config.r2_secret_access_key,
    )

    s3.put_object(
        Bucket=config.r2_bucket,
        Key=config.r2_object_key,
        Body=ics_data,
        ContentType="text/calendar",
    )

    logger.info(
        "Uploaded %d bytes to R2 bucket '%s' as '%s'",
        len(ics_data),
        config.r2_bucket,
        config.r2_object_key,
    )

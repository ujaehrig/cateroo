"""Configuration loading from .env file."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    cateroo_url: str
    cateroo_user: str
    cateroo_password: str
    ics_output_path: str
    db_path: str
    r2_bucket: str
    r2_endpoint_url: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_object_key: str


def _require_env(name: str) -> str:
    """Get a required environment variable or raise ValueError."""
    value = os.environ.get(name)
    if not value:
        msg = f"Missing required environment variable: {name}"
        raise ValueError(msg)
    return value


def load_config() -> Config:
    """Load configuration from environment variables.

    Calls load_dotenv() to load .env file if present.
    Raises ValueError if required variables are missing.
    """
    load_dotenv()

    return Config(
        cateroo_url=_require_env("CATEROO_URL"),
        cateroo_user=_require_env("CATEROO_USER"),
        cateroo_password=_require_env("CATEROO_PASSWORD"),
        ics_output_path=os.environ.get("ICS_OUTPUT_PATH", "./cateroo.ics"),
        db_path=os.environ.get("DB_PATH", "./cateroo.db"),
        r2_bucket=_require_env("R2_BUCKET"),
        r2_endpoint_url=_require_env("R2_ENDPOINT_URL"),
        r2_access_key_id=_require_env("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_require_env("R2_SECRET_ACCESS_KEY"),
        r2_object_key=os.environ.get("R2_OBJECT_KEY", "cateroo.ics"),
    )

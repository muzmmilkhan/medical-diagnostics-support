import logging
from pathlib import Path

import boto3

from app.core.config import Settings

logger = logging.getLogger(__name__)


class S3StorageService:
    def __init__(self, bucket: str, client) -> None:
        self._bucket = bucket
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "S3StorageService | None":
        """Return a storage service, or None when no bucket is configured."""
        if not settings.s3_bucket_name:
            return None
        # Falls back to boto3's default credential chain (env, profile, IAM role) when unset.
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=(
                settings.aws_secret_access_key.get_secret_value()
                if settings.aws_secret_access_key
                else None
            ),
            region_name=settings.aws_region,
        )
        return cls(settings.s3_bucket_name, client)

    def upload(self, content: bytes, filename: str) -> str:
        key = f"uploads/{Path(filename).name}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        logger.info("Uploaded %s to s3://%s/%s", filename, self._bucket, key)
        return key

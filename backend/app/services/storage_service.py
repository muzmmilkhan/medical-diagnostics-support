"""Save the original uploaded file to S3 (only if S3_BUCKET_NAME is set)."""

import boto3

from app.config import Config


class S3Storage:
    def __init__(self):
        self.bucket = Config.S3_BUCKET_NAME
        self.s3 = boto3.client("s3", region_name=Config.AWS_REGION) if self.bucket else None

    def upload(self, content: bytes, filename: str) -> bool:
        if not self.s3:
            return False
        self.s3.put_object(Bucket=self.bucket, Key=f"uploads/{filename}", Body=content)
        return True

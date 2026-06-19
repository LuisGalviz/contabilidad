from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

from src.config import get_settings

settings = get_settings()


def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_s3_endpoint_url or None,
        aws_access_key_id=settings.storage_s3_access_key or None,
        aws_secret_access_key=settings.storage_s3_secret_key or None,
        config=Config(signature_version="s3v4"),
        region_name=settings.storage_s3_region,
    )


def _ensure_bucket() -> None:
    s3 = _client()
    try:
        s3.head_bucket(Bucket=settings.storage_s3_bucket)
    except Exception:
        s3.create_bucket(Bucket=settings.storage_s3_bucket)


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    _ensure_bucket()
    _client().put_object(
        Bucket=settings.storage_s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def get_presigned_url(key: str, expires: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_s3_bucket, "Key": key},
        ExpiresIn=expires,
    )


def download_bytes(key: str) -> bytes:
    response = _client().get_object(Bucket=settings.storage_s3_bucket, Key=key)
    return response["Body"].read()

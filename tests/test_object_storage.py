from __future__ import annotations

from pathlib import Path

import pytest

from backend.config import Settings, validate_settings
from backend.services.object_storage import AliyunOssObjectStorage, LocalObjectStorage

pytestmark = pytest.mark.infra


def test_local_object_storage_writes_upload(tmp_path: Path) -> None:
    storage = LocalObjectStorage(str(tmp_path), "uploads", "/storage")

    stored = storage.store_upload("images", "../hello world.png", b"image", "image/png")

    assert stored.storage_provider == "local"
    assert stored.file_name == "../hello world.png"
    assert stored.public_url.startswith("/storage/uploads/images/")
    assert stored.public_url.endswith("_hello_world.png")
    assert Path(stored.local_path).read_bytes() == b"image"


def test_aliyun_oss_public_url_uses_bucket_endpoint() -> None:
    storage = AliyunOssObjectStorage.__new__(AliyunOssObjectStorage)
    storage._public_base_url = ""
    storage._endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
    storage._bucket_name = "jiandouai"

    assert (
        storage.public_url("prod/uploads/images/a b.png")
        == "https://jiandouai.oss-cn-hangzhou.aliyuncs.com/prod/uploads/images/a%20b.png"
    )


def test_aliyun_oss_put_object_applies_key_prefix_once() -> None:
    class _Bucket:
        def __init__(self) -> None:
            self.keys: list[str] = []

        def put_object(self, key: str, content: bytes, headers=None) -> None:
            self.keys.append(key)

    bucket = _Bucket()
    storage = AliyunOssObjectStorage.__new__(AliyunOssObjectStorage)
    storage._bucket = bucket
    storage._public_base_url = "https://cdn.example.test"
    storage._key_prefix = "dev"

    stored = storage.put_object("uploads/texts/a.txt", b"hello", "text/plain", "a.txt")
    prefixed = storage.put_object("dev/uploads/texts/b.txt", b"hello", "text/plain", "b.txt")

    assert stored.storage_key == "dev/uploads/texts/a.txt"
    assert stored.public_url == "https://cdn.example.test/dev/uploads/texts/a.txt"
    assert prefixed.storage_key == "dev/uploads/texts/b.txt"
    assert bucket.keys == ["dev/uploads/texts/a.txt", "dev/uploads/texts/b.txt"]


def test_aliyun_oss_settings_require_credentials() -> None:
    settings = Settings(
        storage_backend="aliyun_oss",
        aliyun_oss_endpoint="",
        aliyun_oss_bucket="jiandouai",
        aliyun_oss_access_key_id="",
        aliyun_oss_access_key_secret="",
    )

    errors = [issue.field for issue in validate_settings(settings) if issue.severity == "error"]

    assert "aliyun_oss_endpoint" in errors
    assert "aliyun_oss_access_key_id" in errors
    assert "aliyun_oss_access_key_secret" in errors

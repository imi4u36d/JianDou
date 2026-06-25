"""Upload-oriented object storage adapters."""

from __future__ import annotations

import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

from backend.config import Settings


@dataclass(frozen=True)
class StoredObject:
    asset_id: str
    file_name: str
    storage_provider: str
    storage_key: str
    public_url: str
    size_bytes: int
    local_path: str = ""


class LocalObjectStorage:
    def __init__(self, storage_root: str, uploads_dir: str, public_base_url: str = "") -> None:
        self._storage_root = Path(storage_root).resolve()
        self._uploads_dir = _clean_path_prefix(uploads_dir) or "uploads"
        self._public_base_url = (public_base_url or "/storage").rstrip("/")

    def store_upload(
        self,
        media_type: str,
        file_name: str,
        content: bytes,
        content_type: str = "",
    ) -> StoredObject:
        safe_name = _safe_file_name(file_name, content_type)
        asset_id = f"asset_{uuid.uuid4().hex}"
        storage_key = f"{self._uploads_dir}/{_safe_segment(media_type)}/{asset_id}_{safe_name}"
        stored = self.put_object(storage_key, content, content_type, file_name or safe_name)
        return StoredObject(
            asset_id=asset_id,
            file_name=file_name or safe_name,
            storage_provider=stored.storage_provider,
            storage_key=stored.storage_key,
            public_url=stored.public_url,
            size_bytes=stored.size_bytes,
            local_path=stored.local_path,
        )

    def put_object(
        self,
        storage_key: str,
        content: bytes,
        content_type: str = "",
        file_name: str = "",
    ) -> StoredObject:
        key = _clean_storage_key(storage_key)
        path = (self._storage_root / key).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(
            asset_id="",
            file_name=file_name or Path(key).name,
            storage_provider="local",
            storage_key=key,
            public_url=_join_url(self._public_base_url, key),
            size_bytes=len(content),
            local_path=str(path),
        )


class AliyunOssObjectStorage:
    def __init__(
        self,
        endpoint: str,
        bucket_name: str,
        access_key_id: str,
        access_key_secret: str,
        security_token: str = "",
        key_prefix: str = "",
        uploads_dir: str = "uploads",
        public_base_url: str = "",
    ) -> None:
        if not endpoint or not bucket_name or not access_key_id or not access_key_secret:
            raise RuntimeError("Aliyun OSS storage requires endpoint, bucket, access key id and access key secret")

        try:
            import oss2
        except ImportError as ex:  # pragma: no cover - dependency is declared in pyproject
            raise RuntimeError("Aliyun OSS storage requires the 'oss2' package") from ex

        auth = (
            oss2.StsAuth(access_key_id, access_key_secret, security_token)
            if security_token
            else oss2.Auth(access_key_id, access_key_secret)
        )
        self._bucket = oss2.Bucket(auth, endpoint, bucket_name)
        self._endpoint = endpoint
        self._bucket_name = bucket_name
        self._uploads_dir = _clean_path_prefix(uploads_dir) or "uploads"
        self._key_prefix = _clean_path_prefix(key_prefix)
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else ""

    def store_upload(
        self,
        media_type: str,
        file_name: str,
        content: bytes,
        content_type: str = "",
    ) -> StoredObject:
        safe_name = _safe_file_name(file_name, content_type)
        asset_id = f"asset_{uuid.uuid4().hex}"
        key_parts = [self._uploads_dir, _safe_segment(media_type), f"{asset_id}_{safe_name}"]
        storage_key = "/".join(part for part in key_parts if part)
        stored = self.put_object(storage_key, content, content_type, file_name or safe_name)
        return StoredObject(
            asset_id=asset_id,
            file_name=file_name or safe_name,
            storage_provider=stored.storage_provider,
            storage_key=stored.storage_key,
            public_url=stored.public_url,
            size_bytes=stored.size_bytes,
        )

    def put_object(
        self,
        storage_key: str,
        content: bytes,
        content_type: str = "",
        file_name: str = "",
    ) -> StoredObject:
        key = self._prefixed_storage_key(storage_key)
        headers = {"Content-Type": content_type} if content_type else None
        self._bucket.put_object(key, content, headers=headers)
        return StoredObject(
            asset_id="",
            file_name=file_name or Path(key).name,
            storage_provider="aliyun_oss",
            storage_key=key,
            public_url=self.public_url(key),
            size_bytes=len(content),
        )

    def _prefixed_storage_key(self, storage_key: str) -> str:
        key = _clean_storage_key(storage_key)
        if not self._key_prefix:
            return key
        if key == self._key_prefix or key.startswith(f"{self._key_prefix}/"):
            return key
        return f"{self._key_prefix}/{key}" if key else self._key_prefix

    def public_url(self, storage_key: str) -> str:
        if self._public_base_url:
            return _join_url(self._public_base_url, storage_key)
        parsed = urlparse(self._endpoint if "://" in self._endpoint else f"https://{self._endpoint}")
        host = parsed.netloc or parsed.path
        scheme = parsed.scheme or "https"
        return f"{scheme}://{self._bucket_name}.{host.rstrip('/')}/{quote(storage_key, safe='/')}"


def create_upload_storage(settings: Settings):
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "aliyun_oss":
        return AliyunOssObjectStorage(
            endpoint=settings.aliyun_oss_endpoint,
            bucket_name=settings.aliyun_oss_bucket,
            access_key_id=settings.aliyun_oss_access_key_id,
            access_key_secret=settings.aliyun_oss_access_key_secret,
            security_token=settings.aliyun_oss_security_token,
            key_prefix=settings.aliyun_oss_key_prefix,
            uploads_dir=settings.uploads_dir,
            public_base_url=settings.storage_public_base_url,
        )
    return LocalObjectStorage(
        storage_root=settings.storage_root,
        uploads_dir=settings.uploads_dir,
        public_base_url=settings.storage_public_base_url or "/storage",
    )


def create_remote_object_storage(settings: Settings):
    backend = (settings.storage_backend or "local").strip().lower()
    if backend != "aliyun_oss":
        return None
    return AliyunOssObjectStorage(
        endpoint=settings.aliyun_oss_endpoint,
        bucket_name=settings.aliyun_oss_bucket,
        access_key_id=settings.aliyun_oss_access_key_id,
        access_key_secret=settings.aliyun_oss_access_key_secret,
        security_token=settings.aliyun_oss_security_token,
        key_prefix=settings.aliyun_oss_key_prefix,
        uploads_dir=settings.uploads_dir,
        public_base_url=settings.storage_public_base_url,
    )


def _safe_file_name(file_name: str, content_type: str = "") -> str:
    candidate = Path((file_name or "").replace("\\", "/")).name.strip()
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    if candidate:
        return candidate[:160]
    extension = mimetypes.guess_extension(content_type or "") or ".bin"
    return f"upload{extension}"


def _safe_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9_-]+", "-", (value or "").strip().lower()).strip("-")
    return segment or "files"


def _clean_path_prefix(value: str) -> str:
    return "/".join(part for part in (value or "").replace("\\", "/").split("/") if part and part != ".")


def _clean_storage_key(value: str) -> str:
    return _clean_path_prefix(value)


def _join_url(base_url: str, storage_key: str) -> str:
    return f"{base_url.rstrip('/')}/{quote(storage_key.lstrip('/'), safe='/')}"

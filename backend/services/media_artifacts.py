"""Artifact value objects shared by local media collaborators."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    mime_type: str


@dataclass
class ImageArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    width: int
    height: int
    mime_type: str


@dataclass
class VideoArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    width: int
    height: int
    duration_seconds: int
    has_audio: bool
    mime_type: str


@dataclass
class StoredArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int

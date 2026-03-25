from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UploadResponse(BaseModel):
    assetId: str
    fileName: str
    fileUrl: str
    sizeBytes: int


class CreateTaskRequest(BaseModel):
    title: str
    sourceAssetId: str
    sourceFileName: str
    platform: str
    aspectRatio: str = Field(pattern="^(9:16|16:9)$")
    minDurationSeconds: int = Field(ge=1)
    maxDurationSeconds: int = Field(ge=1)
    outputCount: int = Field(ge=1, le=10)
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None


class TaskOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clipIndex: int
    title: str
    reason: str
    startSeconds: float
    endSeconds: float
    durationSeconds: float
    previewUrl: str
    downloadUrl: str


class TaskListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: TaskStatus
    platform: str
    progress: int
    outputCount: int
    createdAt: str
    updatedAt: str


class TaskDetail(TaskListItem):
    sourceFileName: str
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None
    errorMessage: str | None = None
    outputs: list[TaskOutput] = Field(default_factory=list)


class ClipPlan(BaseModel):
    clipIndex: int
    title: str
    reason: str
    startSeconds: float
    endSeconds: float
    durationSeconds: float


class MediaProbe(BaseModel):
    durationSeconds: float
    width: int
    height: int
    hasAudio: bool
    fps: float | None = None


class TaskSpec(BaseModel):
    title: str
    platform: str
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    outputCount: int
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None

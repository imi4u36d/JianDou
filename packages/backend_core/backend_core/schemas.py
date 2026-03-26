from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    sourceAssetId: str | None = None
    sourceAssetIds: list[str] = Field(default_factory=list)
    sourceFileName: str | None = None
    sourceFileNames: list[str] = Field(default_factory=list)
    editingMode: Literal["drama", "mixcut"] = "drama"
    mixcutEnabled: bool | None = None
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None
    platform: str
    aspectRatio: str = Field(pattern="^(9:16|16:9)$")
    minDurationSeconds: int = Field(ge=1)
    maxDurationSeconds: int = Field(ge=1)
    outputCount: int = Field(ge=1, le=10)
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None
    transcriptText: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_mode(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        editing_mode = str(payload.get("editingMode") or "").strip()
        legacy_mixcut = payload.get("mixcutEnabled")
        if not editing_mode:
            payload["editingMode"] = "mixcut" if legacy_mixcut else "drama"
        return payload

    @model_validator(mode="after")
    def _validate_sources(self) -> "CreateTaskRequest":
        self.editingMode = "mixcut" if self.editingMode == "mixcut" else "drama"
        self.mixcutEnabled = self.editingMode == "mixcut"
        source_ids = [item.strip() for item in self.sourceAssetIds if item and item.strip()]
        if self.sourceAssetId and self.sourceAssetId.strip():
            source_ids = [self.sourceAssetId.strip(), *[item for item in source_ids if item != self.sourceAssetId.strip()]]
        if not source_ids:
            raise ValueError("at least one source asset is required")
        if self.editingMode == "mixcut" and len(source_ids) < 2:
            raise ValueError("editingMode=mixcut requires at least two source assets")
        if self.editingMode == "drama" and len(source_ids) > 1:
            raise ValueError("editingMode=drama supports only one source asset")
        if self.editingMode == "mixcut" and not (self.mixcutContentType or "").strip():
            self.mixcutContentType = "generic"
        if self.editingMode == "mixcut" and not (self.mixcutStylePreset or "").strip():
            self.mixcutStylePreset = "director"
        if self.sourceFileName and self.sourceFileName.strip() and not self.sourceFileNames:
            self.sourceFileNames = [self.sourceFileName.strip()]
        if self.sourceFileNames and len(self.sourceFileNames) not in {1, len(source_ids)}:
            raise ValueError("sourceFileNames must contain one item or match sourceAssetIds length")
        self.sourceAssetIds = source_ids
        self.sourceAssetId = source_ids[0]
        return self


class GenerateCreativePromptRequest(BaseModel):
    title: str
    platform: str
    aspectRatio: str = Field(pattern="^(9:16|16:9)$")
    minDurationSeconds: int = Field(ge=1)
    maxDurationSeconds: int = Field(ge=1)
    outputCount: int = Field(ge=1, le=10)
    introTemplate: str
    outroTemplate: str
    sourceFileNames: list[str] = Field(default_factory=list)
    editingMode: Literal["drama", "mixcut"] = "drama"
    mixcutEnabled: bool | None = None
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None
    transcriptText: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_mode(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        editing_mode = str(payload.get("editingMode") or "").strip()
        legacy_mixcut = payload.get("mixcutEnabled")
        if not editing_mode:
            payload["editingMode"] = "mixcut" if legacy_mixcut else "drama"
        return payload

    @model_validator(mode="after")
    def _normalize_mode(self) -> "GenerateCreativePromptRequest":
        self.editingMode = "mixcut" if self.editingMode == "mixcut" else "drama"
        self.mixcutEnabled = self.editingMode == "mixcut"
        if self.editingMode == "mixcut" and not (self.mixcutContentType or "").strip():
            self.mixcutContentType = "generic"
        if self.editingMode == "mixcut" and not (self.mixcutStylePreset or "").strip():
            self.mixcutStylePreset = "director"
        return self


class GenerateCreativePromptResponse(BaseModel):
    prompt: str
    source: str


class SourceAssetSummary(BaseModel):
    assetId: str
    originalFileName: str
    storedFileName: str
    fileUrl: str
    mimeType: str | None = None
    sizeBytes: int
    sha256: str | None = None
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    hasAudio: bool
    createdAt: str
    updatedAt: str


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


class TaskTraceEvent(BaseModel):
    timestamp: str
    level: str
    stage: str
    event: str
    message: str
    payload: dict[str, object] = Field(default_factory=dict)


class TaskDeleteResult(BaseModel):
    taskId: str
    deleted: bool = True


class ClipSegment(BaseModel):
    sourceAssetId: str
    sourceFileName: str
    startSeconds: float
    endSeconds: float
    durationSeconds: float
    segmentKind: str | None = None
    frameTimestampSeconds: float | None = None
    segmentRole: str | None = None


class AdminOverviewCounts(BaseModel):
    totalTasks: int
    queuedTasks: int
    runningTasks: int
    completedTasks: int
    failedTasks: int
    semanticTasks: int
    timedSemanticTasks: int
    averageProgress: int


class AdminOverview(BaseModel):
    generatedAt: str
    counts: AdminOverviewCounts
    modelReady: bool
    primaryModel: str
    visionModel: str | None = None
    recentTasks: list["TaskListItem"] = Field(default_factory=list)
    recentFailures: list["TaskListItem"] = Field(default_factory=list)
    recentRunningTasks: list["TaskListItem"] = Field(default_factory=list)
    recentTraceCount: int = 0


class AdminTraceEvent(TaskTraceEvent):
    taskId: str
    taskTitle: str | None = None
    taskStatus: str | None = None


class AdminTaskBatchRequest(BaseModel):
    taskIds: list[str] = Field(min_length=1, max_length=100)


class AdminTaskActionFailure(BaseModel):
    taskId: str
    reason: str


class AdminTaskBatchResult(BaseModel):
    action: Literal["retry", "delete"]
    requestedCount: int
    succeededTaskIds: list[str] = Field(default_factory=list)
    failed: list[AdminTaskActionFailure] = Field(default_factory=list)


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
    sourceFileName: str
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    retryCount: int = 0
    startedAt: str | None = None
    finishedAt: str | None = None
    completedOutputCount: int = 0
    hasTranscript: bool = False
    hasTimedTranscript: bool = False
    sourceAssetCount: int = 1
    editingMode: Literal["drama", "mixcut"] = "drama"
    mixcutEnabled: bool = False


class TaskDraft(BaseModel):
    sourceTaskId: str
    sourceAssetId: str
    sourceAssetIds: list[str] = Field(default_factory=list)
    sourceFileName: str
    sourceFileNames: list[str] = Field(default_factory=list)
    sourceAssetCount: int = 1
    editingMode: Literal["drama", "mixcut"] = "drama"
    mixcutEnabled: bool = False
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None
    mixcutTransitionStyle: str | None = None
    mixcutLayoutStyle: str | None = None
    mixcutEffectStyle: str | None = None
    mixcutTemplate: str | None = None
    title: str
    platform: str
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    outputCount: int
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None
    transcriptText: str | None = None
    hasTimedTranscript: bool = False
    transcriptCueCount: int = 0
    source: SourceAssetSummary | None = None
    sourceAssets: list[SourceAssetSummary] = Field(default_factory=list)


class TaskDetail(TaskListItem):
    sourceFileName: str
    sourceFileNames: list[str] = Field(default_factory=list)
    sourceAssetIds: list[str] = Field(default_factory=list)
    mixcutEnabled: bool = False
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None
    mixcutTransitionStyle: str | None = None
    mixcutLayoutStyle: str | None = None
    mixcutEffectStyle: str | None = None
    mixcutTemplate: str | None = None
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None
    errorMessage: str | None = None
    startedAt: str | None = None
    finishedAt: str | None = None
    retryCount: int = 0
    completedOutputCount: int = 0
    transcriptPreview: str | None = None
    hasTranscript: bool = False
    hasTimedTranscript: bool = False
    transcriptCueCount: int = 0
    source: SourceAssetSummary | None = None
    sourceAssets: list[SourceAssetSummary] = Field(default_factory=list)
    plan: list[ClipPlan] = Field(default_factory=list)
    outputs: list[TaskOutput] = Field(default_factory=list)


class ClipPlan(BaseModel):
    clipIndex: int
    title: str
    reason: str
    startSeconds: float
    endSeconds: float
    durationSeconds: float
    sourceAssetId: str | None = None
    sourceFileName: str | None = None
    segments: list[ClipSegment] = Field(default_factory=list)
    transitionStyle: str | None = None
    layoutStyle: str | None = None
    effectStyle: str | None = None
    mixcutTemplate: str | None = None


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
    sourceAssetIds: list[str] = Field(default_factory=list)
    sourceFileNames: list[str] = Field(default_factory=list)
    editingMode: Literal["drama", "mixcut"] = "drama"
    mixcutEnabled: bool = False
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None
    mixcutTransitionStyle: str | None = None
    mixcutLayoutStyle: str | None = None
    mixcutEffectStyle: str | None = None
    mixcutTemplate: str | None = None
    creativePrompt: str | None = None
    transcriptText: str | None = None

    @model_validator(mode="after")
    def _normalize_mode(self) -> "TaskSpec":
        self.editingMode = "mixcut" if self.editingMode == "mixcut" else "drama"
        self.mixcutEnabled = self.editingMode == "mixcut"
        return self


class TaskPreset(BaseModel):
    key: str
    name: str
    description: str
    defaultTitle: str
    editingMode: Literal["drama", "mixcut"] = "drama"
    platform: str
    aspectRatio: str
    minDurationSeconds: int
    maxDurationSeconds: int
    outputCount: int
    introTemplate: str
    outroTemplate: str
    creativePrompt: str | None = None
    mixcutContentType: str | None = None
    mixcutStylePreset: str | None = None

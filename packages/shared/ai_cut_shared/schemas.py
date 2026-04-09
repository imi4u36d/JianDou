from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PAUSED = "PAUSED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskType(str, Enum):
    GENERATION = "generation"


class TaskStage(str, Enum):
    API = "api"
    DISPATCH = "dispatch"
    PIPELINE = "pipeline"
    TASK = "task"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RENDER = "render"
    GENERATION = "generation"
    SYSTEM = "system"
    USAGE = "usage"


class TaskOperationKind(str, Enum):
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RENDER = "render"
    PIPELINE = "pipeline"
    DISPATCH = "dispatch"
    GENERATION_VIDEO = "generation.video"
    GENERATION_IMAGE = "generation.image"
    GENERATION_SCRIPT = "generation.script"
    SYSTEM = "system"


class EditingMode(str, Enum):
    DRAMA = "drama"


class MaterialKind(str, Enum):
    SOURCE = "source"
    OUTPUT = "output"
    INTERMEDIATE = "intermediate"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    OTHER = "other"


class TraceLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class TaskModelCallStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


class UploadResponse(BaseModel):
    assetId: str
    fileName: str
    fileUrl: str
    sizeBytes: int


class CreateGenerationTaskRequest(BaseModel):
    taskType: TaskType = TaskType.GENERATION
    title: str
    creativePrompt: str | None = None
    platform: str = "douyin"
    aspectRatio: str = Field(pattern="^(9:16|16:9)$")
    textAnalysisModel: str | None = None
    videoModel: str | None = None
    videoSize: str | None = None
    videoDurationSeconds: int | Literal["auto"] | None = None
    minDurationSeconds: int | None = Field(default=None, ge=1, le=120)
    maxDurationSeconds: int | None = Field(default=None, ge=1, le=120)
    transcriptText: str | None = None
    stopBeforeVideoGeneration: bool | None = False

    @field_validator("videoDurationSeconds", mode="before")
    @classmethod
    def _normalize_video_duration_seconds(cls, value: object) -> int | Literal["auto"] | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return None
            if normalized == "auto":
                return "auto"
            raw_value: object = normalized
        else:
            raw_value = value
        if isinstance(raw_value, bool):
            raise ValueError("videoDurationSeconds must be integer seconds or 'auto'")
        try:
            numeric = float(raw_value)
        except Exception as exc:
            raise ValueError("videoDurationSeconds must be integer seconds or 'auto'") from exc
        if not numeric.is_integer():
            raise ValueError("videoDurationSeconds must be integer seconds")
        seconds = int(numeric)
        if seconds < 1 or seconds > 120:
            raise ValueError("videoDurationSeconds must be between 1 and 120")
        return seconds

    @model_validator(mode="after")
    def _normalize(self) -> "CreateGenerationTaskRequest":
        self.taskType = TaskType.GENERATION
        self.title = self.title.strip()
        self.creativePrompt = (self.creativePrompt or "").strip() or None
        if not self.title:
            raise ValueError("title is required")
        self.platform = (self.platform or "").strip() or "douyin"
        if isinstance(self.videoDurationSeconds, int):
            self.minDurationSeconds = self.videoDurationSeconds
            self.maxDurationSeconds = self.videoDurationSeconds
        if self.videoDurationSeconds != "auto" and (self.minDurationSeconds is None or self.maxDurationSeconds is None):
            raise ValueError("videoDurationSeconds is required")
        if (
            self.minDurationSeconds is not None
            and self.maxDurationSeconds is not None
            and self.minDurationSeconds > self.maxDurationSeconds
        ):
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")
        self.textAnalysisModel = (self.textAnalysisModel or "").strip() or None
        self.videoModel = (self.videoModel or "").strip() or None
        self.videoSize = (self.videoSize or "").strip() or None
        self.transcriptText = (self.transcriptText or "").strip() or None
        self.stopBeforeVideoGeneration = bool(self.stopBeforeVideoGeneration)
        return self

class GenerateCreativePromptRequest(BaseModel):
    title: str
    platform: str = "douyin"
    aspectRatio: str = Field(pattern="^(9:16|16:9)$")
    minDurationSeconds: int = Field(ge=1)
    maxDurationSeconds: int = Field(ge=1)
    introTemplate: str
    outroTemplate: str
    sourceFileNames: list[str] = Field(default_factory=list)
    editingMode: EditingMode = EditingMode.DRAMA
    transcriptText: str | None = None

    @model_validator(mode="after")
    def _normalize_mode(self) -> "GenerateCreativePromptRequest":
        self.platform = (self.platform or "").strip() or "douyin"
        self.editingMode = EditingMode.DRAMA
        return self

class GenerateCreativePromptResponse(BaseModel):
    prompt: str
    source: str


class GenerateTextScriptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_000_000)
    visualStyle: str | None = Field(default=None, max_length=120)
    textAnalysisModel: str | None = Field(default=None, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def _migrate_aliases(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "textAnalysisModel" not in payload:
            payload["textAnalysisModel"] = (
                payload.get("text_model")
                or payload.get("textModel")
                or payload.get("analysisModel")
                or payload.get("model")
                or payload.get("modelName")
            )
        return payload

    @field_validator("text", mode="after")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must be non-empty")
        return normalized

    @field_validator("visualStyle", mode="after")
    @classmethod
    def _normalize_visual_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("textAnalysisModel", mode="after")
    @classmethod
    def _normalize_text_analysis_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GenerateTextScriptResponse(BaseModel):
    id: str
    sourceText: str
    visualStyle: str
    outputFormat: Literal["markdown"] = "markdown"
    scriptMarkdown: str
    markdownFilePath: str | None = None
    markdownFileUrl: str | None = None
    downloadUrl: str | None = None
    source: str
    createdAt: str
    modelInfo: dict[str, object] = Field(default_factory=dict)
    callChain: list[dict[str, object]] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ProbeTextAnalysisModelRequest(BaseModel):
    textAnalysisModel: str | None = Field(default=None, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def _migrate_aliases(cls, data):
        if isinstance(data, str):
            return {"textAnalysisModel": data}
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "textAnalysisModel" not in payload:
            payload["textAnalysisModel"] = (
                payload.get("text_model")
                or payload.get("textModel")
                or payload.get("analysisModel")
                or payload.get("model")
                or payload.get("modelName")
            )
        return payload

    @field_validator("textAnalysisModel", mode="after")
    @classmethod
    def _normalize_text_analysis_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProbeTextAnalysisModelResponse(BaseModel):
    ready: bool = True
    requestedModel: str
    resolvedModel: str
    provider: str
    family: str | None = None
    mode: str
    endpointHost: str
    latencyMs: int = Field(ge=0)
    messagePreview: str | None = None
    checkedAt: str


class TextMediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class GenerationMediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class GenerateTextMediaRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    kind: TextMediaKind
    providerModel: str | None = Field(default=None, max_length=120)
    textAnalysisModel: str | None = Field(default=None, max_length=120)
    videoModel: str | None = Field(default=None, max_length=120)
    videoSize: str | None = Field(default=None, max_length=32)
    width: int = Field(default=1024, ge=256, le=4096)
    height: int = Field(default=1024, ge=256, le=4096)
    durationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
    minDurationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
    maxDurationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
    stylePreset: str | None = Field(default=None, max_length=120)
    extras: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt", mode="after")
    @classmethod
    def _validate_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must be non-empty")
        return normalized

    @field_validator("stylePreset", mode="after")
    @classmethod
    def _normalize_style_preset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("providerModel", "textAnalysisModel", "videoModel", mode="after")
    @classmethod
    def _normalize_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("videoSize", mode="after")
    @classmethod
    def _normalize_video_size(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().replace("x", "*")
        return normalized or None

    @model_validator(mode="after")
    def _validate_constraints(self) -> "GenerateTextMediaRequest":
        pixels = self.width * self.height
        if pixels > 8_294_400:
            raise ValueError("output dimensions are too large")
        if self.kind == TextMediaKind.IMAGE and any(
            value is not None for value in (self.durationSeconds, self.minDurationSeconds, self.maxDurationSeconds)
        ):
            raise ValueError("duration constraints are only allowed for video generation")
        if self.kind == TextMediaKind.VIDEO and self.durationSeconds is not None:
            if self.minDurationSeconds is None:
                self.minDurationSeconds = self.durationSeconds
            if self.maxDurationSeconds is None:
                self.maxDurationSeconds = self.durationSeconds
        if (
            self.kind == TextMediaKind.VIDEO
            and self.minDurationSeconds is not None
            and self.maxDurationSeconds is not None
            and self.minDurationSeconds > self.maxDurationSeconds
        ):
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")
        return self


class GenerateTextMediaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    kind: TextMediaKind | None = None
    prompt: str | None = None
    outputUrl: str | None = None
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    status: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class GenerationVersionInfo(BaseModel):
    version: int = Field(ge=1, le=10)
    label: str
    isDefault: bool = False
    supportedKinds: list[TextMediaKind] = Field(default_factory=list)
    description: str | None = None


class GenerationTextAnalysisModelInfo(BaseModel):
    value: str
    label: str
    description: str | None = None
    isDefault: bool = False
    provider: str | None = None
    family: str | None = None
    aliases: list[str] = Field(default_factory=list)


class GenerationStylePresetOption(BaseModel):
    key: str
    label: str
    description: str | None = None
    mediaKinds: list[TextMediaKind] = Field(default_factory=list)


class GenerationImageSizeOption(BaseModel):
    value: str
    label: str
    width: int | None = None
    height: int | None = None


class GenerationVideoModelInfo(BaseModel):
    value: str
    label: str
    description: str | None = None
    isDefault: bool = False
    supportedSizes: list[str] = Field(default_factory=list)
    supportedDurations: list[int] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class GenerationVideoModelOption(GenerationVideoModelInfo):
    pass


class GenerationVideoSizeOption(BaseModel):
    value: str
    label: str
    width: int | None = None
    height: int | None = None
    supportedModels: list[str] = Field(default_factory=list)


class GenerationVideoDurationOption(BaseModel):
    value: int = Field(ge=1, le=120)
    label: str
    supportedModels: list[str] = Field(default_factory=list)


class GenerationOptionsResponse(BaseModel):
    versions: list[int] = Field(default_factory=list)
    versionDetails: list[GenerationVersionInfo] = Field(default_factory=list)
    defaultVersion: int | None = Field(default=None, ge=1, le=10)
    stylePresets: list[GenerationStylePresetOption] = Field(default_factory=list)
    imageSizes: list[GenerationImageSizeOption] = Field(default_factory=list)
    textAnalysisModels: list[GenerationTextAnalysisModelInfo] = Field(default_factory=list)
    defaultTextAnalysisModel: str | None = None
    videoModels: list[GenerationVideoModelInfo] = Field(default_factory=list)
    defaultVideoModel: str | None = None
    videoSizes: list[GenerationVideoSizeOption] = Field(default_factory=list)
    videoDurations: list[GenerationVideoDurationOption] = Field(default_factory=list)
    defaultStylePreset: str | None = None
    defaultImageSize: str | None = None
    defaultVideoSize: str | None = None
    defaultVideoDurationSeconds: int | None = Field(default=None, ge=1, le=120)


class VideoModelUsageItem(BaseModel):
    model: str
    label: str
    provider: str
    used: float = 0.0
    unit: str | None = None
    remaining: float | None = None
    remainingUnit: str | None = None
    remainingLabel: str | None = None
    quota: float | None = None
    usedDurationSeconds: float = 0.0
    source: str | None = None
    note: str | None = None
    updatedAt: str | None = None


class VideoModelUsageResponse(BaseModel):
    generatedAt: str
    items: list[VideoModelUsageItem] = Field(default_factory=list)


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


class TaskMaterial(BaseModel):
    id: str
    kind: MaterialKind
    mediaType: MediaType = MediaType.VIDEO
    title: str
    fileUrl: str
    previewUrl: str | None = None
    mimeType: str | None = None
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    sizeBytes: int | None = None
    createdAt: str | None = None


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
    level: TraceLevel
    stage: TaskStage
    event: str
    message: str
    payload: dict[str, object] = Field(default_factory=dict)


class TaskStatusHistoryRecord(BaseModel):
    statusHistoryId: str
    taskId: str
    previousStatus: TaskStatus | None = None
    nextStatus: TaskStatus
    progress: int
    stage: TaskStage
    event: str
    reason: str | None = None
    operator: str | None = None
    changedAt: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskModelCallRecord(BaseModel):
    modelCallId: str
    taskId: str
    provider: str
    modelName: str
    operationKind: TaskOperationKind | str
    status: TaskModelCallStatus
    latencyMs: int | None = None
    requestPayload: dict[str, Any] = Field(default_factory=dict)
    responsePayload: dict[str, Any] = Field(default_factory=dict)
    responseCode: int | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    startedAt: str | None = None
    finishedAt: str | None = None
    createdAt: str


class SeeddanceTaskQueryResponse(BaseModel):
    taskId: str
    status: str
    videoUrl: str | None = None
    message: str | None = None
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
    textModel: str | None = None
    visionModel: str | None = None
    recentTasks: list["TaskListItem"] = Field(default_factory=list)
    recentFailures: list["TaskListItem"] = Field(default_factory=list)
    recentRunningTasks: list["TaskListItem"] = Field(default_factory=list)
    recentTraceCount: int = 0


class AdminTraceEvent(TaskTraceEvent):
    taskId: str
    taskTitle: str | None = None
    taskStatus: TaskStatus | None = None


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
    editingMode: EditingMode = EditingMode.DRAMA


class TaskDetail(TaskListItem):
    sourceFileName: str
    sourceFileNames: list[str] = Field(default_factory=list)
    sourceAssetIds: list[str] = Field(default_factory=list)
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
    storyboardScript: str | None = None
    materials: list[TaskMaterial] = Field(default_factory=list)
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
    introTemplate: str
    outroTemplate: str
    sourceAssetIds: list[str] = Field(default_factory=list)
    sourceFileNames: list[str] = Field(default_factory=list)
    editingMode: EditingMode = EditingMode.DRAMA
    creativePrompt: str | None = None
    transcriptText: str | None = None

    @model_validator(mode="after")
    def _normalize_mode(self) -> "TaskSpec":
        self.editingMode = EditingMode.DRAMA
        return self


class ModelConstraint(BaseModel):
    model: str
    mediaKind: GenerationMediaKind | Literal["script", "analysis"]
    provider: str | None = None
    maxWidth: int | None = None
    maxHeight: int | None = None
    supportedSizes: list[str] = Field(default_factory=list)
    maxDurationSeconds: float | None = None
    minDurationSeconds: float | None = None
    supportedDurations: list[int] = Field(default_factory=list)
    promptLimit: int | None = None


class ModelCatalog(BaseModel):
    generatedAt: str | None = None
    versions: list[int] = Field(default_factory=list)
    versionDetails: list[GenerationVersionInfo] = Field(default_factory=list)
    stylePresets: list[GenerationStylePresetOption] = Field(default_factory=list)
    imageSizes: list[GenerationImageSizeOption] = Field(default_factory=list)
    textAnalysisModels: list[GenerationTextAnalysisModelInfo] = Field(default_factory=list)
    videoModels: list[GenerationVideoModelInfo] = Field(default_factory=list)
    videoSizes: list[GenerationVideoSizeOption] = Field(default_factory=list)
    videoDurations: list[GenerationVideoDurationOption] = Field(default_factory=list)
    defaultVersion: int | None = None
    defaultTextAnalysisModel: str | None = None
    defaultVideoModel: str | None = None
    defaultImageSize: str | None = None
    defaultVideoSize: str | None = None
    defaultVideoDurationSeconds: int | None = None
    aliases: dict[str, str] = Field(default_factory=dict)
    modelConstraints: list[ModelConstraint] = Field(default_factory=list)


class ProviderErrorEnvelope(BaseModel):
    code: str
    message: str
    provider: str | None = None
    statusCode: int | None = None
    retriable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class GenerationResultBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    runId: str
    kind: GenerationMediaKind | Literal["script", "probe"]
    prompt: str | None = None
    shapedPrompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    modelInfo: dict[str, Any] = Field(default_factory=dict)
    callChain: list[dict[str, Any]] = Field(default_factory=list)


class GenerationResultImage(GenerationResultBase):
    outputUrl: str
    mimeType: str | None = None
    width: int | None = None
    height: int | None = None


class GenerationResultVideo(GenerationResultBase):
    outputUrl: str
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None


class GenerationResultScript(GenerationResultBase):
    sourceText: str | None = None
    visualStyle: str | None = None
    outputFormat: Literal["markdown"] | None = None
    scriptMarkdown: str | None = None
    markdownUrl: str | None = None
    markdownPath: str | None = None


class GenerationResultProbe(GenerationResultBase):
    ready: bool = True
    latencyMs: int | None = None


class GenerationRunRequest(BaseModel):
    id: str | None = None
    kind: GenerationMediaKind | Literal["script", "probe"]
    input: dict[str, Any] = Field(default_factory=dict)
    model: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if isinstance(payload.get("input"), dict):
            return payload
        legacy_input: dict[str, Any] = {}
        prompt = payload.get("prompt")
        if prompt not in {None, ""}:
            if str(payload.get("kind") or "").strip().lower() == "script":
                legacy_input["text"] = prompt
            else:
                legacy_input["prompt"] = prompt
        for key in (
            "version",
            "width",
            "height",
            "durationSeconds",
            "minDurationSeconds",
            "maxDurationSeconds",
            "videoSize",
            "imageSize",
            "stylePreset",
            "extras",
            "metadata",
        ):
            if key in payload and payload.get(key) is not None:
                legacy_input[key] = payload.get(key)
        payload["input"] = legacy_input
        payload["model"] = {
            "textAnalysisModel": payload.get("textAnalysisModel"),
            "providerModel": payload.get("providerModel"),
            "videoModel": payload.get("videoModel"),
        }
        payload["options"] = {
            "stylePreset": payload.get("stylePreset"),
        }
        return payload


class GenerationRunStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationRunResponse(BaseModel):
    id: str
    status: GenerationRunStatus
    kind: GenerationMediaKind | Literal["script", "probe"]
    createdAt: str | None = None
    updatedAt: str
    result: GenerationResultImage | GenerationResultVideo | GenerationResultScript | GenerationResultProbe | None = None
    resultImage: GenerationResultImage | None = None
    resultVideo: GenerationResultVideo | None = None
    resultScript: GenerationResultScript | None = None
    resultProbe: GenerationResultProbe | None = None
    error: ProviderErrorEnvelope | None = None

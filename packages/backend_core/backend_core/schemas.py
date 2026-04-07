from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
        disabled_content_types = {"travel"}
        disabled_style_presets = {
            "travel_citywalk",
            "travel_landscape",
            "travel_healing",
            "travel_roadtrip",
        }
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
        if self.editingMode == "mixcut" and (self.mixcutContentType or "").strip() in disabled_content_types:
            self.mixcutContentType = "generic"
        if self.editingMode == "mixcut" and (self.mixcutStylePreset or "").strip() in disabled_style_presets:
            self.mixcutStylePreset = "director"
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
        disabled_content_types = {"travel"}
        disabled_style_presets = {
            "travel_citywalk",
            "travel_landscape",
            "travel_healing",
            "travel_roadtrip",
        }
        self.editingMode = "mixcut" if self.editingMode == "mixcut" else "drama"
        self.mixcutEnabled = self.editingMode == "mixcut"
        if self.editingMode == "mixcut" and (self.mixcutContentType or "").strip() in disabled_content_types:
            self.mixcutContentType = "generic"
        if self.editingMode == "mixcut" and (self.mixcutStylePreset or "").strip() in disabled_style_presets:
            self.mixcutStylePreset = "director"
        if self.editingMode == "mixcut" and not (self.mixcutContentType or "").strip():
            self.mixcutContentType = "generic"
        if self.editingMode == "mixcut" and not (self.mixcutStylePreset or "").strip():
            self.mixcutStylePreset = "director"
        return self


class GenerateCreativePromptResponse(BaseModel):
    prompt: str
    source: str


class GenerateTextScriptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    visualStyle: str | None = Field(default=None, max_length=120)

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


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentDefinitionSummary(BaseModel):
    key: str
    name: str
    summary: str
    category: str
    color: str
    icon: str
    runPath: str
    executionMode: str
    capabilities: list[str] = Field(default_factory=list)
    defaultInput: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    sortOrder: int = 0
    totalRuns: int = 0
    runningRuns: int = 0
    succeededRuns: int = 0
    failedRuns: int = 0
    lastRunAt: str | None = None
    lastRunStatus: AgentRunStatus | None = None


class AgentArtifact(BaseModel):
    id: str
    kind: str
    title: str
    mimeType: str | None = None
    textContent: str | None = None
    jsonContent: dict[str, Any] = Field(default_factory=dict)
    filePath: str | None = None
    fileUrl: str | None = None
    orderIndex: int = 0
    createdAt: str


class AgentEvent(BaseModel):
    timestamp: str
    level: str
    stage: str
    event: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentTimelineEvent(AgentEvent):
    runId: str
    agentKey: str
    agentName: str
    runStatus: AgentRunStatus
    runTitle: str


class AgentRunSummary(BaseModel):
    id: str
    agentKey: str
    agentName: str
    agentColor: str
    status: AgentRunStatus
    title: str
    summary: str | None = None
    progress: int = 0
    inputText: str | None = None
    outputText: str | None = None
    sourceTaskId: str | None = None
    artifactCount: int = 0
    eventCount: int = 0
    createdAt: str
    startedAt: str | None = None
    finishedAt: str | None = None
    durationSeconds: float | None = None


class AgentRunDetail(AgentRunSummary):
    inputJson: dict[str, Any] = Field(default_factory=dict)
    outputJson: dict[str, Any] = Field(default_factory=dict)
    monitor: dict[str, Any] = Field(default_factory=dict)
    agent: AgentDefinitionSummary
    artifacts: list[AgentArtifact] = Field(default_factory=list)
    events: list[AgentEvent] = Field(default_factory=list)


class AgentDashboardCounts(BaseModel):
    totalAgents: int
    totalRuns: int
    queuedRuns: int
    runningRuns: int
    succeededRuns: int
    failedRuns: int
    totalArtifacts: int
    totalEvents: int


class AgentDashboardAgent(BaseModel):
    key: str
    name: str
    category: str
    color: str
    enabled: bool = True
    totalRuns: int = 0
    runningRuns: int = 0
    succeededRuns: int = 0
    failedRuns: int = 0
    lastRunAt: str | None = None
    lastRunStatus: AgentRunStatus | None = None
    successRate: float = 0.0


class AgentDashboardResponse(BaseModel):
    generatedAt: str
    counts: AgentDashboardCounts
    agents: list[AgentDashboardAgent] = Field(default_factory=list)
    recentRuns: list[AgentRunSummary] = Field(default_factory=list)


class ShortDramaAgentRunRequest(CreateTaskRequest):
    agentNote: str | None = None


class TextMediaAgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    mediaKind: Literal["image", "video"] = "image"
    version: int = Field(ge=1, le=10)
    providerModel: str | None = Field(default=None, max_length=120)
    aspectRatio: str = "9:16"
    durationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
    visualStyle: str | None = None
    stylePreset: str | None = None
    width: int | None = Field(default=None, ge=256, le=4096)
    height: int | None = Field(default=None, ge=256, le=4096)

    @field_validator("prompt", mode="after")
    @classmethod
    def _validate_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must be non-empty")
        return normalized

    @field_validator("visualStyle", mode="after")
    @classmethod
    def _normalize_visual_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("stylePreset", mode="after")
    @classmethod
    def _normalize_style_preset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _normalize_constraints(self) -> "TextMediaAgentRunRequest":
        if self.mediaKind == "image" and self.durationSeconds is not None:
            raise ValueError("durationSeconds is only allowed for video generation")
        if self.mediaKind == "video" and self.durationSeconds is None:
            self.durationSeconds = 4.0
        if self.width is None or self.height is None:
            self.width = 1080 if self.aspectRatio == "9:16" else 1920
            self.height = 1920 if self.aspectRatio == "9:16" else 1080
        return self


class TextScriptAgentRunRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    visualStyle: str | None = None

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


class AIDramaAgentRunRequest(BaseModel):
    title: str = Field(default="一键 AI 剧", max_length=255)
    text: str = Field(min_length=1, max_length=50000)
    visualStyle: str | None = None
    aspectRatio: Literal["9:16", "16:9"] = "9:16"
    totalDurationSeconds: float | None = Field(default=None, ge=6.0, le=90.0)
    shotCount: int | None = Field(default=None, ge=1, le=12)
    shotDurationSeconds: float | None = Field(default=None, ge=1.0, le=8.0)
    continuitySeed: int = Field(default=2025, ge=1, le=2_147_483_647)
    introTemplate: str | None = None
    outroTemplate: str | None = None
    transitionStyle: Literal["cut", "crossfade", "flash", "fade_black"] | None = None
    includeKeyframes: bool = True
    includeDubPlan: bool = True
    includeLipsyncPlan: bool = True

    @model_validator(mode="before")
    @classmethod
    def _migrate_aliases(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "includeKeyframes" not in payload and "generateStoryboardImages" in payload:
            payload["includeKeyframes"] = payload.get("generateStoryboardImages")
        return payload

    @field_validator("title", mode="after")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "一键 AI 剧"

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


class TextMediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class GenerateTextMediaRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    version: int = Field(ge=1, le=10)
    kind: TextMediaKind
    providerModel: str | None = Field(default=None, max_length=120)
    videoModel: str | None = Field(default=None, max_length=120)
    videoSize: str | None = Field(default=None, max_length=32)
    width: int = Field(default=1024, ge=256, le=4096)
    height: int = Field(default=1024, ge=256, le=4096)
    durationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
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

    @field_validator("providerModel", "videoModel", mode="after")
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
        if self.kind == TextMediaKind.IMAGE and self.durationSeconds is not None:
            raise ValueError("durationSeconds is only allowed for video generation")
        if self.kind == TextMediaKind.VIDEO and self.durationSeconds is None:
            raise ValueError("durationSeconds is required for video generation")
        return self


class GenerateTextMediaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    kind: TextMediaKind | None = None
    version: int | None = Field(default=None, ge=1, le=10)
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


class GenerationVideoSizeOption(BaseModel):
    value: str
    label: str
    width: int = Field(ge=256, le=4096)
    height: int = Field(ge=256, le=4096)
    aspectRatio: str
    tier: str | None = None


class GenerationVideoModelOption(BaseModel):
    key: str
    label: str
    description: str | None = None
    sizes: list[GenerationVideoSizeOption] = Field(default_factory=list)
    defaultSize: str | None = None
    durations: list[int] = Field(default_factory=list)
    defaultDurationSeconds: int | None = Field(default=None, ge=1, le=120)
    durationMode: Literal["fixed", "discrete", "range"] = "fixed"
    durationMinSeconds: int | None = Field(default=None, ge=1, le=120)
    durationMaxSeconds: int | None = Field(default=None, ge=1, le=120)
    supportsAudio: bool = False
    supportsShotType: bool = False


class GenerationOptionsResponse(BaseModel):
    versions: list[int] = Field(default_factory=list)
    versionDetails: list[GenerationVersionInfo] = Field(default_factory=list)
    defaultVersion: int | None = Field(default=None, ge=1, le=10)
    stylePresets: list[GenerationStylePresetOption] = Field(default_factory=list)
    imageSizes: list[GenerationImageSizeOption] = Field(default_factory=list)
    videoDurations: list[GenerationVideoDurationOption] = Field(default_factory=list)
    defaultStylePreset: str | None = None
    defaultImageSize: str | None = None
    defaultVideoDurationSeconds: int | None = Field(default=None, ge=1, le=120)
    videoModels: list[GenerationVideoModelOption] = Field(default_factory=list)
    defaultVideoModel: str | None = None
    defaultVideoSize: str | None = None


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
    stylePresets: list[GenerationStylePresetOption] = Field(default_factory=list)
    imageSizes: list[GenerationImageSizeOption] = Field(default_factory=list)
    videoModels: list[GenerationVideoModelInfo] = Field(default_factory=list)
    defaultVideoModel: str | None = None
    videoSizes: list[GenerationVideoSizeOption] = Field(default_factory=list)
    videoDurations: list[GenerationVideoDurationOption] = Field(default_factory=list)
    defaultVersion: int | None = Field(default=None, ge=1, le=10)
    defaultStylePreset: str | None = None
    defaultImageSize: str | None = None
    defaultVideoSize: str | None = None
    defaultVideoDurationSeconds: int | None = Field(default=None, ge=1, le=120)


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

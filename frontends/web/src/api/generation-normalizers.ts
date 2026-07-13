import type {
  GenerateMediaRequest,
  GenerateMediaResponse,
  GenerationCallLogEntry,
  GenerationOptionsResponse,
} from "@/types";

export type UnknownRecord = Record<string, unknown>;

export function asRecord(value: unknown): UnknownRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as UnknownRecord;
}

export function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export function parseImageSize(size: string | undefined): { width: number; height: number } {
  const match = (size ?? "").trim().match(/^(\d+)\s*[xX*]\s*(\d+)$/);
  if (!match) return { width: 1024, height: 1024 };
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return { width: 1024, height: 1024 };
  }
  return { width: Math.trunc(width), height: Math.trunc(height) };
}

function normalizeCallChain(raw: unknown): GenerationCallLogEntry[] {
  if (!Array.isArray(raw)) return [];
  const items: GenerationCallLogEntry[] = [];
  for (const item of raw) {
    const record = asRecord(item);
    if (!record) continue;
    const timestamp = asString(record.timestamp);
    const stage = asString(record.stage);
    const event = asString(record.event);
    const status = asString(record.status);
    const message = asString(record.message);
    if (!timestamp || !stage || !event || !status || !message) continue;
    items.push({
      timestamp,
      stage,
      event,
      status,
      message,
      details: asRecord(record.details) ?? undefined,
    });
  }
  return items;
}

export function normalizeGenerationOptions(raw: unknown): GenerationOptionsResponse {
  const record = asRecord(raw) ?? {};
  const defaultDuration = asNumber(record.defaultVideoDurationSeconds);
  return {
    aspectRatios: Array.isArray(record.aspectRatios)
      ? record.aspectRatios as GenerationOptionsResponse["aspectRatios"]
      : [],
    defaultAspectRatio: asString(record.defaultAspectRatio) || null,
    imageSizes: Array.isArray(record.imageSizes)
      ? record.imageSizes as GenerationOptionsResponse["imageSizes"]
      : [],
    textAnalysisModels: Array.isArray(record.textAnalysisModels)
      ? record.textAnalysisModels as GenerationOptionsResponse["textAnalysisModels"]
      : [],
    defaultTextAnalysisModel: asString(record.defaultTextAnalysisModel) || null,
    imageModels: Array.isArray(record.imageModels)
      ? record.imageModels as GenerationOptionsResponse["imageModels"]
      : [],
    defaultImageModel: asString(record.defaultImageModel) || null,
    videoModels: Array.isArray(record.videoModels)
      ? record.videoModels as GenerationOptionsResponse["videoModels"]
      : [],
    defaultVideoModel: asString(record.defaultVideoModel) || null,
    videoSizes: Array.isArray(record.videoSizes)
      ? record.videoSizes as GenerationOptionsResponse["videoSizes"]
      : [],
    videoDurations: Array.isArray(record.videoDurations)
      ? record.videoDurations as GenerationOptionsResponse["videoDurations"]
      : [],
    defaultImageSize: asString(record.defaultImageSize) || undefined,
    defaultVideoSize: asString(record.defaultVideoSize) || undefined,
    defaultVideoDurationSeconds: defaultDuration === null
      ? undefined
      : Math.trunc(defaultDuration),
  };
}

export function buildGenerationRunPayload(payload: GenerateMediaRequest): UnknownRecord {
  const size = payload.mediaKind === "image" ? payload.imageSize : payload.videoSize;
  const { width, height } = parseImageSize(size);
  const input: UnknownRecord = { prompt: payload.prompt, version: payload.version, width, height };
  if (payload.mediaKind === "video") {
    input.durationSeconds = payload.videoDurationSeconds;
    input.minDurationSeconds = payload.minDurationSeconds;
    input.maxDurationSeconds = payload.maxDurationSeconds;
    input.videoSize = payload.videoSize || undefined;
  }
  return {
    kind: payload.mediaKind,
    input,
    model: {
      providerModel: payload.providerModel || undefined,
      textAnalysisModel: payload.textAnalysisModel || undefined,
    },
  };
}

function resultRecord(rawRun: unknown): UnknownRecord {
  const run = asRecord(rawRun) ?? {};
  return asRecord(run.result) ?? asRecord(run.resultImage) ?? asRecord(run.resultVideo) ?? {};
}

export function normalizeMediaRunResult(
  rawRun: unknown,
  requestPayload: GenerateMediaRequest,
): GenerateMediaResponse {
  const run = asRecord(rawRun) ?? {};
  const result = resultRecord(run);
  const metadata = asRecord(result.metadata) ?? {};
  const modelInfo = asRecord(result.modelInfo) ?? {};
  const outputUrl = asString(result.outputUrl)
    || asString(metadata.outputUrl)
    || asString(metadata.fileUrl);
  if (!outputUrl) throw new Error("生成任务尚未返回可用输出地址");
  const mediaKind = (asString(run.kind) || requestPayload.mediaKind) as GenerateMediaResponse["mediaKind"];
  return {
    id: asString(run.id) || `${Date.now()}`,
    mediaKind,
    prompt: asString(result.prompt) || requestPayload.prompt,
    version: Math.trunc(asNumber((asRecord(run.input) ?? {}).version) ?? requestPayload.version),
    outputUrl,
    thumbnailUrl: asString(result.thumbnailUrl) || null,
    providerModel: asString(modelInfo.providerModel) || requestPayload.providerModel || null,
    mimeType: asString(result.mimeType) || null,
    width: asNumber(result.width),
    height: asNumber(result.height),
    durationSeconds: asNumber(result.durationSeconds),
    createdAt: asString(run.createdAt) || null,
    modelInfo: {
      provider: asString(modelInfo.provider) || null,
      modelName: asString(modelInfo.modelName) || null,
      providerModel: asString(modelInfo.providerModel) || null,
      requestedModel: asString(modelInfo.requestedModel) || null,
      resolvedModel: asString(modelInfo.resolvedModel) || null,
      textAnalysisModel: asString(modelInfo.textAnalysisModel) || null,
      endpointHost: asString(modelInfo.endpointHost) || null,
      temperature: asNumber(modelInfo.temperature),
      maxTokens: asNumber(modelInfo.maxTokens),
      timeoutSeconds: asNumber(modelInfo.timeoutSeconds),
      strategyVersion: asNumber(modelInfo.strategyVersion),
      strategyVersionLabel: asString(modelInfo.strategyVersionLabel) || null,
      strategySummary: asString(modelInfo.strategySummary) || null,
      mediaKind,
    },
    callChain: normalizeCallChain(result.callChain),
    metadata,
  };
}

export function hasTerminalRunResult(rawRun: unknown): boolean {
  const result = resultRecord(rawRun);
  const metadata = asRecord(result.metadata) ?? {};
  return Boolean(
    asString(result.outputUrl)
    || asString(result.thumbnailUrl)
    || asString(metadata.outputUrl)
    || asString(metadata.fileUrl),
  );
}

export function runStatus(rawRun: unknown): string {
  return asString((asRecord(rawRun) ?? {}).status).toLowerCase();
}

export function runErrorMessage(rawRun: unknown): string {
  const result = resultRecord(rawRun);
  const metadata = asRecord(result.metadata) ?? {};
  return asString(result.error)
    || asString(metadata.taskMessage)
    || asString(metadata.error)
    || "生成任务失败";
}

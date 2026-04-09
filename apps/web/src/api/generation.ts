import { getJson, postJson } from "./client";
import type {
  GenerationCallLogEntry,
  GenerateMediaRequest,
  GenerateMediaResponse,
  GenerationOptionsResponse,
  ProbeTextAnalysisModelRequest,
  ProbeTextAnalysisModelResponse,
  VideoModelUsageResponse,
} from "@/types";

type UnknownRecord = Record<string, unknown>;

const CATALOG_ENDPOINT = "/api/v2/generation/catalog";
const RUNS_ENDPOINT = "/api/v2/generation/runs";
const RUN_DETAILS_ENDPOINT = (runId: string) => `/api/v2/generation/runs/${encodeURIComponent(runId)}`;
const USAGE_ENDPOINT = "/api/v2/generation/usage";

function asRecord(value: unknown): UnknownRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function parseImageSize(size: string | undefined): { width: number; height: number } {
  const normalized = (size ?? "").trim();
  const match = normalized.match(/^(\d+)\s*[xX]\s*(\d+)$/);
  if (!match) {
    return { width: 1024, height: 1024 };
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return { width: 1024, height: 1024 };
  }
  return { width: Math.trunc(width), height: Math.trunc(height) };
}

function normalizeCallChain(raw: unknown): GenerationCallLogEntry[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  const items: GenerationCallLogEntry[] = [];
  for (const item of raw) {
    const record = asRecord(item);
    if (!record) {
      continue;
    }
    const timestamp = asString(record.timestamp);
    const stage = asString(record.stage);
    const event = asString(record.event);
    const status = asString(record.status);
    const message = asString(record.message);
    if (!timestamp || !stage || !event || !status || !message) {
      continue;
    }
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

function normalizeOptions(raw: unknown): GenerationOptionsResponse {
  const record = asRecord(raw) ?? {};
  return {
    versions: Array.isArray(record.versions)
      ? record.versions
          .map((item) => asNumber(item))
          .filter((item): item is number => item !== null)
          .map((item) => Math.trunc(item))
      : [1],
    versionDetails: Array.isArray(record.versionDetails) ? (record.versionDetails as GenerationOptionsResponse["versionDetails"]) : [],
    defaultVersion: asNumber(record.defaultVersion) ? Math.trunc(asNumber(record.defaultVersion) as number) : 1,
    stylePresets: Array.isArray(record.stylePresets) ? (record.stylePresets as GenerationOptionsResponse["stylePresets"]) : [],
    imageSizes: Array.isArray(record.imageSizes) ? (record.imageSizes as GenerationOptionsResponse["imageSizes"]) : [],
    textAnalysisModels: Array.isArray(record.textAnalysisModels)
      ? (record.textAnalysisModels as GenerationOptionsResponse["textAnalysisModels"])
      : [],
    defaultTextAnalysisModel: asString(record.defaultTextAnalysisModel) || null,
    videoModels: Array.isArray(record.videoModels) ? (record.videoModels as GenerationOptionsResponse["videoModels"]) : [],
    defaultVideoModel: asString(record.defaultVideoModel) || null,
    videoSizes: Array.isArray(record.videoSizes) ? (record.videoSizes as GenerationOptionsResponse["videoSizes"]) : [],
    videoDurations: Array.isArray(record.videoDurations)
      ? (record.videoDurations as GenerationOptionsResponse["videoDurations"])
      : [],
    defaultStylePreset: asString(record.defaultStylePreset) || null,
    defaultImageSize: asString(record.defaultImageSize) || undefined,
    defaultVideoSize: asString(record.defaultVideoSize) || undefined,
    defaultVideoDurationSeconds: asNumber(record.defaultVideoDurationSeconds) ? Math.trunc(asNumber(record.defaultVideoDurationSeconds) as number) : undefined,
  };
}

function buildRunPayload(payload: GenerateMediaRequest): UnknownRecord {
  const { width, height } = parseImageSize(payload.mediaKind === "image" ? payload.imageSize : payload.videoSize);
  const input: UnknownRecord = {
    prompt: payload.prompt,
    version: payload.version,
    width,
    height,
  };
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
    options: {
      stylePreset: payload.stylePreset || undefined,
    },
  };
}

function normalizeMediaRunResult(rawRun: unknown, requestPayload: GenerateMediaRequest): GenerateMediaResponse {
  const run = asRecord(rawRun) ?? {};
  const resultRecord =
    asRecord(run.result) ??
    asRecord(run.resultImage) ??
    asRecord(run.resultVideo) ??
    {};
  const metadata = asRecord(resultRecord.metadata) ?? {};
  const modelInfo = asRecord(resultRecord.modelInfo) ?? {};
  const outputUrl = asString(resultRecord.outputUrl) || asString(metadata.outputUrl) || asString(metadata.fileUrl);
  if (!outputUrl) {
    throw new Error("生成任务尚未返回可用输出地址");
  }
  const mediaKind = (asString(run.kind) || requestPayload.mediaKind) as GenerateMediaResponse["mediaKind"];
  return {
    id: asString(run.id) || `${Date.now()}`,
    mediaKind,
    prompt: asString(resultRecord.prompt) || requestPayload.prompt,
    version: Math.trunc(asNumber((asRecord(run.input) ?? {}).version) ?? requestPayload.version),
    outputUrl,
    thumbnailUrl: asString(resultRecord.thumbnailUrl) || null,
    stylePreset: asString((asRecord(run.options) ?? {}).stylePreset) || requestPayload.stylePreset || null,
    providerModel: asString(modelInfo.providerModel) || requestPayload.providerModel || null,
    mimeType: asString(resultRecord.mimeType) || null,
    width: asNumber(resultRecord.width),
    height: asNumber(resultRecord.height),
    durationSeconds: asNumber(resultRecord.durationSeconds),
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
    callChain: normalizeCallChain(resultRecord.callChain),
    metadata,
  };
}

export async function fetchGenerationOptions() {
  const raw = await getJson<unknown>(CATALOG_ENDPOINT);
  return normalizeOptions(raw);
}

export async function generateMediaFromText(payload: GenerateMediaRequest) {
  const runPayload = buildRunPayload(payload);
  let run = await postJson<unknown>(RUNS_ENDPOINT, runPayload);
  const runRecord = asRecord(run) ?? {};
  const status = asString(runRecord.status).toLowerCase();
  if ((status === "accepted" || status === "running") && asString(runRecord.id)) {
    run = await getJson<unknown>(RUN_DETAILS_ENDPOINT(asString(runRecord.id)));
  }
  return normalizeMediaRunResult(run, payload);
}

export async function probeTextAnalysisModel(payload: ProbeTextAnalysisModelRequest) {
  const run = await postJson<unknown>(RUNS_ENDPOINT, {
    kind: "probe",
    input: {},
    model: {
      textAnalysisModel: payload.textAnalysisModel?.trim() || undefined,
    },
    options: {},
  });
  const runRecord = asRecord(run) ?? {};
  const probe =
    asRecord(runRecord.result) ??
    asRecord(runRecord.resultProbe) ??
    {};
  const metadata = asRecord(probe.metadata) ?? {};
  return {
    ready: Boolean(probe.ready ?? metadata.ready ?? true),
    requestedModel: asString(metadata.requestedModel) || payload.textAnalysisModel || "",
    resolvedModel: asString(metadata.resolvedModel) || asString(payload.textAnalysisModel) || "",
    provider: asString(metadata.provider) || "unknown",
    family: asString(metadata.family) || null,
    mode: asString(metadata.mode) || "",
    endpointHost: asString(metadata.endpointHost) || "",
    latencyMs: Math.trunc(asNumber(probe.latencyMs ?? metadata.latencyMs) ?? 0),
    messagePreview: asString(metadata.messagePreview) || null,
    checkedAt: asString(metadata.checkedAt) || new Date().toISOString(),
  } satisfies ProbeTextAnalysisModelResponse;
}

export async function fetchVideoModelUsage() {
  const raw = await getJson<unknown>(USAGE_ENDPOINT);
  const record = asRecord(raw) ?? {};
  return {
    generatedAt: asString(record.generatedAt) || null,
    updatedAt: asString(record.updatedAt) || null,
    items: Array.isArray(record.items) ? (record.items as VideoModelUsageResponse["items"]) : [],
  } satisfies VideoModelUsageResponse;
}

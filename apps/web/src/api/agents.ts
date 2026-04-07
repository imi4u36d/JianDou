import { getJson, postForm, postJson } from "./client";
import type { AgentDefinition, AgentId, AgentRunDetail, AgentRunEvent, AgentRunSummary, UploadResponse } from "@/types";
import { DEFAULT_AGENT_ID, getAgentDefinition } from "@/workbench/agents";
import { loadAgentRuns, upsertAgentRun } from "@/workbench/storage";

export interface AIDramaAgentDraft {
  title: string;
  text: string;
  aspectRatio: "9:16" | "16:9";
  continuitySeed: number;
  totalDurationSeconds: number | null;
  includeKeyframes: boolean;
  includeDubPlan: boolean;
  includeLipsyncPlan: boolean;
}

export interface DramaAgentDraft {
  title: string;
  sourceFiles: File[];
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt: string;
  transcriptText: string;
  editingMode: "drama" | "mixcut";
  mixcutContentType: string;
  mixcutStylePreset: string;
}

export interface VisualAgentDraft {
  prompt: string;
  mediaKind: "image" | "video";
  version: number;
  stylePreset: string;
  providerModel: string;
  imageSize: string;
  videoSize: string;
  videoDurationSeconds: number;
}

export interface ScriptAgentDraft {
  text: string;
  visualStyle: string;
}

export interface AgentDashboardSnapshot {
  generatedAt: string;
  counts: {
    totalAgents: number;
    totalRuns: number;
    queuedRuns: number;
    runningRuns: number;
    succeededRuns: number;
    failedRuns: number;
    totalArtifacts: number;
    totalEvents: number;
  };
}

type BackendRunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
type UnknownRecord = Record<string, unknown>;

const AGENT_ENDPOINT = "/agents";
const UPLOAD_VIDEO_ENDPOINT = "/uploads/videos";

const UI_TO_BACKEND_AGENT_KEY: Record<AgentId, string> = {
  "ai-drama": "ai-drama",
  "drama-editor": "short-drama",
  "visual-lab": "text-media",
  "script-director": "text-script",
};

const BACKEND_TO_UI_AGENT_ID: Record<string, AgentId> = {
  "ai-drama": "ai-drama",
  "short-drama": "drama-editor",
  "text-media": "visual-lab",
  "text-script": "script-director",
};

function asRecord(value: unknown): UnknownRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function backendAgentKey(agentId: AgentId) {
  return UI_TO_BACKEND_AGENT_KEY[agentId] || UI_TO_BACKEND_AGENT_KEY[DEFAULT_AGENT_ID];
}

function uiAgentId(agentKey: unknown): AgentId {
  if (typeof agentKey === "string" && BACKEND_TO_UI_AGENT_ID[agentKey]) {
    return BACKEND_TO_UI_AGENT_ID[agentKey];
  }
  return DEFAULT_AGENT_ID;
}

function toUiStatus(status: unknown): AgentRunSummary["status"] {
  const normalized = asString(status).toLowerCase() as BackendRunStatus | "";
  if (normalized === "running") {
    return "running";
  }
  if (normalized === "queued" || normalized === "cancelled") {
    return "queued";
  }
  if (normalized === "failed") {
    return "failed";
  }
  if (normalized === "succeeded") {
    return "completed";
  }
  return "idle";
}

function toUiLevel(level: unknown): AgentRunEvent["level"] {
  const normalized = asString(level).toLowerCase();
  if (normalized === "error") {
    return "error";
  }
  if (normalized === "warn" || normalized === "warning") {
    return "warn";
  }
  if (normalized === "success" || normalized === "ok") {
    return "success";
  }
  return "info";
}

function inferArtifactKind(record: UnknownRecord): string {
  const kind = asString(record.kind).toLowerCase();
  const mimeType = asString(record.mimeType).toLowerCase();
  const fileUrl = asString(record.fileUrl).toLowerCase();
  const textContent = asString(record.textContent).toLowerCase();
  if (mimeType.startsWith("image/")) {
    return "image";
  }
  if (mimeType.startsWith("video/")) {
    return "video";
  }
  if (mimeType.includes("markdown") || kind.includes("script")) {
    return "markdown";
  }
  if (/\.(png|jpe?g|webp|gif|avif)(\?|#|$)/.test(fileUrl)) {
    return "image";
  }
  if (/\.(mp4|webm|mov|m4v)(\?|#|$)/.test(fileUrl)) {
    return "video";
  }
  if (textContent.includes("| 镜号 |") || textContent.includes("```") || textContent.includes("## ")) {
    return "markdown";
  }
  return kind || "artifact";
}

function normalizeEvent(value: unknown): AgentRunEvent {
  const record = asRecord(value) ?? {};
  return {
    timestamp: asString(record.timestamp) || new Date().toISOString(),
    level: toUiLevel(record.level),
    stage: asString(record.stage) || "agent",
    event: asString(record.event) || "step",
    message: asString(record.message) || "",
    payload: (asRecord(record.payload) ?? {}) as Record<string, unknown>,
  };
}

function normalizeSummary(value: unknown): AgentRunSummary {
  const record = asRecord(value) ?? {};
  const agentId = uiAgentId(record.agentKey);
  const createdAt = asString(record.createdAt) || new Date().toISOString();
  const updatedAt = asString(record.finishedAt) || asString(record.startedAt) || createdAt;
  const summary = asString(record.summary);
  const sourceTaskId = asString(record.sourceTaskId);
  const artifactCount = Math.max(0, Math.trunc(asNumber(record.artifactCount) ?? 0));
  const durationSeconds = asNumber(record.durationSeconds);
  return {
    id: asString(record.id) || `${Date.now()}`,
    agentId,
    title: asString(record.title) || getAgentDefinition(agentId).name,
    summary: summary || getAgentDefinition(agentId).description,
    status: toUiStatus(record.status),
    progress: Math.max(0, Math.min(100, Math.trunc(asNumber(record.progress) ?? 0))),
    createdAt,
    updatedAt,
    sourceLabel: sourceTaskId || asString(record.agentName) || getAgentDefinition(agentId).name,
    resultLabel: summary || toUiStatus(record.status),
    artifactCount,
    sourceTaskId: sourceTaskId || null,
    startedAt: asString(record.startedAt) || null,
    finishedAt: asString(record.finishedAt) || null,
    durationSeconds,
    latencyMs: durationSeconds !== null ? Math.round(durationSeconds * 1000) : null,
  };
}

function normalizeDetail(value: unknown): AgentRunDetail {
  const record = asRecord(value) ?? {};
  const summary = normalizeSummary(value);
  const artifactsRaw = Array.isArray(record.artifacts) ? record.artifacts : [];
  const eventsRaw = Array.isArray(record.events) ? record.events : [];
  return {
    ...summary,
    input: (asRecord(record.inputJson) ?? {}) as Record<string, unknown>,
    output: (asRecord(record.outputJson) ?? {}) as Record<string, unknown>,
    events: eventsRaw.map((item) => normalizeEvent(item)),
    artifacts: artifactsRaw.map((item) => {
      const artifact = asRecord(item) ?? {};
      const jsonContent = asRecord(artifact.jsonContent) ?? {};
      return {
        kind: inferArtifactKind(artifact),
        label: asString(artifact.title) || asString(artifact.kind) || "Artifact",
        url: asString(artifact.fileUrl) || asString(jsonContent.outputUrl) || asString(jsonContent.fileUrl) || null,
        mimeType: asString(artifact.mimeType) || null,
        text: asString(artifact.textContent) || asString(jsonContent.scriptMarkdown) || asString(jsonContent.outputText) || null,
        json: jsonContent as Record<string, unknown>,
      };
    }),
    monitor: (asRecord(record.monitor) ?? {}) as Record<string, unknown>,
  };
}

async function uploadVideo(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>(UPLOAD_VIDEO_ENDPOINT, form);
}

function parseImageSize(size: string) {
  const match = size.trim().match(/^(\d+)\s*[xX]\s*(\d+)$/);
  if (!match) {
    return { width: 1024, height: 1024 };
  }
  return {
    width: Number(match[1]) || 1024,
    height: Number(match[2]) || 1024,
  };
}

function aspectRatioFromDimensions(width: number, height: number): "9:16" | "16:9" {
  return width > height ? "16:9" : "9:16";
}

export async function fetchAgentDashboard() {
  const raw = await getJson<unknown>(`${AGENT_ENDPOINT}/dashboard`);
  const record = asRecord(raw) ?? {};
  const counts = asRecord(record.counts) ?? {};
  return {
    generatedAt: asString(record.generatedAt) || new Date().toISOString(),
    counts: {
      totalAgents: Math.trunc(asNumber(counts.totalAgents) ?? 0),
      totalRuns: Math.trunc(asNumber(counts.totalRuns) ?? 0),
      queuedRuns: Math.trunc(asNumber(counts.queuedRuns) ?? 0),
      runningRuns: Math.trunc(asNumber(counts.runningRuns) ?? 0),
      succeededRuns: Math.trunc(asNumber(counts.succeededRuns) ?? 0),
      failedRuns: Math.trunc(asNumber(counts.failedRuns) ?? 0),
      totalArtifacts: Math.trunc(asNumber(counts.totalArtifacts) ?? 0),
      totalEvents: Math.trunc(asNumber(counts.totalEvents) ?? 0),
    },
  } satisfies AgentDashboardSnapshot;
}

export async function fetchAgentRuns(agentId?: AgentId) {
  const params = new URLSearchParams();
  if (agentId) {
    params.set("agentKey", backendAgentKey(agentId));
  }
  const raw = await getJson<unknown>(`${AGENT_ENDPOINT}/runs${params.toString() ? `?${params.toString()}` : ""}`);
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map((item) => normalizeSummary(item));
}

export async function fetchAgentRun(runId: string) {
  const raw = await getJson<unknown>(`${AGENT_ENDPOINT}/runs/${encodeURIComponent(runId)}`);
  const detail = normalizeDetail(raw);
  upsertAgentRun(detail);
  return detail;
}

export async function runDramaAgent(draft: DramaAgentDraft) {
  if (!draft.sourceFiles.length) {
    throw new Error("短剧剪辑 Agent 需要至少一个源素材。");
  }
  const uploaded: UploadResponse[] = [];
  for (const file of draft.sourceFiles) {
    uploaded.push(await uploadVideo(file));
  }
  const editingMode = uploaded.length > 1 ? "mixcut" : draft.editingMode;
  const payload = {
    title: draft.title,
    sourceAssetId: uploaded[0].assetId,
    sourceAssetIds: uploaded.map((item) => item.assetId),
    sourceFileName: uploaded[0].fileName,
    sourceFileNames: uploaded.map((item) => item.fileName),
    editingMode,
    mixcutEnabled: editingMode === "mixcut",
    platform: draft.platform,
    aspectRatio: draft.aspectRatio,
    minDurationSeconds: draft.minDurationSeconds,
    maxDurationSeconds: draft.maxDurationSeconds,
    outputCount: draft.outputCount,
    introTemplate: draft.introTemplate,
    outroTemplate: draft.outroTemplate,
    creativePrompt: draft.creativePrompt.trim() || undefined,
    transcriptText: draft.transcriptText.trim() || undefined,
    mixcutContentType: editingMode === "mixcut" ? (draft.mixcutContentType || "generic") : undefined,
    mixcutStylePreset: editingMode === "mixcut" ? (draft.mixcutStylePreset || "director") : undefined,
  };
  const raw = await postJson<unknown>(`${AGENT_ENDPOINT}/${backendAgentKey("drama-editor")}/runs`, payload);
  const detail = normalizeDetail(raw);
  upsertAgentRun(detail);
  return detail;
}

export async function runAIDramaAgent(draft: AIDramaAgentDraft) {
  const payload = {
    title: draft.title.trim(),
    text: draft.text.trim(),
    aspectRatio: draft.aspectRatio,
    continuitySeed: draft.continuitySeed,
    totalDurationSeconds: draft.totalDurationSeconds ?? undefined,
    includeKeyframes: draft.includeKeyframes,
    includeDubPlan: draft.includeDubPlan,
    includeLipsyncPlan: draft.includeLipsyncPlan,
  };
  const raw = await postJson<unknown>(`${AGENT_ENDPOINT}/${backendAgentKey("ai-drama")}/runs`, payload);
  const detail = normalizeDetail(raw);
  upsertAgentRun(detail);
  return detail;
}

export async function runVisualAgent(agentId: AgentId, draft: VisualAgentDraft) {
  const imageDimensions = parseImageSize(draft.imageSize);
  const videoDimensions = parseImageSize(draft.videoSize || draft.imageSize);
  const aspectRatio = aspectRatioFromDimensions(
    draft.mediaKind === "video" ? videoDimensions.width : imageDimensions.width,
    draft.mediaKind === "video" ? videoDimensions.height : imageDimensions.height
  );
  const payload = {
    prompt: draft.prompt.trim(),
    mediaKind: draft.mediaKind,
    version: draft.version,
    aspectRatio,
    durationSeconds: draft.mediaKind === "video" ? draft.videoDurationSeconds : undefined,
    stylePreset: draft.stylePreset || undefined,
    providerModel: draft.mediaKind === "video" ? draft.providerModel || undefined : undefined,
    videoSize: draft.mediaKind === "video" ? draft.videoSize || undefined : undefined,
    width: draft.mediaKind === "image" ? imageDimensions.width : videoDimensions.width,
    height: draft.mediaKind === "image" ? imageDimensions.height : videoDimensions.height,
  };
  const raw = await postJson<unknown>(`${AGENT_ENDPOINT}/${backendAgentKey(agentId)}/runs`, payload);
  const detail = normalizeDetail(raw);
  upsertAgentRun(detail);
  return detail;
}

export async function runScriptAgent(agentId: AgentId, draft: ScriptAgentDraft) {
  const payload = {
    text: draft.text,
    visualStyle: draft.visualStyle || undefined,
  };
  const raw = await postJson<unknown>(`${AGENT_ENDPOINT}/${backendAgentKey(agentId)}/runs`, payload);
  const detail = normalizeDetail(raw);
  upsertAgentRun(detail);
  return detail;
}

export function getWorkbenchAgentDefinition(agentId: AgentId): AgentDefinition {
  return getAgentDefinition(agentId);
}

export function getPersistedRuns() {
  return loadAgentRuns();
}

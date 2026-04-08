import type { GenerateMediaResponse, GenerateScriptResponse, AgentRunDetail, GenerationMediaKind } from "@/types";
import type { TaskProgressState } from "@/components/generate/types";

type UnknownRecord = Record<string, unknown>;

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
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function parseMediaKind(value: unknown, fallback: GenerationMediaKind = "image"): GenerationMediaKind {
  const normalized = asString(value).toLowerCase();
  if (normalized === "image" || normalized === "video") {
    return normalized;
  }
  return fallback;
}

function findMediaArtifact(run: AgentRunDetail) {
  return run.artifacts.find((artifact) => {
    const mimeType = asString(artifact.mimeType).toLowerCase();
    return Boolean(artifact.url) && (mimeType.startsWith("image/") || mimeType.startsWith("video/") || artifact.kind === "media-asset");
  }) || null;
}

export function isAgentRunActive(run: AgentRunDetail | null | undefined): boolean {
  return Boolean(run && (run.status === "queued" || run.status === "running"));
}

export function isAgentRunTerminal(run: AgentRunDetail | null | undefined): boolean {
  return Boolean(run && (run.status === "completed" || run.status === "failed"));
}

export function mediaResultFromAgentRun(run: AgentRunDetail | null | undefined): GenerateMediaResponse | null {
  if (!run) {
    return null;
  }
  const output = asRecord(run.output) ?? {};
  const metadata = asRecord(output.metadata) ?? {};
  const artifact = findMediaArtifact(run);
  const outputUrl = asString(output.outputUrl) || asString(output.fileUrl) || asString(artifact?.url);
  if (!outputUrl) {
    return null;
  }
  const mediaKind = parseMediaKind(output.kind ?? output.mediaKind ?? run.monitor.mediaKind, artifact?.mimeType?.startsWith("video/") ? "video" : "image");
  const providerModel = asString(output.providerModel) || asString(asRecord(output.modelInfo)?.providerModel) || asString(metadata.providerModel) || null;
  return {
    id: asString(output.id) || run.id,
    mediaKind,
    prompt: asString(output.prompt) || asString(run.input.prompt),
    version: Math.trunc(asNumber(output.version) ?? 1),
    outputUrl,
    thumbnailUrl: asString(output.thumbnailUrl) || null,
    stylePreset: asString(output.stylePreset) || asString(run.input.stylePreset) || null,
    providerModel,
    mimeType: asString(output.mimeType) || asString(artifact?.mimeType) || null,
    width: asNumber(output.width),
    height: asNumber(output.height),
    durationSeconds: asNumber(output.durationSeconds),
    createdAt: asString(output.createdAt) || run.finishedAt || run.createdAt,
    modelInfo: asRecord(output.modelInfo),
    callChain: asArray(output.callChain),
    metadata,
  };
}

export function scriptResultFromAgentRun(run: AgentRunDetail | null | undefined): GenerateScriptResponse | null {
  if (!run) {
    return null;
  }
  const output = asRecord(run.output) ?? {};
  const primaryArtifact = run.artifacts.find((artifact) => Boolean(artifact.text) || artifact.kind === "markdown") || null;
  const scriptMarkdown = asString(output.scriptMarkdown) || asString(primaryArtifact?.text);
  if (!scriptMarkdown) {
    return null;
  }
  const metadata = asRecord(output.metadata) ?? {};
  return {
    id: asString(output.id) || run.id,
    sourceText: asString(output.sourceText) || asString(run.input.text),
    visualStyle: asString(output.visualStyle) || asString(run.input.visualStyle) || "AI 自动决策",
    outputFormat: "markdown",
    scriptMarkdown,
    markdownFilePath: asString(output.markdownFilePath) || null,
    markdownFileUrl: asString(output.markdownFileUrl) || asString(primaryArtifact?.url) || null,
    downloadUrl: asString(output.downloadUrl) || asString(output.markdownFileUrl) || asString(primaryArtifact?.url) || null,
    source: asString(output.source) || "agent-run",
    createdAt: asString(output.createdAt) || run.finishedAt || run.createdAt,
    modelInfo: asRecord(output.modelInfo),
    callChain: asArray(output.callChain),
    metadata,
  };
}

export function progressStateFromAgentRun(
  run: AgentRunDetail | null | undefined,
  fallbackMessage: string,
): TaskProgressState {
  if (!run) {
    return {
      status: "idle",
      progress: 0,
      stage: "等待任务",
      message: fallbackMessage,
      updatedAt: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    };
  }
  const updatedAt = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  if (run.status === "queued") {
    return {
      status: "running",
      progress: Math.max(run.progress, 12),
      stage: "任务排队中",
      message: run.summary || "已创建任务，等待 worker 开始执行。",
      updatedAt,
    };
  }
  if (run.status === "running") {
    return {
      status: "running",
      progress: Math.max(run.progress, 56),
      stage: "任务执行中",
      message: run.summary || "正在请求模型并等待结果返回。",
      updatedAt,
    };
  }
  if (run.status === "failed") {
    return {
      status: "failed",
      progress: Math.max(run.progress, 1),
      stage: "任务失败",
      message: run.summary || "生成失败，请稍后重试。",
      updatedAt,
    };
  }
  return {
    status: "completed",
    progress: 100,
    stage: "任务完成",
    message: run.summary || "生成结果已返回。",
    updatedAt,
  };
}

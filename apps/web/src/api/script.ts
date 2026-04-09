import { getJson, postJson } from "./client";
import type { GenerateScriptRequest, GenerateScriptResponse } from "@/types";

const RUNS_ENDPOINT = "/api/v2/generation/runs";
const RUN_DETAILS_ENDPOINT = (runId: string) => `/api/v2/generation/runs/${encodeURIComponent(runId)}`;

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

function normalizeResponse(
  raw: Partial<GenerateScriptResponse> | null | undefined,
  requestPayload: GenerateScriptRequest,
): GenerateScriptResponse {
  return {
    id: (raw?.id || "").trim() || `${Date.now()}`,
    sourceText: (raw?.sourceText || "").trim() || requestPayload.text.trim(),
    visualStyle: (raw?.visualStyle || "").trim() || requestPayload.visualStyle?.trim() || "AI 自动决策",
    outputFormat: raw?.outputFormat || "markdown",
    scriptMarkdown: (raw?.scriptMarkdown || "").trim(),
    markdownFilePath: (raw?.markdownFilePath || "").trim() || null,
    markdownFileUrl: (raw?.markdownFileUrl || "").trim() || null,
    downloadUrl: (raw?.downloadUrl || "").trim() || null,
    source: (raw?.source || "").trim() || "remote",
    createdAt: (raw?.createdAt || "").trim() || new Date().toISOString(),
    modelInfo: raw?.modelInfo || null,
    callChain: Array.isArray(raw?.callChain) ? raw.callChain : [],
    metadata: raw?.metadata || {},
  };
}

function simplifyGenerationRun(raw: UnknownRecord | null | undefined, payload: GenerateScriptRequest): Partial<GenerateScriptResponse> {
  const run = raw ?? {};
  const scriptResult = asRecord(run.resultScript ?? run.result ?? {}) ?? {};
  const metadata = asRecord(scriptResult.metadata) ?? {};
  const callChain = Array.isArray(scriptResult.callChain) ? scriptResult.callChain : [];
  return {
    id: asString(run.id) || asString(scriptResult.runId) || `${Date.now()}`,
    sourceText: asString(scriptResult.sourceText) || payload.text,
    visualStyle: asString(scriptResult.visualStyle) || asString(metadata.visualStyle) || payload.visualStyle?.trim() || "AI 自动决策",
    scriptMarkdown: asString(scriptResult.scriptMarkdown) || asString(metadata.scriptMarkdown) || "",
    markdownFilePath: asString(scriptResult.markdownPath) || null,
    markdownFileUrl: asString(scriptResult.markdownUrl) || null,
    downloadUrl: asString(scriptResult.markdownUrl) || null,
    source: asString(metadata.source) || "remote",
    createdAt: asString(run.createdAt) || new Date().toISOString(),
    modelInfo: (asRecord(scriptResult.modelInfo) ?? {}) as Record<string, unknown>,
    callChain,
    metadata: {
      ...metadata,
      shapedPrompt: asString(scriptResult.prompt) || undefined,
    },
  };
}

export async function generateScriptFromText(payload: GenerateScriptRequest) {
  const runPayload = {
    kind: "script",
    input: {
      text: payload.text.trim(),
    },
    model: {
      textAnalysisModel: payload.textAnalysisModel?.trim() || undefined,
    },
    options: {
      visualStyle: payload.visualStyle?.trim() || undefined,
    },
    metadata: { source: "frontend-script" },
  };
  let raw = await postJson<unknown>(RUNS_ENDPOINT, runPayload);
  const run = asRecord(raw) ?? {};
  const status = asString(run.status).toLowerCase();
  const runId = asString(run.id);
  if ((status === "accepted" || status === "running") && runId) {
    raw = await getJson<unknown>(RUN_DETAILS_ENDPOINT(runId));
  }
  const simplified = simplifyGenerationRun(asRecord(raw), payload);
  return normalizeResponse(simplified, payload);
}

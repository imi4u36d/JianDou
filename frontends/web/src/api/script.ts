/**
 * 脚本相关 API 请求封装。
 */
import { getJson, postJson } from "./client";
import type { GenerateScriptRequest, GenerateScriptResponse } from "@/types";

const RUNS_ENDPOINT = "/api/v3/generation/runs";
/**
 * 处理RUNDETAILSENDPOINT。
 * @param runId 运行标识值
 */
const RUN_DETAILS_ENDPOINT = (runId: string) => `/api/v3/generation/runs/${encodeURIComponent(runId)}`;
const RUN_POLL_INTERVAL_MS = 1200;
const RUN_POLL_TIMEOUT_MS = 120000;

type UnknownRecord = Record<string, unknown>;

/**
 * 处理as记录。
 * @param value 待处理的值
 * @return 处理结果
 */
function asRecord(value: unknown): UnknownRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

/**
 * 处理asString。
 * @param value 待处理的值
 * @return 处理结果
 */
function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

/**
 * 规范化响应。
 * @param raw 原始值
 * @param requestPayload 请求负载值
 * @return 处理结果
 */
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

/**
 * 处理simplify生成运行。
 * @param raw 原始值
 * @param payload 附加负载数据
 * @return 处理结果
 */
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

/**
 * 检查是否脚本结果。
 * @param raw 原始值
 */
function hasScriptResult(raw: UnknownRecord | null | undefined) {
  const run = raw ?? {};
  const scriptResult = asRecord(run.resultScript ?? run.result ?? {}) ?? {};
  const metadata = asRecord(scriptResult.metadata) ?? {};
  return Boolean(
    asString(scriptResult.scriptMarkdown) ||
    asString(scriptResult.markdownUrl) ||
    asString(metadata.scriptMarkdown),
  );
}

function runErrorMessage(raw: UnknownRecord | null | undefined) {
  const run = raw ?? {};
  const scriptResult = asRecord(run.resultScript ?? run.result ?? {}) ?? {};
  const metadata = asRecord(scriptResult.metadata) ?? {};
  return asString(scriptResult.error) || asString(metadata.error) || "脚本生成失败";
}

async function delay(ms: number) {
  await new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function waitForScriptRun(runId: string, initialRun?: UnknownRecord | null) {
  const startedAt = Date.now();
  let latest = initialRun;
  while (Date.now() - startedAt < RUN_POLL_TIMEOUT_MS) {
    if (hasScriptResult(latest)) {
      return latest;
    }
    const status = asString(latest?.status).toLowerCase();
    if (status === "failed" || status === "cancelled" || status === "canceled") {
      throw new Error(runErrorMessage(latest));
    }
    await delay(RUN_POLL_INTERVAL_MS);
    latest = asRecord(await getJson<unknown>(RUN_DETAILS_ENDPOINT(runId)));
  }
  throw new Error("脚本生成等待超时，请稍后重试");
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
    raw = await waitForScriptRun(runId, run);
  }
  const simplified = simplifyGenerationRun(asRecord(raw), payload);
  return normalizeResponse(simplified, payload);
}

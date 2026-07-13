/**
 * 生成相关 API 请求封装。
 */
import type {
  GenerateMediaRequest,
  ProbeTextAnalysisModelRequest,
  ProbeTextAnalysisModelResponse,
  VideoModelUsageResponse,
} from "@/types/generation";

import { getJson, postJson } from "./client";
import {
  asNumber,
  asRecord,
  asString,
  buildGenerationRunPayload,
  hasTerminalRunResult,
  normalizeGenerationOptions,
  normalizeMediaRunResult,
  runErrorMessage,
  runStatus,
} from "./generation-normalizers";

const CATALOG_ENDPOINT = "/api/v3/generation/catalog";
const RUNS_ENDPOINT = "/api/v3/generation/runs";
const ASPECT_RATIO_PREFERENCE_ENDPOINT = "/api/v3/generation/preferences/aspect-ratio";
/**
 * 处理RUNDETAILSENDPOINT。
 * @param runId 运行标识值
 */
const RUN_DETAILS_ENDPOINT = (runId: string) => `/api/v3/generation/runs/${encodeURIComponent(runId)}`;
const USAGE_ENDPOINT = "/api/v3/generation/usage";
const RUN_POLL_INTERVAL_MS = 1200;
const RUN_POLL_TIMEOUT_MS = 120000;

async function delay(ms: number) {
  await new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function waitForRunResult(runId: string, initialRun?: unknown) {
  const startedAt = Date.now();
  let latestRun = initialRun;
  while (Date.now() - startedAt < RUN_POLL_TIMEOUT_MS) {
    if (latestRun && hasTerminalRunResult(latestRun)) {
      return latestRun;
    }
    if (latestRun) {
      const status = runStatus(latestRun);
      if (status === "failed" || status === "cancelled" || status === "canceled") {
        throw new Error(runErrorMessage(latestRun));
      }
    }
    await delay(RUN_POLL_INTERVAL_MS);
    latestRun = await getJson<unknown>(RUN_DETAILS_ENDPOINT(runId));
  }
  throw new Error("生成任务等待超时，请稍后在任务列表中查看结果");
}

export async function fetchGenerationOptions() {
  const raw = await getJson<unknown>(CATALOG_ENDPOINT);
  return normalizeGenerationOptions(raw);
}

/**
 * 保存当前用户默认画幅。
 * @param aspectRatio 画幅比例
 */
export async function saveDefaultAspectRatio(aspectRatio: string) {
  await postJson(ASPECT_RATIO_PREFERENCE_ENDPOINT, { aspectRatio });
}

export async function generateMediaFromText(payload: GenerateMediaRequest) {
  const runPayload = buildGenerationRunPayload(payload);
  let run = await postJson<unknown>(RUNS_ENDPOINT, runPayload);
  const runRecord = asRecord(run) ?? {};
  const status = asString(runRecord.status).toLowerCase();
  if ((status === "accepted" || status === "running") && asString(runRecord.id)) {
    run = await waitForRunResult(asString(runRecord.id), run);
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
  const probe = asRecord(runRecord.result) ?? asRecord(runRecord.resultProbe) ?? {};
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

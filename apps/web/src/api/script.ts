import { postJson } from "./client";
import type { GenerateScriptRequest, GenerateScriptResponse } from "@/types";

const SCRIPT_GENERATE_ENDPOINT = "/generations/script";
const DEFAULT_VISUAL_STYLE = "AI 自动决策";

function normalizeResponse(
  raw: Partial<GenerateScriptResponse> | null | undefined,
  requestPayload: GenerateScriptRequest,
): GenerateScriptResponse {
  return {
    id: (raw?.id || "").trim() || `${Date.now()}`,
    sourceText: (raw?.sourceText || "").trim() || requestPayload.text.trim(),
    visualStyle: (raw?.visualStyle || "").trim() || requestPayload.visualStyle?.trim() || DEFAULT_VISUAL_STYLE,
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

export async function generateScriptFromText(payload: GenerateScriptRequest) {
  const backendPayload = {
    text: payload.text,
    visualStyle: payload.visualStyle?.trim() || undefined,
  };
  const raw = await postJson<GenerateScriptResponse>(SCRIPT_GENERATE_ENDPOINT, backendPayload);
  return normalizeResponse(raw, payload);
}

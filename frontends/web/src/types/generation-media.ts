import type { GenerationMediaKind } from "./generation-catalog";

export interface GenerateMediaRequest {
  prompt: string;
  mediaKind: GenerationMediaKind;
  version: number;
  textAnalysisModel?: string | null;
  providerModel?: string | null;
  imageSize?: string;
  videoSize?: string;
  videoDurationSeconds?: number;
  minDurationSeconds?: number;
  maxDurationSeconds?: number;
}

export interface GenerationModelInfo {
  provider?: string | null;
  modelName?: string | null;
  providerModel?: string | null;
  requestedModel?: string | null;
  resolvedModel?: string | null;
  textAnalysisModel?: string | null;
  endpointHost?: string | null;
  temperature?: number | null;
  maxTokens?: number | null;
  timeoutSeconds?: number | null;
  strategyVersion?: number | null;
  strategyVersionLabel?: string | null;
  strategySummary?: string | null;
  mediaKind?: GenerationMediaKind | null;
}

export interface GenerationCallLogEntry {
  timestamp: string;
  stage: string;
  event: string;
  status: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface GenerateMediaResponse {
  id: string;
  mediaKind: GenerationMediaKind;
  prompt: string;
  version: number;
  outputUrl: string;
  thumbnailUrl?: string | null;
  providerModel?: string | null;
  mimeType?: string | null;
  width?: number | null;
  height?: number | null;
  durationSeconds?: number | null;
  createdAt?: string | null;
  modelInfo?: GenerationModelInfo | null;
  callChain?: GenerationCallLogEntry[];
  metadata?: Record<string, unknown>;
}

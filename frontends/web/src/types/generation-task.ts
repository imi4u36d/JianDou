import type { EditingMode } from "./task";
import type { MaterialAssetType } from "./workflow";
import type { GenerationCallLogEntry, GenerationModelInfo } from "./generation-media";

export interface UploadResponse { assetId: string; fileName: string; fileUrl: string; sizeBytes: number; }

export interface ImageUploadResponse {
  assetId?: string | null;
  fileName?: string | null;
  fileUrl: string;
  publicUrl?: string | null;
  previewUrl?: string | null;
  sizeBytes?: number | null;
}

export interface CreateGenerationTaskRequest {
  title: string;
  taskType?: "image_generation" | "image_to_image" | "character_sheet" | "video_generation" | string | null;
  assetType?: MaterialAssetType | string | null;
  creativePrompt?: string | null;
  aspectRatio: string;
  imageSize?: string | null;
  textAnalysisModel?: string | null;
  imageModel?: string | null;
  videoModel?: string | null;
  videoSize?: string | null;
  seed?: number | null;
  videoDurationSeconds?: number | "auto" | null;
  outputCount?: number | "auto" | { auto?: boolean; count?: number | string | null } | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  transcriptText?: string | null;
  stopBeforeVideoGeneration?: boolean | null;
  referenceImageUrls?: string[];
  referenceAssetIds?: string[];
}

export interface GenerateCreativePromptRequest {
  title: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  introTemplate: string;
  outroTemplate: string;
  transcriptText?: string;
  sourceFileNames?: string[];
  editingMode?: EditingMode;
}

export interface GenerateCreativePromptResponse { prompt: string; source: string; }
export interface GenerateScriptRequest { text: string; textAnalysisModel?: string | null; }

export interface GenerateScriptResponse {
  id: string;
  sourceText: string;
  outputFormat?: "markdown";
  scriptMarkdown: string;
  markdownFilePath?: string | null;
  markdownFileUrl?: string | null;
  downloadUrl?: string | null;
  source: string;
  createdAt: string;
  modelInfo?: GenerationModelInfo | null;
  callChain?: GenerationCallLogEntry[];
  metadata?: Record<string, unknown>;
}

export interface ProbeTextAnalysisModelRequest { textAnalysisModel?: string | null; }

export interface ProbeTextAnalysisModelResponse {
  ready: boolean;
  requestedModel: string;
  resolvedModel: string;
  provider: string;
  family?: string | null;
  mode: string;
  endpointHost: string;
  latencyMs: number;
  messagePreview?: string | null;
  checkedAt: string;
}

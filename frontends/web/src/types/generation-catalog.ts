export type GenerationMediaKind = "image" | "video";

export interface GenerationVideoModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  supportsSeed?: boolean;
  generationMode?: "t2v" | "i2v" | "vl" | null;
  supportedSizes?: string[];
  supportedDurations?: number[];
}

export interface GenerationTextAnalysisModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  supportsSeed?: boolean;
  supportedSizes?: string[];
}

export interface VideoModelUsageItem {
  model: string;
  label?: string | null;
  used: number;
  unit?: string | null;
  remaining: number | null;
  remainingUnit?: string | null;
  remainingLabel?: string | null;
  quota?: number | null;
  usedDurationSeconds?: number | null;
  provider?: string | null;
  source?: string | null;
  note?: string | null;
  updatedAt?: string | null;
}

export interface VideoModelUsageResponse { items: VideoModelUsageItem[]; generatedAt?: string | null; updatedAt?: string | null; }
export interface GenerationAspectRatioOption { value: string; label: string; }
export interface GenerationImageSizeOption { value: string; label: string; width?: number; height?: number; supportedModels?: string[]; }
export interface GenerationVideoSizeOption { value: string; label: string; width?: number; height?: number; supportedModels?: string[]; }
export interface GenerationVideoDurationOption { value: number; label: string; supportedModels?: string[]; }

export interface GenerationOptionsResponse {
  aspectRatios?: GenerationAspectRatioOption[];
  defaultAspectRatio?: string | null;
  imageSizes: GenerationImageSizeOption[];
  videoModels: GenerationVideoModelInfo[];
  defaultVideoModel?: string | null;
  textAnalysisModels?: GenerationTextAnalysisModelInfo[];
  defaultTextAnalysisModel?: string | null;
  imageModels?: GenerationTextAnalysisModelInfo[];
  defaultImageModel?: string | null;
  videoSizes: GenerationVideoSizeOption[];
  videoDurations: GenerationVideoDurationOption[];
  defaultImageSize?: string;
  defaultVideoSize?: string;
  defaultVideoDurationSeconds?: number | null;
}

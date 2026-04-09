import type {
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";

export interface GenerateFormModel {
  prompt: string;
  textAnalysisModel: string;
  providerModel: string;
  videoSize: string;
  minDurationSeconds: string;
  maxDurationSeconds: string;
}

export interface GenerateFormCardProps {
  form: GenerateFormModel;
  textAnalysisModels: GenerationTextAnalysisModelInfo[];
  videoModels: GenerationVideoModelInfo[];
  selectedVideoModel?: GenerationVideoModelInfo | null;
  videoSizes: GenerationVideoSizeOption[];
  videoDurations: GenerationVideoDurationOption[];
  optionsLoading: boolean;
  optionsError: string;
  usageLoading: boolean;
  usageError: string;
  submitError: string;
  submitting: boolean;
  canSubmit: boolean;
}

export type ProgressStatus = "idle" | "running" | "paused" | "completed" | "failed";

export interface TaskProgressState {
  status: ProgressStatus;
  progress: number;
  stage: string;
  message: string;
  updatedAt: string;
}

export interface TaskProgressCardProps {
  state: TaskProgressState;
  taskId: string;
  traceCount: number;
  elapsedLabel?: string;
  resultTitle: string;
  resultMeta: string[];
  outputUrl: string;
  posterUrl: string;
}

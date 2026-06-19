/**
 * 类型组件。
 */
import type {
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";

/**
 * Generate表单模型接口定义。
 */
export interface GenerateFormModel {
  prompt: string;
  textAnalysisModel: string;
  providerModel: string;
  videoSize: string;
  minDurationSeconds: string;
  maxDurationSeconds: string;
}

/**
 * Generate表单卡片Props接口定义。
 */
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

/**
 * 进度状态。
 */
export type ProgressStatus = "idle" | "running" | "paused" | "completed" | "failed";

/**
 * 任务进度接口定义。
 */
export interface TaskProgressState {
  status: ProgressStatus;
  progress: number;
  stage: string;
  message: string;
  updatedAt: string;
}

/**
 * 任务进度卡片Props接口定义。
 */
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

import type { TaskStatus } from "./task";

export interface TaskShowcaseModels {
  textAnalysisModel?: string | null;
  imageModel?: string | null;
  videoModel?: string | null;
}

export interface TaskShowcaseMedia {
  title?: string | null;
  clipIndex?: number | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  hasAudio?: boolean | null;
}

export interface TaskShowcaseItem {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
  sourceFileName?: string | null;
  aspectRatio?: string | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  completedOutputCount?: number | null;
  taskSeed?: number | null;
  effectRating?: number | null;
  description?: string | null;
  previewUrl?: string | null;
  downloadUrl?: string | null;
  joinName?: string | null;
  models?: TaskShowcaseModels | null;
  media?: TaskShowcaseMedia | null;
}

export interface TaskShowcaseResponse {
  generatedAt: string;
  totalCompletedTasks: number;
  items: TaskShowcaseItem[];
}

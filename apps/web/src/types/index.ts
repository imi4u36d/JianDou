export type TaskStatus =
  | "PENDING"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export interface UploadResponse {
  assetId: string;
  fileName: string;
  fileUrl: string;
  sizeBytes: number;
}

export interface CreateTaskRequest {
  title: string;
  sourceAssetId: string;
  sourceFileName: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
}

export interface TaskOutput {
  id: string;
  clipIndex: number;
  title: string;
  reason: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  previewUrl: string;
  downloadUrl: string;
}

export interface TaskListItem {
  id: string;
  title: string;
  status: TaskStatus;
  platform: string;
  progress: number;
  outputCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface TaskDetail extends TaskListItem {
  sourceFileName: string;
  aspectRatio: string;
  minDurationSeconds: number;
  maxDurationSeconds: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  errorMessage?: string | null;
  outputs: TaskOutput[];
}


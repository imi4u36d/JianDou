export interface TaskOutput {
  id?: string; resultId?: string; taskId?: string; resultType?: string | null; sourceModelCallId?: string | null;
  materialAssetId?: string | null; clipIndex: number; title: string; reason: string; startSeconds: number;
  endSeconds: number; durationSeconds: number; previewUrl?: string | null; previewPath?: string | null;
  downloadUrl?: string | null; downloadPath?: string | null; remoteUrl?: string | null; mimeType?: string | null;
  width?: number | null; height?: number | null; sizeBytes?: number | null; thumbnailUrl?: string | null;
  extra?: Record<string, unknown> | null; producedAt?: string | null;
}

export interface TaskMaterial {
  id: string; taskId?: string | null; workflowId?: string | null; sourceTaskId?: string | null;
  sourceMaterialId?: string | null; stageType?: string | null; clipIndex?: number | null;
  kind: "source" | "output" | string; assetRole?: string | null; mediaType: "video" | "image" | "text" | string;
  title: string; publicUrl?: string | null; fileUrl: string; previewUrl?: string | null; thumbnailUrl?: string | null;
  mimeType?: string | null; durationSeconds?: number | null; width?: number | null; height?: number | null;
  sizeBytes?: number | null; createdAt?: string | null;
}

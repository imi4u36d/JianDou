/** Upload response contracts shared by task and material APIs. */
export interface UploadResponse {
  assetId: string;
  fileName: string;
  fileUrl: string;
  sizeBytes: number;
}

export interface ImageUploadResponse {
  assetId?: string | null;
  fileName?: string | null;
  fileUrl: string;
  publicUrl?: string | null;
  previewUrl?: string | null;
  sizeBytes?: number | null;
}

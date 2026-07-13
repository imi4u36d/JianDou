import type { WorkflowMetadataSummary, WorkflowStageType } from "./workflow-stage";

export type MaterialAssetType = "character_sheet" | "scene" | "prop" | "free" | "workflow";

export interface MaterialAssetLibraryItem {
  id: string;
  taskId?: string | null;
  workflowId?: string | null;
  stageType: WorkflowStageType;
  clipIndex: number;
  versionNo: number;
  selectedForNext: boolean;
  assetType?: MaterialAssetType | string | null;
  assetRole?: string | null;
  userRating?: number | null;
  ratingNote?: string | null;
  mediaType: "text" | "image" | "video" | string;
  title: string;
  originModel?: string | null;
  originProvider?: string | null;
  mimeType?: string | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  hasAudio?: boolean | null;
  publicUrl: string;
  fileUrl: string;
  previewUrl: string;
  thumbnailUrl?: string | null;
  remoteUrl?: string | null;
  hasRemotePath?: boolean;
  remotePath?: string | null;
  metadata?: WorkflowMetadataSummary | null;
  createdAt: string;
  updatedAt: string;
}

export interface MaterialAssetQuery {
  q?: string;
  type?: WorkflowStageType | "";
  assetType?: MaterialAssetType | "";
  minRating?: number | null;
  model?: string;
  aspectRatio?: string;
  clipIndex?: number | null;
  includeWorkflowArtifacts?: boolean;
  offset?: number;
  limit?: number;
}

export interface MaterialAssetPage {
  items: MaterialAssetLibraryItem[];
  offset: number;
  limit: number;
  total: number;
  hasMore: boolean;
  nextOffset: number | null;
}

export interface MaterialFavoriteFolder { id: string; name: string; assetIds: string[]; createdAt: string }
export interface MaterialFavoriteFolderList { folders: MaterialFavoriteFolder[] }
export interface CreateMaterialFavoriteFolderRequest { name: string; assetIds?: string[] }
export interface RenameMaterialFavoriteFolderRequest { name: string }
export interface MaterialFavoriteAssetIdsRequest { assetIds: string[] }
export interface MaterialFavoriteFolderDeleteResult { deleted: boolean; folderId: string }
export interface RenameMaterialAssetRequest { title: string }

export interface CreateMaterialGenerationRequest {
  assetType: Exclude<MaterialAssetType, "workflow">;
  title: string;
  description?: string | null;
  styleKeywords?: string[];
  aspectRatio: string;
  imageSize?: string | null;
  textAnalysisModel?: string | null;
  imageModel?: string | null;
  seed?: number | null;
  referenceImageUrls?: string[];
  referenceAssetIds?: string[];
}

export interface MaterialGenerationResponse {
  id?: string | null;
  asset?: MaterialAssetLibraryItem | null;
  assets?: MaterialAssetLibraryItem[];
  outputUrl?: string | null;
  previewUrl?: string | null;
  fileUrl?: string | null;
  title?: string | null;
  status?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface MaterialAssetDeleteResult { assetId?: string | null; deleted: boolean }

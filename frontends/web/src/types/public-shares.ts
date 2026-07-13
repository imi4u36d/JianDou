/** Public showcase sharing contracts. */
export interface PublicShareItem {
  id: string;
  shareId: string;
  materialAssetId: string;
  sourceType: "task" | "workflow" | "material" | string;
  sourceId: string;
  ownerUserId: number;
  authorName: string;
  title: string;
  mediaType: "image" | "video";
  publicUrl: string;
  fileUrl: string;
  previewUrl: string;
  thumbnailUrl?: string | null;
  width?: number | null;
  height?: number | null;
  durationSeconds?: number | null;
  likeCount: number;
  likedByMe: boolean;
  sharedAt: string;
  updatedAt: string;
  status: string;
}

export interface PublicShareListResponse {
  items: PublicShareItem[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
  nextOffset?: number | null;
}

export interface PublicShareQuery {
  type?: "image" | "video";
  offset?: number;
  limit?: number;
  sort?: "popular" | "latest";
}

export interface CreatePublicShareRequest {
  materialAssetId: string;
  sourceType: "task" | "workflow" | "material";
  sourceId: string;
}

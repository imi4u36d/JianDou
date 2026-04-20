/**
 * 素材库 API 请求封装。
 */
import { getJson, patchJson, postJson } from "./client";
import type {
  MaterialAssetLibraryItem,
  MaterialAssetQuery,
  ReuseMaterialRequest,
  UpdateMaterialAssetRatingRequest,
  UpdateMaterialAssetTagsRequest,
  WorkflowDetail,
} from "@/types";

function buildQuery(filters?: MaterialAssetQuery) {
  const params = new URLSearchParams();
  if (filters?.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters?.type?.trim()) {
    params.set("type", filters.type.trim());
  }
  if (filters?.tag?.trim()) {
    params.set("tag", filters.tag.trim());
  }
  if (typeof filters?.minRating === "number") {
    params.set("minRating", String(filters.minRating));
  }
  if (filters?.model?.trim()) {
    params.set("model", filters.model.trim());
  }
  if (filters?.aspectRatio?.trim()) {
    params.set("aspectRatio", filters.aspectRatio.trim());
  }
  if (typeof filters?.clipIndex === "number") {
    params.set("clipIndex", String(filters.clipIndex));
  }
  return params.toString();
}

export function fetchMaterialAssets(filters?: MaterialAssetQuery) {
  const query = buildQuery(filters);
  return getJson<MaterialAssetLibraryItem[]>(query ? `/material-assets?${query}` : "/material-assets");
}

export function fetchMaterialAsset(assetId: string) {
  return getJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}`);
}

export function rateMaterialAsset(assetId: string, payload: UpdateMaterialAssetRatingRequest) {
  return patchJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}/rating`, payload);
}

export function updateMaterialAssetTags(assetId: string, payload: UpdateMaterialAssetTagsRequest) {
  return patchJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}/tags`, payload);
}

export function reuseMaterialAsset(assetId: string, payload: ReuseMaterialRequest = { mode: "clone" }) {
  return postJson<WorkflowDetail>(`/material-assets/${encodeURIComponent(assetId)}/reuse`, payload);
}

/**
 * 素材库 API 请求封装。
 */
import { deleteJson, getJson, patchJson, postForm, postJson } from "./client";
import type {
  CreateMaterialGenerationRequest,
  ImageUploadResponse,
  MaterialAssetDeleteResult,
  MaterialAssetLibraryItem,
  MaterialAssetPage,
  MaterialGenerationResponse,
  MaterialAssetQuery,
  ReuseMaterialRequest,
  UpdateMaterialAssetRatingRequest,
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
  if (filters?.assetType?.trim()) {
    params.set("assetType", filters.assetType.trim());
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
  if (typeof filters?.offset === "number") {
    params.set("offset", String(filters.offset));
  }
  if (typeof filters?.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  return params.toString();
}

export function fetchMaterialAssets(filters?: MaterialAssetQuery) {
  const query = buildQuery(filters);
  return getJson<MaterialAssetLibraryItem[]>(query ? `/material-assets?${query}` : "/material-assets");
}

export function fetchMaterialAssetPage(filters?: MaterialAssetQuery) {
  const query = buildQuery(filters);
  return getJson<MaterialAssetPage>(query ? `/material-assets?${query}` : "/material-assets");
}

export function fetchMaterialAsset(assetId: string) {
  return getJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}`);
}

export function rateMaterialAsset(assetId: string, payload: UpdateMaterialAssetRatingRequest) {
  return patchJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}/rating`, payload);
}

export function reuseMaterialAsset(assetId: string, payload: ReuseMaterialRequest = { mode: "clone" }) {
  return postJson<WorkflowDetail>(`/material-assets/${encodeURIComponent(assetId)}/reuse`, payload);
}

export function uploadMaterialAsset(assetId: string) {
  return postJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}/upload`, {});
}

export function deleteMaterialAsset(assetId: string) {
  return deleteJson<MaterialAssetDeleteResult>(`/material-assets/${encodeURIComponent(assetId)}`);
}

export function createMaterialGeneration(payload: CreateMaterialGenerationRequest) {
  return postJson<MaterialGenerationResponse>("/material-center/generations", payload);
}

export function uploadImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<ImageUploadResponse>("/uploads/images", form);
}

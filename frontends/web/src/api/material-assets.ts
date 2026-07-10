/**
 * 素材库 API 请求封装。
 */
import type {
  CreateMaterialFavoriteFolderRequest,
  CreateMaterialGenerationRequest,
  MaterialAssetDeleteResult,
  MaterialAssetLibraryItem,
  MaterialAssetPage,
  MaterialAssetQuery,
  MaterialFavoriteAssetIdsRequest,
  MaterialFavoriteFolder,
  MaterialFavoriteFolderDeleteResult,
  MaterialFavoriteFolderList,
  MaterialGenerationResponse,
  RenameMaterialAssetRequest,
  RenameMaterialFavoriteFolderRequest,
  ReuseMaterialRequest,
  UpdateMaterialAssetRatingRequest,
} from "@/types/materials";
import type { ImageUploadResponse } from "@/types/uploads";
import type { WorkflowDetail } from "@/types/workflows";

import { deleteJson, getJson, patchJson, postForm, postJson } from "./client";
import { withQuery } from "./query";

function materialAssetsPath(filters?: MaterialAssetQuery) {
  return withQuery("/material-assets", {
    q: filters?.q,
    type: filters?.type,
    assetType: filters?.assetType,
    minRating: filters?.minRating,
    model: filters?.model,
    aspectRatio: filters?.aspectRatio,
    clipIndex: filters?.clipIndex,
    includeWorkflowArtifacts: filters?.includeWorkflowArtifacts,
    offset: filters?.offset,
    limit: filters?.limit,
  });
}

export async function fetchMaterialAssets(filters?: MaterialAssetQuery) {
  const result = await getJson<MaterialAssetLibraryItem[] | MaterialAssetPage>(materialAssetsPath(filters));
  return Array.isArray(result) ? result : result.items ?? [];
}

export function fetchMaterialAssetPage(filters?: MaterialAssetQuery) {
  return getJson<MaterialAssetPage>(materialAssetsPath(filters));
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

export function renameMaterialAsset(assetId: string, payload: RenameMaterialAssetRequest) {
  return patchJson<MaterialAssetLibraryItem>(`/material-assets/${encodeURIComponent(assetId)}`, payload);
}

export function fetchMaterialFavoriteFolders() {
  return getJson<MaterialFavoriteFolderList>("/material-assets/favorite-folders");
}

export function createMaterialFavoriteFolder(payload: CreateMaterialFavoriteFolderRequest) {
  return postJson<MaterialFavoriteFolder>("/material-assets/favorite-folders", payload);
}

export function renameMaterialFavoriteFolder(folderId: string, payload: RenameMaterialFavoriteFolderRequest) {
  return patchJson<MaterialFavoriteFolder>(
    `/material-assets/favorite-folders/${encodeURIComponent(folderId)}`,
    payload,
  );
}

export function deleteMaterialFavoriteFolder(folderId: string) {
  return deleteJson<MaterialFavoriteFolderDeleteResult>(
    `/material-assets/favorite-folders/${encodeURIComponent(folderId)}`,
  );
}

export function addMaterialFavoriteAssets(folderId: string, payload: MaterialFavoriteAssetIdsRequest) {
  return postJson<MaterialFavoriteFolder>(
    `/material-assets/favorite-folders/${encodeURIComponent(folderId)}/assets`,
    payload,
  );
}

export function removeMaterialFavoriteAsset(folderId: string, assetId: string) {
  return deleteJson<MaterialFavoriteFolder>(
    `/material-assets/favorite-folders/${encodeURIComponent(folderId)}/assets/${encodeURIComponent(assetId)}`,
  );
}

export function createMaterialGeneration(payload: CreateMaterialGenerationRequest) {
  return postJson<MaterialGenerationResponse>("/material-center/generations", payload);
}

export function uploadImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<ImageUploadResponse>("/uploads/images", form);
}

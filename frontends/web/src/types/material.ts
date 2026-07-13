export interface UpdateMaterialAssetRatingRequest {
  effectRating: number;
  effectRatingNote?: string | null;
}

export interface ReuseMaterialRequest {
  mode: "clone";
}

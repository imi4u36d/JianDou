import { deleteJson, getJson, postJson } from "./client";
import type { CreatePublicShareRequest, PublicShareItem, PublicShareListResponse, PublicShareQuery } from "@/types";

function queryString(query: PublicShareQuery = {}) {
  const params = new URLSearchParams();
  if (query.type) params.set("type", query.type);
  if (typeof query.offset === "number") params.set("offset", String(query.offset));
  if (typeof query.limit === "number") params.set("limit", String(query.limit));
  if (query.sort) params.set("sort", query.sort);
  const value = params.toString();
  return value ? `?${value}` : "";
}

export function fetchPublicShares(query: PublicShareQuery = {}) {
  return getJson<PublicShareListResponse>(`/public-shares${queryString(query)}`);
}

export function createPublicShare(payload: CreatePublicShareRequest) {
  return postJson<PublicShareItem>("/public-shares", payload);
}

export function deletePublicShare(shareId: string) {
  return deleteJson<{ deleted: boolean; shareId: string }>(`/public-shares/${encodeURIComponent(shareId)}`);
}

export function likePublicShare(shareId: string) {
  return postJson<PublicShareItem>(`/public-shares/${encodeURIComponent(shareId)}/like`, {});
}

export function unlikePublicShare(shareId: string) {
  return deleteJson<PublicShareItem>(`/public-shares/${encodeURIComponent(shareId)}/like`);
}

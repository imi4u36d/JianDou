import type {
  CreatePublicShareRequest,
  PublicShareItem,
  PublicShareListResponse,
  PublicShareQuery,
} from "@/types/public-shares";

import { deleteJson, getJson, postJson } from "./client";
import { withQuery } from "./query";

export function fetchPublicShares(query: PublicShareQuery = {}) {
  return getJson<PublicShareListResponse>(
    withQuery("/public-shares", {
      type: query.type,
      offset: query.offset,
      limit: query.limit,
      sort: query.sort,
    }),
  );
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

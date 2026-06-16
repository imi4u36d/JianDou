import { getJson, postJson } from "./client";
import type { AdminInvite, CreateAdminInviteRequest } from "@/types";

export async function fetchAdminInvites() {
  return getJson<AdminInvite[]>("/admin/invites");
}

export async function createAdminInvite(payload: CreateAdminInviteRequest) {
  return postJson<AdminInvite>("/admin/invites", payload);
}

export async function revokeAdminInvite(id: number) {
  return postJson<AdminInvite>(`/admin/invites/${id}/revoke`, {});
}

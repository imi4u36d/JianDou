import type {
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigResponse,
  AdminPaginatedResponse,
  AdminUser,
  AdminUserQuery,
  CreateAdminUserRequest,
  UpdateAdminUserPasswordRequest,
  UpdateAdminUserRequest,
} from "@/types/admin";

import { deleteJson, getJson, patchJson, postJson, putJson } from "@/api/client";
import { withQuery } from "@/api/query";

export async function fetchAdminUsers(query?: AdminUserQuery) {
  return getJson<AdminPaginatedResponse<AdminUser>>(
    withQuery("/admin/users", {
      q: query?.q,
      role: query?.role,
      status: query?.status,
      offset: query?.offset != null && query.offset > 0 ? query.offset : undefined,
      limit: query?.limit,
    }),
  );
}

export async function fetchAdminModelConfig() {
  return getJson<AdminModelConfigResponse>("/admin/model-config");
}

export async function fetchUserModelConfig(userId: number) {
  return getJson<AdminModelConfigResponse>(`/admin/users/${userId}/model-config`);
}

export async function createAdminUser(payload: CreateAdminUserRequest) {
  return postJson<AdminUser>("/admin/users", payload);
}

export async function updateAdminUser(id: number, payload: UpdateAdminUserRequest) {
  return patchJson<AdminUser>(`/admin/users/${id}`, payload);
}

export async function updateAdminUserPassword(id: number, payload: UpdateAdminUserPasswordRequest) {
  return patchJson<AdminUser>(`/admin/users/${id}/password`, payload);
}

export async function resetAdminUserModelConfigKeys(userId: number, payload: AdminModelConfigKeyUpdateRequest) {
  return putJson<AdminModelConfigResponse>(`/admin/users/${userId}/model-config/keys`, payload);
}

export async function enableAdminUser(id: number) {
  return postJson<AdminUser>(`/admin/users/${id}/enable`, {});
}

export async function disableAdminUser(id: number) {
  return postJson<AdminUser>(`/admin/users/${id}/disable`, {});
}

export async function deleteAdminUser(id: number) {
  return deleteJson<void>(`/admin/users/${id}`);
}

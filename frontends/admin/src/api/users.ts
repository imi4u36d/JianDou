import { deleteJson, getJson, postJson, putJson } from "./client";
import type {
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigResponse,
  AdminUser,
  AdminUserQuery,
  CreateAdminUserRequest,
  UpdateAdminUserPasswordRequest,
  UpdateAdminUserRequest
} from "@/types";

export async function fetchAdminUsers(query?: AdminUserQuery) {
  const params = new URLSearchParams();
  if (query?.q?.trim()) {
    params.set("q", query.q.trim());
  }
  if (query?.role) {
    params.set("role", query.role);
  }
  if (query?.status) {
    params.set("status", query.status);
  }
  const search = params.toString();
  return getJson<AdminUser[]>(search ? `/admin/users?${search}` : "/admin/users");
}

export async function fetchAdminModelConfig() {
  return getJson<AdminModelConfigResponse>("/admin/model-config");
}

export async function createAdminUser(payload: CreateAdminUserRequest) {
  return postJson<AdminUser>("/admin/users", payload);
}

export async function updateAdminUser(id: number, payload: UpdateAdminUserRequest) {
  return putJson<AdminUser>(`/admin/users/${id}`, payload);
}

export async function updateAdminUserPassword(id: number, payload: UpdateAdminUserPasswordRequest) {
  return putJson<AdminUser>(`/admin/users/${id}/password`, payload);
}

export async function resetAdminUserModelConfigKeys(id: number, payload: AdminModelConfigKeyUpdateRequest) {
  return postJson<void>(`/admin/users/${id}/model-config/keys`, payload);
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

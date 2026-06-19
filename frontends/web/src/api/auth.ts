/**
 * 认证相关 API 请求封装。
 */
import { getJson, postJson, putJson } from "./client";
import type {
  ActivateInviteRequest,
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigResponse,
  AdminModelConfigValidationResponse,
  AuthSession,
  LoginRequest,
} from "@/types";

export async function fetchAuthSession() {
  return getJson<AuthSession>("/auth/session");
}

export async function loginByPassword(payload: LoginRequest) {
  return postJson<AuthSession>("/auth/login", payload, { skipUnauthorizedHandler: true });
}

export async function logoutSession() {
  return postJson<{ success: boolean }>("/auth/logout", {}, { skipUnauthorizedHandler: true });
}

export async function activateInviteAccount(payload: ActivateInviteRequest) {
  return postJson<AuthSession>("/auth/activate-invite", payload, { skipUnauthorizedHandler: true });
}

export async function fetchUserModelConfig() {
  return getJson<AdminModelConfigResponse>("/admin/model-config");
}

export async function validateUserModelConfig(payload: AdminModelConfigKeyUpdateRequest) {
  return postJson<AdminModelConfigValidationResponse>("/admin/model-config/validate", payload);
}

export async function saveUserModelConfigKeys(payload: AdminModelConfigKeyUpdateRequest) {
  return putJson<AdminModelConfigResponse>("/admin/model-config/keys", payload);
}

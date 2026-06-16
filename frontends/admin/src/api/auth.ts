import { getJson, postJson } from "./client";
import type { AuthSession, LoginRequest } from "@/types";

export async function fetchAuthSession() {
  return getJson<AuthSession>("/auth/session");
}

export async function loginByPassword(payload: LoginRequest) {
  return postJson<AuthSession>("/auth/login", payload, { skipUnauthorizedHandler: true });
}

export async function logoutSession() {
  return postJson<{ success: boolean }>("/auth/logout", {}, { skipUnauthorizedHandler: true });
}

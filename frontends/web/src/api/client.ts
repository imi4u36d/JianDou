/**
 * Web 应用的共享 API client 实例。
 */
import {
  ApiClientError,
  createApiClient,
  type ApiAuthFailureHandler,
  type ApiRequestInit,
} from "@jiandou/api";
import { getRuntimeConfig } from "./runtime-config";

const apiClient = createApiClient({
  baseUrl: () => getRuntimeConfig().apiBaseUrl,
});

export { ApiClientError };
export type { ApiRequestInit };

export function setUnauthorizedHandler(handler: ApiAuthFailureHandler | null) {
  apiClient.setUnauthorizedHandler(handler);
}

export function getJson<T>(path: string) {
  return apiClient.getJson<T>(path);
}

export function postJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">) {
  return apiClient.postJson<T>(path, body, init);
}

export function postForm<T>(path: string, body: FormData, init?: Omit<ApiRequestInit, "body" | "method">) {
  return apiClient.postForm<T>(path, body, init);
}

export function patchJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">) {
  return apiClient.patchJson<T>(path, body, init);
}

export function putJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">) {
  return apiClient.putJson<T>(path, body, init);
}

export function deleteJson<T>(path: string, init?: Omit<ApiRequestInit, "method">) {
  return apiClient.deleteJson<T>(path, init);
}

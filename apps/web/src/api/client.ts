/**
 * 客户端相关 API 请求封装。
 */
import { getRuntimeConfig } from "./runtime-config";

const ABSOLUTE_URL_RE = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//;
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

type AuthFailureHandler = (error: ApiClientError) => void;

let unauthorizedHandler: AuthFailureHandler | null = null;
let pendingCsrfRefresh: Promise<void> | null = null;
let csrfTokenValue = "";

export class ApiClientError extends Error {
  status: number;
  code?: string;
  detail?: string;
  payload?: unknown;

  constructor(message: string, status: number, options?: {
    code?: string;
    detail?: string;
    payload?: unknown;
  }) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = options?.code;
    this.detail = options?.detail;
    this.payload = options?.payload;
  }
}

interface ApiRequestInit extends RequestInit {
  skipUnauthorizedHandler?: boolean;
}

/**
 * 处理解析Origin。
 * @param baseUrl 基础 URL
 */
function resolveOrigin(baseUrl: string) {
  try {
    const fallbackOrigin = typeof window !== "undefined" ? window.location.origin : "http://localhost";
    return new URL(baseUrl, fallbackOrigin).origin;
  } catch {
    return "";
  }
}

/**
 * 拼接URL。
 * @param baseUrl 基础 URL
 * @param path 路径值
 */
function joinUrl(baseUrl: string, path: string) {
  const normalizedPath = path.trim();
  if (ABSOLUTE_URL_RE.test(normalizedPath)) {
    return normalizedPath;
  }
  if (normalizedPath.startsWith("/api/")) {
    const origin = resolveOrigin(baseUrl);
    return origin ? `${origin}${normalizedPath}` : normalizedPath;
  }
  return `${baseUrl.replace(/\/+$/, "")}/${normalizedPath.replace(/^\/+/, "")}`;
}

async function readResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
}

function readCookie(name: string) {
  if (typeof document === "undefined") {
    return "";
  }
  const matched = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(`${name}=`));
  if (!matched) {
    return "";
  }
  return decodeURIComponent(matched.slice(name.length + 1));
}

function readCsrfToken() {
  return csrfTokenValue || readCookie("XSRF-TOKEN");
}

function storeCsrfTokenFromHeaders(headers: Headers) {
  const token = headers.get("X-XSRF-TOKEN");
  if (token && token.trim()) {
    csrfTokenValue = token.trim();
  }
}

function attachCsrfHeader(headers: Headers, method?: string) {
  const normalizedMethod = (method ?? "GET").toUpperCase();
  if (!MUTATING_METHODS.has(normalizedMethod) || headers.has("X-XSRF-TOKEN")) {
    return;
  }
  const token = readCsrfToken();
  if (token) {
    headers.set("X-XSRF-TOKEN", token);
  }
}

async function ensureCsrfCookie(apiBaseUrl: string, method?: string) {
  const normalizedMethod = (method ?? "GET").toUpperCase();
  if (!MUTATING_METHODS.has(normalizedMethod) || readCsrfToken()) {
    return;
  }
  if (!pendingCsrfRefresh) {
    pendingCsrfRefresh = fetch(joinUrl(apiBaseUrl, "/auth/session"), {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/json"
      }
    }).then((response) => {
      storeCsrfTokenFromHeaders(response.headers);
      return undefined;
    }).finally(() => {
      pendingCsrfRefresh = null;
    });
  }
  await pendingCsrfRefresh;
}

export function setUnauthorizedHandler(handler: AuthFailureHandler | null) {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const { apiBaseUrl } = getRuntimeConfig();
  await ensureCsrfCookie(apiBaseUrl, init?.method);
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  attachCsrfHeader(headers, init?.method);
  const response = await fetch(joinUrl(apiBaseUrl, path), {
    ...init,
    credentials: "include",
    headers
  });
  storeCsrfTokenFromHeaders(response.headers);
  if (!response.ok) {
    const body = await readResponse<{ code?: string; message?: string; detail?: string } | string | null>(response);
    let message = `请求失败（${response.status}）`;
    let code = "";
    let detail = "";
    if (typeof body === "string" && body.trim()) {
      message = body;
    } else if (body && typeof body === "object") {
      code = typeof body.code === "string" ? body.code : "";
      detail = typeof body.detail === "string" ? body.detail : "";
      if (typeof body.message === "string" && body.message.trim()) {
        message = body.message;
      } else if (detail.trim()) {
        message = detail;
      }
    }
    const error = new ApiClientError(message, response.status, {
      code,
      detail,
      payload: body
    });
    if (response.status === 401 && !init?.skipUnauthorizedHandler) {
      unauthorizedHandler?.(error);
    }
    throw error;
  }
  return readResponse<T>(response);
}

export async function getJson<T>(path: string) {
  return request<T>(path);
}

export async function postJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">) {
  return request<T>(path, {
    ...init,
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
}

export async function postForm<T>(path: string, body: FormData, init?: Omit<ApiRequestInit, "body" | "method">) {
  return request<T>(path, {
    ...init,
    method: "POST",
    body
  });
}

export async function deleteJson<T>(path: string, init?: Omit<ApiRequestInit, "method">) {
  return request<T>(path, {
    ...init,
    method: "DELETE"
  });
}

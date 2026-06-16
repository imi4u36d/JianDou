export * from "./generated";

import createOpenApiFetch, { type Client, type Middleware } from "openapi-fetch";
import type { paths } from "./generated";

const ABSOLUTE_URL_RE = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//;
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export type ApiAuthFailureHandler = (error: ApiClientError) => void;

export interface ApiErrorPayload {
  code?: string;
  message?: string;
  detail?: string;
  [key: string]: unknown;
}

export interface ApiClientErrorOptions {
  code?: string;
  detail?: string;
  payload?: unknown;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly detail?: string;
  readonly payload?: unknown;

  constructor(message: string, status: number, options?: ApiClientErrorOptions) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = options?.code;
    this.detail = options?.detail;
    this.payload = options?.payload;
  }
}

export interface ApiRequestInit extends RequestInit {
  skipUnauthorizedHandler?: boolean;
}

export interface ApiClientOptions {
  baseUrl: string | (() => string);
  fetcher?: typeof fetch;
  csrfCookieName?: string;
  csrfHeaderName?: string;
  csrfRefreshPath?: string;
  unauthorizedHandler?: ApiAuthFailureHandler | null;
}

export interface ApiClient {
  setUnauthorizedHandler(handler: ApiAuthFailureHandler | null): void;
  request<T>(path: string, init?: ApiRequestInit): Promise<T>;
  getJson<T>(path: string, init?: Omit<ApiRequestInit, "body" | "method">): Promise<T>;
  postJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">): Promise<T>;
  putJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">): Promise<T>;
  patchJson<T>(path: string, body: unknown, init?: Omit<ApiRequestInit, "body" | "method" | "headers">): Promise<T>;
  deleteJson<T>(path: string, init?: Omit<ApiRequestInit, "method">): Promise<T>;
  postForm<T>(path: string, body: FormData, init?: Omit<ApiRequestInit, "body" | "method">): Promise<T>;
}

export type OpenApiClient = Client<paths>;

export type TypedOpenApiClient = OpenApiClient & {
  setUnauthorizedHandler(handler: ApiAuthFailureHandler | null): void;
};

function defaultFetch(): typeof fetch {
  if (typeof fetch === "undefined") {
    throw new Error("Global fetch is not available. Pass a fetcher to createApiClient().");
  }
  return fetch.bind(globalThis);
}

function resolveBaseUrl(baseUrl: string | (() => string)) {
  return typeof baseUrl === "function" ? baseUrl() : baseUrl;
}

function resolveOrigin(baseUrl: string) {
  try {
    const fallbackOrigin = typeof window !== "undefined" ? window.location.origin : "http://localhost";
    return new URL(baseUrl, fallbackOrigin).origin;
  } catch {
    return "";
  }
}

export function joinApiUrl(baseUrl: string, path: string) {
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

export async function readApiResponse<T>(response: Response): Promise<T> {
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

interface CsrfSupportOptions {
  fetcher: typeof fetch;
  csrfCookieName: string;
  csrfHeaderName: string;
  csrfRefreshPath: string;
}

function createCsrfSupport(options: CsrfSupportOptions) {
  let pendingCsrfRefresh: Promise<void> | null = null;
  let csrfTokenValue = "";

  function readCsrfToken() {
    return csrfTokenValue || readCookie(options.csrfCookieName);
  }

  function storeTokenFromHeaders(headers: Headers) {
    const token = headers.get(options.csrfHeaderName);
    if (token && token.trim()) {
      csrfTokenValue = token.trim();
    }
  }

  function attachHeader(headers: Headers, method?: string) {
    const normalizedMethod = (method ?? "GET").toUpperCase();
    if (!MUTATING_METHODS.has(normalizedMethod) || headers.has(options.csrfHeaderName)) {
      return;
    }
    const token = readCsrfToken();
    if (token) {
      headers.set(options.csrfHeaderName, token);
    }
  }

  async function ensureCookie(baseUrl: string, method?: string) {
    const normalizedMethod = (method ?? "GET").toUpperCase();
    if (!MUTATING_METHODS.has(normalizedMethod) || readCsrfToken()) {
      return;
    }
    if (!pendingCsrfRefresh) {
      pendingCsrfRefresh = options.fetcher(joinApiUrl(baseUrl, options.csrfRefreshPath), {
        method: "GET",
        credentials: "include",
        headers: {
          Accept: "application/json"
        }
      }).then((response) => {
        storeTokenFromHeaders(response.headers);
        return undefined;
      }).finally(() => {
        pendingCsrfRefresh = null;
      });
    }
    await pendingCsrfRefresh;
  }

  return {
    attachHeader,
    ensureCookie,
    storeTokenFromHeaders
  };
}

function parseApiErrorPayload(body: ApiErrorPayload | string | null | undefined, status: number) {
  let message = `请求失败（${status}）`;
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

  return { message, code, detail };
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const fetcher = options.fetcher ?? defaultFetch();
  const csrfCookieName = options.csrfCookieName ?? "XSRF-TOKEN";
  const csrfHeaderName = options.csrfHeaderName ?? "X-XSRF-TOKEN";
  const csrfRefreshPath = options.csrfRefreshPath ?? "/auth/session";
  const csrfSupport = createCsrfSupport({
    fetcher,
    csrfCookieName,
    csrfHeaderName,
    csrfRefreshPath
  });

  let unauthorizedHandler = options.unauthorizedHandler ?? null;

  async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
    const baseUrl = resolveBaseUrl(options.baseUrl);
    await csrfSupport.ensureCookie(baseUrl, init?.method);

    const headers = new Headers(init?.headers);
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }
    csrfSupport.attachHeader(headers, init?.method);

    const response = await fetcher(joinApiUrl(baseUrl, path), {
      ...init,
      credentials: "include",
      headers
    });
    csrfSupport.storeTokenFromHeaders(response.headers);

    if (!response.ok) {
      const body = await readApiResponse<ApiErrorPayload | string | null>(response);
      const parsed = parseApiErrorPayload(body, response.status);
      const error = new ApiClientError(parsed.message, response.status, {
        code: parsed.code,
        detail: parsed.detail,
        payload: body
      });
      if (response.status === 401 && !init?.skipUnauthorizedHandler) {
        unauthorizedHandler?.(error);
      }
      throw error;
    }

    return readApiResponse<T>(response);
  }

  function setUnauthorizedHandler(handler: ApiAuthFailureHandler | null) {
    unauthorizedHandler = handler;
  }

  return {
    setUnauthorizedHandler,
    request,
    getJson: (path, init) => request(path, init),
    postJson: (path, body, init) => request(path, {
      ...init,
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    }),
    putJson: (path, body, init) => request(path, {
      ...init,
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    }),
    patchJson: (path, body, init) => request(path, {
      ...init,
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    }),
    deleteJson: (path, init) => request(path, {
      ...init,
      method: "DELETE"
    }),
    postForm: (path, body, init) => request(path, {
      ...init,
      method: "POST",
      body
    })
  };
}

export function createTypedApiClient(options: ApiClientOptions): TypedOpenApiClient {
  const fetcher = options.fetcher ?? defaultFetch();
  const csrfSupport = createCsrfSupport({
    fetcher,
    csrfCookieName: options.csrfCookieName ?? "XSRF-TOKEN",
    csrfHeaderName: options.csrfHeaderName ?? "X-XSRF-TOKEN",
    csrfRefreshPath: options.csrfRefreshPath ?? "/auth/session"
  });

  let unauthorizedHandler = options.unauthorizedHandler ?? null;

  const authMiddleware: Middleware = {
    async onResponse({ response }) {
      if (response.status !== 401) {
        return undefined;
      }
      const body = await readApiResponse<ApiErrorPayload | string | null>(response.clone());
      const parsed = parseApiErrorPayload(body, response.status);
      unauthorizedHandler?.(new ApiClientError(parsed.message, response.status, {
        code: parsed.code,
        detail: parsed.detail,
        payload: body
      }));
      return undefined;
    }
  };

  const client = createOpenApiFetch<paths>({
    baseUrl: resolveBaseUrl(options.baseUrl).replace(/\/+$/, ""),
    credentials: "include",
    headers: {
      Accept: "application/json"
    },
    fetch: async (request) => {
      const baseUrl = resolveBaseUrl(options.baseUrl);
      await csrfSupport.ensureCookie(baseUrl, request.method);

      const headers = new Headers(request.headers);
      if (!headers.has("Accept")) {
        headers.set("Accept", "application/json");
      }
      csrfSupport.attachHeader(headers, request.method);

      const nextRequest = new Request(request, {
        credentials: "include",
        headers
      });
      const response = await fetcher(nextRequest);
      csrfSupport.storeTokenFromHeaders(response.headers);
      return response;
    }
  });

  client.use(authMiddleware);

  return Object.assign(client, {
    setUnauthorizedHandler(handler: ApiAuthFailureHandler | null) {
      unauthorizedHandler = handler;
    }
  });
}

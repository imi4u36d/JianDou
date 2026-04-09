import { getRuntimeConfig } from "./runtime-config";

const ABSOLUTE_URL_RE = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//;

function resolveOrigin(baseUrl: string) {
  try {
    const fallbackOrigin = typeof window !== "undefined" ? window.location.origin : "http://localhost";
    return new URL(baseUrl, fallbackOrigin).origin;
  } catch {
    return "";
  }
}

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { apiBaseUrl } = getRuntimeConfig();
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  const response = await fetch(joinUrl(apiBaseUrl, path), {
    ...init,
    headers
  });
  if (!response.ok) {
    const body = await readResponse<{ message?: string; detail?: string } | string | null>(response);
    if (typeof body === "string" && body.trim()) {
      throw new Error(body);
    }
    if (body && typeof body === "object" && "message" in body && body.message) {
      throw new Error(body.message);
    }
    if (body && typeof body === "object" && "detail" in body && body.detail) {
      throw new Error(body.detail);
    }
    throw new Error(`请求失败（${response.status}）`);
  }
  return readResponse<T>(response);
}

export async function getJson<T>(path: string) {
  return request<T>(path);
}

export async function postJson<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
}

export async function postForm<T>(path: string, body: FormData) {
  return request<T>(path, {
    method: "POST",
    body
  });
}

export async function deleteJson<T>(path: string) {
  return request<T>(path, {
    method: "DELETE"
  });
}

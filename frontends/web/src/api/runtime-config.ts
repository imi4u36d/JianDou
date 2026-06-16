/**
 * 运行时配置。
 */
/**
 * 运行时配置相关 API 请求封装。
 */
export interface RuntimeConfig {
  // 前端调用后端 REST 接口时使用的基础路径。
  apiBaseUrl: string;
  // 加载上传文件和生成资源时使用的基础路径。
  storageBaseUrl: string;
  // 独立管理端访问地址。
  adminBaseUrl: string;
}

function resolveDefaultAdminBaseUrl() {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:5174";
  }
  try {
    const url = new URL(window.location.origin);
    url.port = "5174";
    return url.toString().replace(/\/$/, "");
  } catch {
    return "http://127.0.0.1:5174";
  }
}

function normalizeAdminBaseUrl(value: string, fallbackValue: string) {
  const normalizedValue = value.trim();
  if (!normalizedValue) {
    return fallbackValue;
  }
  if (typeof window === "undefined") {
    return normalizedValue;
  }
  try {
    const configuredUrl = new URL(normalizedValue, window.location.origin);
    const configuredPath = configuredUrl.pathname.replace(/\/+$/, "") || "/";
    const currentUrl = new URL(window.location.href);
    const currentPort = currentUrl.port || (currentUrl.protocol === "https:" ? "443" : "80");
    if (configuredUrl.origin === currentUrl.origin && configuredPath === "/" && currentPort !== "5174") {
      return fallbackValue;
    }
    return configuredUrl.toString().replace(/\/$/, "");
  } catch {
    return fallbackValue;
  }
}

// 在 runtime-config.json 未加载或不可用时使用的安全默认值。
function createDefaultRuntimeConfig(): RuntimeConfig {
  return {
    apiBaseUrl: "/api/v3",
    storageBaseUrl: "/storage",
    adminBaseUrl: resolveDefaultAdminBaseUrl()
  };
}

let runtimeConfig: RuntimeConfig = createDefaultRuntimeConfig();

/**
 * 检查是否非EmptyString。
 * @param value 待处理的值
 * @return 是否满足条件
 */
function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

// 允许只覆盖部分字段，其余字段回退到默认值。
/**
 * 规范化运行时配置。
 * @param config 配置值
 * @return 处理结果
 */
function normalizeRuntimeConfig(config: Partial<RuntimeConfig>): RuntimeConfig {
  const defaultRuntimeConfig = createDefaultRuntimeConfig();
  return {
    apiBaseUrl: isNonEmptyString(config.apiBaseUrl) ? config.apiBaseUrl : defaultRuntimeConfig.apiBaseUrl,
    storageBaseUrl: isNonEmptyString(config.storageBaseUrl) ? config.storageBaseUrl : defaultRuntimeConfig.storageBaseUrl,
    adminBaseUrl: normalizeAdminBaseUrl(
      isNonEmptyString(config.adminBaseUrl) ? config.adminBaseUrl : "",
      defaultRuntimeConfig.adminBaseUrl
    )
  };
}

export async function loadRuntimeConfig() {
  try {
    // 使用 Vite 的 BASE_URL 组装静态资源地址，避免在 /tasks 等子路由下被解析成相对路径。
    const basePath = import.meta.env.BASE_URL || "/";
    const runtimeConfigUrl = new URL(`runtime-config.json`, window.location.origin + basePath).toString();

    // 加载公开的运行时配置，便于部署环境在不重建前端的情况下覆盖接口地址。
    const response = await fetch(runtimeConfigUrl, {
      cache: "no-store"
    });
    if (!response.ok) {
      return runtimeConfig;
    }
    const parsed = (await response.json()) as Partial<RuntimeConfig>;
    runtimeConfig = normalizeRuntimeConfig(parsed);
  } catch {
    return runtimeConfig;
  }
  return runtimeConfig;
}

/**
 * 返回运行时配置。
 */
export function getRuntimeConfig() {
  return runtimeConfig;
}

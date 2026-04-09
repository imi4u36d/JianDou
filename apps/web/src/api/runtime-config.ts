export interface RuntimeConfig {
  // 前端调用后端 REST 接口时使用的基础路径。
  apiBaseUrl: string;
  // 加载上传文件和生成资源时使用的基础路径。
  storageBaseUrl: string;
}

// 在 runtime-config.json 未加载或不可用时使用的安全默认值。
const defaultRuntimeConfig: RuntimeConfig = {
  apiBaseUrl: "/api/v2",
  storageBaseUrl: "/storage"
};

let runtimeConfig: RuntimeConfig = { ...defaultRuntimeConfig };

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

// 允许只覆盖部分字段，其余字段回退到默认值。
function normalizeRuntimeConfig(config: Partial<RuntimeConfig>): RuntimeConfig {
  return {
    apiBaseUrl: isNonEmptyString(config.apiBaseUrl) ? config.apiBaseUrl : defaultRuntimeConfig.apiBaseUrl,
    storageBaseUrl: isNonEmptyString(config.storageBaseUrl) ? config.storageBaseUrl : defaultRuntimeConfig.storageBaseUrl
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

export function getRuntimeConfig() {
  return runtimeConfig;
}

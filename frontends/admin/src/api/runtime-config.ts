export interface RuntimeConfig {
  apiBaseUrl: string;
}

const defaultRuntimeConfig: RuntimeConfig = {
  apiBaseUrl: "/api/v3"
};

let runtimeConfig: RuntimeConfig = { ...defaultRuntimeConfig };

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeRuntimeConfig(config: Partial<RuntimeConfig>): RuntimeConfig {
  return {
    apiBaseUrl: isNonEmptyString(config.apiBaseUrl) ? config.apiBaseUrl : defaultRuntimeConfig.apiBaseUrl
  };
}

export async function loadRuntimeConfig() {
  try {
    const basePath = import.meta.env.BASE_URL || "/";
    const runtimeConfigUrl = new URL("runtime-config.json", window.location.origin + basePath).toString();
    const response = await fetch(runtimeConfigUrl, {
      cache: "no-store"
    });
    if (!response.ok) {
      return runtimeConfig;
    }
    runtimeConfig = normalizeRuntimeConfig((await response.json()) as Partial<RuntimeConfig>);
  } catch {
    return runtimeConfig;
  }
  return runtimeConfig;
}

export function getRuntimeConfig() {
  return runtimeConfig;
}

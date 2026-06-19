/**
 * 模型设置工作台辅助方法。
 */
export type TextProviderKey = "openai" | "azure" | "custom";
export type VisionProviderKey = "azure-vision" | "rekognition" | "custom-vision";
export type KeyframeProviderKey = "openai-image" | "flux" | "custom-keyframe";
export type VideoProviderKey = "seedance" | "runway" | "custom-video";

export interface TextProviderProfile {
  label: string;
  modelVersion: string;
  endpoint: string;
  apiKey: string;
}

export interface ModelSettings {
  text: {
    activeProvider: TextProviderKey;
    profiles: Record<TextProviderKey, TextProviderProfile>;
  };
  vision: {
    provider: VisionProviderKey;
    endpoint: string;
    apiKey: string;
  };
  keyframe: {
    provider: KeyframeProviderKey;
    endpoint: string;
    apiKey: string;
  };
  video: {
    provider: VideoProviderKey;
    endpoint: string;
    apiKey: string;
  };
  updatedAt: string;
}

const STORAGE_KEY = "jiandou-model-settings-v1";
const UPDATE_EVENT = "jiandou:model-settings-updated";

const DEFAULT_SETTINGS: ModelSettings = {
  text: {
    activeProvider: "openai",
    profiles: {
      openai: {
        label: "OpenAI GPT-4",
        modelVersion: "gpt-4o-mini",
        endpoint: "https://api.openai.com/v1",
        apiKey: "",
      },
      azure: {
        label: "Azure OpenAI",
        modelVersion: "gpt-4.1",
        endpoint: "",
        apiKey: "",
      },
      custom: {
        label: "自定义端点",
        modelVersion: "custom-chat",
        endpoint: "",
        apiKey: "",
      },
    },
  },
  vision: {
    provider: "azure-vision",
    endpoint: "",
    apiKey: "",
  },
  keyframe: {
    provider: "openai-image",
    endpoint: "",
    apiKey: "",
  },
  video: {
    provider: "seedance",
    endpoint: "",
    apiKey: "",
  },
  updatedAt: "",
};

function sanitizeTextProfile(value: unknown, fallback: TextProviderProfile): TextProviderProfile {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { ...fallback };
  }
  const record = value as Record<string, unknown>;
  return {
    label: typeof record.label === "string" && record.label.trim() ? record.label.trim() : fallback.label,
    modelVersion: typeof record.modelVersion === "string" && record.modelVersion.trim() ? record.modelVersion.trim() : fallback.modelVersion,
    endpoint: typeof record.endpoint === "string" ? record.endpoint.trim() : fallback.endpoint,
    apiKey: typeof record.apiKey === "string" ? record.apiKey.trim() : fallback.apiKey,
  };
}

function sanitizeProviderKey<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && allowed.includes(value as T) ? (value as T) : fallback;
}

function sanitizeSimpleSection<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallbackProvider: T,
  fallbackEndpoint: string,
  fallbackApiKey: string,
) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      provider: fallbackProvider,
      endpoint: fallbackEndpoint,
      apiKey: fallbackApiKey,
    };
  }
  const record = value as Record<string, unknown>;
  return {
    provider: sanitizeProviderKey(record.provider, allowed, fallbackProvider),
    endpoint: typeof record.endpoint === "string" ? record.endpoint.trim() : fallbackEndpoint,
    apiKey: typeof record.apiKey === "string" ? record.apiKey.trim() : fallbackApiKey,
  };
}

/**
 * 规范化模型设置。
 * @param value 待处理的值
 * @return 处理结果
 */
export function normalizeModelSettings(value: unknown): ModelSettings {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return JSON.parse(JSON.stringify(DEFAULT_SETTINGS)) as ModelSettings;
  }
  const record = value as Record<string, unknown>;
  const text = record.text && typeof record.text === "object" && !Array.isArray(record.text) ? (record.text as Record<string, unknown>) : {};
  const profiles = text.profiles && typeof text.profiles === "object" && !Array.isArray(text.profiles)
    ? (text.profiles as Record<string, unknown>)
    : {};

  return {
    text: {
      activeProvider: sanitizeProviderKey<TextProviderKey>(text.activeProvider, ["openai", "azure", "custom"], DEFAULT_SETTINGS.text.activeProvider),
      profiles: {
        openai: sanitizeTextProfile(profiles.openai, DEFAULT_SETTINGS.text.profiles.openai),
        azure: sanitizeTextProfile(profiles.azure, DEFAULT_SETTINGS.text.profiles.azure),
        custom: sanitizeTextProfile(profiles.custom, DEFAULT_SETTINGS.text.profiles.custom),
      },
    },
    vision: sanitizeSimpleSection<VisionProviderKey>(
      record.vision,
      ["azure-vision", "rekognition", "custom-vision"],
      DEFAULT_SETTINGS.vision.provider,
      DEFAULT_SETTINGS.vision.endpoint,
      DEFAULT_SETTINGS.vision.apiKey,
    ),
    keyframe: sanitizeSimpleSection<KeyframeProviderKey>(
      record.keyframe,
      ["openai-image", "flux", "custom-keyframe"],
      DEFAULT_SETTINGS.keyframe.provider,
      DEFAULT_SETTINGS.keyframe.endpoint,
      DEFAULT_SETTINGS.keyframe.apiKey,
    ),
    video: sanitizeSimpleSection<VideoProviderKey>(
      record.video,
      ["seedance", "runway", "custom-video"],
      DEFAULT_SETTINGS.video.provider,
      DEFAULT_SETTINGS.video.endpoint,
      DEFAULT_SETTINGS.video.apiKey,
    ),
    updatedAt: typeof record.updatedAt === "string" ? record.updatedAt : "",
  };
}

/**
 * 加载模型设置。
 * @return 处理结果
 */
export function loadModelSettings(): ModelSettings {
  if (typeof window === "undefined") {
    return normalizeModelSettings(DEFAULT_SETTINGS);
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return normalizeModelSettings(raw ? JSON.parse(raw) : DEFAULT_SETTINGS);
  } catch {
    return normalizeModelSettings(DEFAULT_SETTINGS);
  }
}

/**
 * 保存模型设置。
 * @param settings 待持久化的设置
 * @return 处理结果
 */
export function saveModelSettings(settings: ModelSettings): ModelSettings {
  const next = normalizeModelSettings({
    ...settings,
    updatedAt: new Date().toISOString(),
  });
  if (typeof window === "undefined") {
    return next;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent<ModelSettings>(UPDATE_EVENT, { detail: next }));
  } catch {
    // 忽略持久化失败，避免设置写入影响主流程。
  }
  return next;
}

/**
 * 订阅模型设置变更。
 * @param listener 监听器
 * @return 取消订阅函数
 */
export function subscribeModelSettings(listener: (settings: ModelSettings) => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  const handler = (event: Event) => {
    const detail = (event as CustomEvent<ModelSettings>).detail;
    listener(normalizeModelSettings(detail));
  };
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

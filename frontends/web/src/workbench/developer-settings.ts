/**
 * Developer接口定义。
 */
/**
 * developer设置工作台辅助方法。
 */
export interface DeveloperSettings {
  stopBeforeVideoGeneration: boolean;
}

const STORAGE_KEY = "jiandou-developer-settings-v1";
const UPDATE_EVENT = "jiandou:developer-settings-updated";

const DEFAULT_SETTINGS: DeveloperSettings = {
  stopBeforeVideoGeneration: false,
};

/**
 * 规范化设置。
 * @param value 待处理的值
 * @return 处理结果
 */
function normalizeSettings(value: unknown): DeveloperSettings {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { ...DEFAULT_SETTINGS };
  }
  const record = value as Record<string, unknown>;
  return {
    stopBeforeVideoGeneration: Boolean(record.stopBeforeVideoGeneration),
  };
}

/**
 * 加载Developer设置。
 * @return 处理结果
 */
export function loadDeveloperSettings(): DeveloperSettings {
  if (typeof window === "undefined") {
    return { ...DEFAULT_SETTINGS };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return normalizeSettings(raw ? JSON.parse(raw) : null);
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

/**
 * 保存Developer设置。
 * @param settings 待持久化的设置
 */
export function saveDeveloperSettings(settings: DeveloperSettings) {
  const next = normalizeSettings(settings);
  if (typeof window === "undefined") {
    return next;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent<DeveloperSettings>(UPDATE_EVENT, { detail: next }));
  } catch {
    // 忽略持久化失败，避免设置写入影响主流程。
  }
  return next;
}

/**
 * 处理subscribeDeveloper设置。
 * @param listener listener值
 */
export function subscribeDeveloperSettings(listener: (settings: DeveloperSettings) => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  /**
   * 处理处理器。
   * @param event 事件名称
   */
  const handler = (event: Event) => {
    const detail = (event as CustomEvent<DeveloperSettings>).detail;
    listener(normalizeSettings(detail));
  };
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

/**
 * 判断是否StopBefore视频生成。
 * @param settings 待持久化的设置
 * @return 是否满足条件
 */
export function shouldStopBeforeVideoGeneration(settings?: DeveloperSettings | null): boolean {
  const resolved = settings ? normalizeSettings(settings) : DEFAULT_SETTINGS;
  return resolved.stopBeforeVideoGeneration;
}

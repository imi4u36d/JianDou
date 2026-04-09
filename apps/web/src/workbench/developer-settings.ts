export interface DeveloperSettings {
  enabled: boolean;
  stopBeforeVideoGeneration: boolean;
}

const STORAGE_KEY = "ai-cut-developer-settings-v1";
const UPDATE_EVENT = "ai-cut:developer-settings-updated";

const DEFAULT_SETTINGS: DeveloperSettings = {
  enabled: false,
  stopBeforeVideoGeneration: false,
};

function normalizeSettings(value: unknown): DeveloperSettings {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { ...DEFAULT_SETTINGS };
  }
  const record = value as Record<string, unknown>;
  return {
    enabled: Boolean(record.enabled),
    stopBeforeVideoGeneration: Boolean(record.stopBeforeVideoGeneration),
  };
}

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

export function saveDeveloperSettings(settings: DeveloperSettings) {
  const next = normalizeSettings(settings);
  if (typeof window === "undefined") {
    return next;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent<DeveloperSettings>(UPDATE_EVENT, { detail: next }));
  } catch {
    // Ignore persistence failures.
  }
  return next;
}

export function subscribeDeveloperSettings(listener: (settings: DeveloperSettings) => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  const handler = (event: Event) => {
    const detail = (event as CustomEvent<DeveloperSettings>).detail;
    listener(normalizeSettings(detail));
  };
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

export function shouldStopBeforeVideoGeneration(settings?: DeveloperSettings | null): boolean {
  const resolved = settings ? normalizeSettings(settings) : loadDeveloperSettings();
  return resolved.enabled && resolved.stopBeforeVideoGeneration;
}

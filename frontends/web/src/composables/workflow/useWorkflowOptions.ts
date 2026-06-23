import { ref, computed } from "vue";
import { fetchGenerationOptions } from "@/features/workflows";
import type { GenerationOptionsResponse, GenerationVideoSizeOption } from "@/types";

export function useWorkflowOptions() {
  const loadingOptions = ref(false);
  const options = ref<GenerationOptionsResponse | null>(null);

  const aspectRatioOptions = computed(() => options.value?.aspectRatios ?? [
    { value: "16:9", label: "16:9" },
    { value: "9:16", label: "9:16" },
  ]);
  const stylePresetOptions = computed(() => options.value?.stylePresets ?? []);
  const textModelOptions = computed(() => options.value?.textAnalysisModels ?? []);
  const imageModelOptions = computed(() => options.value?.imageModels ?? []);
  const videoModelOptions = computed(() => options.value?.videoModels ?? []);
  const catalogVideoSizeOptions = computed(() => options.value?.videoSizes ?? []);

  function normalizeModelName(value?: string | null): string {
    return String(value ?? "").trim().toLowerCase();
  }

  function resolveVideoSizeAspectRatio(size: GenerationVideoSizeOption): "9:16" | "16:9" | null {
    const width = Number(size.width ?? 0);
    const height = Number(size.height ?? 0);
    if (width > 0 && height > 0) {
      return width > height ? "16:9" : "9:16";
    }
    const normalized = String(size.value ?? "").replace(/\*/g, "x").toLowerCase();
    const [rawWidth, rawHeight] = normalized.split("x");
    const parsedWidth = Number(rawWidth);
    const parsedHeight = Number(rawHeight);
    if (parsedWidth > 0 && parsedHeight > 0) {
      return parsedWidth > parsedHeight ? "16:9" : "9:16";
    }
    return null;
  }

  function compareVideoSizeByArea(a: GenerationVideoSizeOption, b: GenerationVideoSizeOption): number {
    const areaA = Number(a.width ?? 0) * Number(a.height ?? 0);
    const areaB = Number(b.width ?? 0) * Number(b.height ?? 0);
    return areaA - areaB;
  }

  function filterVideoSizeOptions(source: GenerationVideoSizeOption[], model: string, aspectRatio: string): GenerationVideoSizeOption[] {
    const selectedModel = normalizeModelName(model);
    const filtered = source
      .filter((item) => {
        const itemAspectRatio = resolveVideoSizeAspectRatio(item);
        return !itemAspectRatio || itemAspectRatio === aspectRatio;
      })
      .filter((item) => {
        if (!selectedModel) return true;
        const supportedModels = Array.isArray(item.supportedModels) ? item.supportedModels : [];
        if (!supportedModels.length) return true;
        return supportedModels.some((itemModel) => normalizeModelName(itemModel) === selectedModel);
      });
    return [...filtered].sort(compareVideoSizeByArea);
  }

  function syncVideoSizeSelection(target: { videoSize: string; videoModel: string; aspectRatio: string }, preferred?: string | null) {
    if (!catalogVideoSizeOptions.value.length) return;
    const available = filterVideoSizeOptions(catalogVideoSizeOptions.value, target.videoModel, target.aspectRatio);
    if (!available.length) {
      target.videoSize = "";
      return;
    }
    const preferredValue = preferred || "";
    const next =
      available.find((item) => item.value === preferredValue)?.value
      ?? available.find((item) => item.value === target.videoSize)?.value
      ?? available[0].value;
    target.videoSize = next;
  }

  function valueOptionLabel<T extends { value: string; label: string }>(opts: T[], value?: string | null, fallback = "-"): string {
    if (!value) return fallback;
    return opts.find((item) => item.value === value)?.label || value;
  }

  function keyOptionLabel<T extends { key: string; label: string }>(opts: T[], value?: string | null, fallback = "-"): string {
    if (!value) return fallback;
    return opts.find((item) => item.key === value)?.label || value;
  }

  async function loadOptions() {
    loadingOptions.value = true;
    try {
      const result = await fetchGenerationOptions();
      options.value = result;
      return result;
    } finally {
      loadingOptions.value = false;
    }
  }

  return {
    loadingOptions,
    options,
    aspectRatioOptions,
    stylePresetOptions,
    textModelOptions,
    imageModelOptions,
    videoModelOptions,
    catalogVideoSizeOptions,
    normalizeModelName,
    resolveVideoSizeAspectRatio,
    compareVideoSizeByArea,
    filterVideoSizeOptions,
    syncVideoSizeSelection,
    valueOptionLabel,
    keyOptionLabel,
    loadOptions,
  };
}

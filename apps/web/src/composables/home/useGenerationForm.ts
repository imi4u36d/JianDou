import { computed, ref, watch, type Ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { fetchCreditSummary, fetchGenerationOptions } from "@/features/home";
import type {
  CreateGenerationTaskRequest,
  CreditSummary,
  GenerationImageSizeOption,
  GenerationOptionsResponse,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ModeValue = "video" | "image" | "character_sheet";
export type AspectRatioValue = "16:9" | "9:16";
export type RatioOptionValue = "智能" | "1:1" | "21:9" | "16:9" | "3:2" | "4:3" | "3:4" | "2:3" | "9:16";

export type WorkbenchForm = Omit<CreateGenerationTaskRequest, "aspectRatio"> & {
  aspectRatio: RatioOptionValue;
  imageSize?: string | null;
};

export interface ModeOption {
  value: ModeValue;
  kind: "video" | "image";
  label: string;
  description: string;
  iconSvg: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const modeIconSvgs: Record<ModeValue, string> = {
  video: `
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4.5" y="5.5" width="10" height="13" rx="3" />
      <path d="m14.5 10 4.5-2.8v9.6L14.5 14" />
    </svg>
  `,
  image: `
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4.5" y="5.5" width="15" height="13" rx="3" />
      <path d="M8 14.5 10.8 11.7 13.3 14.2 15.3 12.2 18 14.9" />
      <circle cx="10" cy="9.4" r="1.3" />
    </svg>
  `,
  character_sheet: `
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7.2 7.6a2.8 2.8 0 1 1 5.6 0a2.8 2.8 0 0 1-5.6 0Z" />
      <path d="M4.8 17.2c.8-2.4 2.7-3.6 5.2-3.6s4.4 1.2 5.2 3.6" />
      <path d="M17.6 6.7v10.6" />
      <path d="M17.6 6.7c1 0 1.8.8 1.8 1.8s-.8 1.8-1.8 1.8" />
    </svg>
  `,
};

const modeOptions: ModeOption[] = [
  {
    value: "video",
    kind: "video",
    label: "视频生成",
    description: "输入文本，自动拆分脚本、关键帧和视频",
    iconSvg: modeIconSvgs.video,
  },
  {
    value: "image",
    kind: "image",
    label: "图片生成",
    description: "素材中心自由模式，支持参考图再创作",
    iconSvg: modeIconSvgs.image,
  },
  {
    value: "character_sheet",
    kind: "image",
    label: "角色三视图",
    description: "生成同一角色正面、侧面、背面设定图",
    iconSvg: modeIconSvgs.character_sheet,
  },
];

const ratioDisplayOrder: RatioOptionValue[] = ["智能", "21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"];
const sizeRatioCandidates: RatioOptionValue[] = ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"];

const videoOutputCountOptions = [1, 2, 3, 4, 6, 8, 10, 12];
const imageOutputCountOptions = [1, 2, 3, 4];

// ---------------------------------------------------------------------------
// Pure utility functions
// ---------------------------------------------------------------------------

export function normalizeModelName(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replace(/[\s._-]/g, "");
}

export function normalizeSizeValue(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replace(/\*/g, "x");
}

export function parseSeed(value: unknown): number | null {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return null;
  }
  const numeric = Number(raw);
  if (!Number.isFinite(numeric) || !Number.isInteger(numeric) || numeric < 0) {
    return null;
  }
  return Math.trunc(numeric);
}

export function createRandomSeed() {
  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    return Math.max(1, values[0] % 2147483647);
  }
  return Math.max(1, Math.floor(Math.random() * 2147483647));
}

export function parseSize(item: { value: string; width?: number; height?: number }) {
  if (typeof item.width === "number" && typeof item.height === "number" && item.width > 0 && item.height > 0) {
    return { width: item.width, height: item.height };
  }
  const matched = String(item.value ?? "").match(/^(\d+)\s*[xX*]\s*(\d+)$/);
  if (!matched) {
    return null;
  }
  const width = Number(matched[1]);
  const height = Number(matched[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return null;
  }
  return { width, height };
}

export function resolveVideoSizeRatio(item: { value: string; width?: number; height?: number }): AspectRatioValue | null {
  const parsed = parseSize(item);
  if (!parsed || parsed.width === parsed.height) {
    return null;
  }
  return parsed.width > parsed.height ? "16:9" : "9:16";
}

export function imageSizeMatchesRatio(item: GenerationImageSizeOption, ratio: string) {
  if (ratio === "智能") {
    return true;
  }
  const itemRatio = sizeRatioLabel(item);
  return itemRatio === ratio;
}

export function compareSizeByArea(a: { value: string; width?: number; height?: number }, b: { value: string; width?: number; height?: number }) {
  const aSize = parseSize(a);
  const bSize = parseSize(b);
  const aArea = aSize ? aSize.width * aSize.height : 0;
  const bArea = bSize ? bSize.width * bSize.height : 0;
  return aArea - bArea;
}

export function sizeRatioLabel(item: { value: string; width?: number; height?: number }): RatioOptionValue | null {
  const parsed = parseSize(item);
  if (!parsed) {
    return null;
  }
  const actual = parsed.width / parsed.height;
  const best = sizeRatioCandidates
    .map((value) => {
      const target = ratioValue(value);
      return target ? { value, delta: Math.abs(actual - target) / target } : null;
    })
    .filter((item): item is { value: RatioOptionValue; delta: number } => Boolean(item))
    .sort((a, b) => a.delta - b.delta)[0];
  return best && best.delta <= 0.03 ? best.value : null;
}

export function ratioShape(value: RatioOptionValue) {
  if (value === "智能") {
    return "1 / 1";
  }
  return value.replace(":", " / ");
}

export function ratioValue(value: RatioOptionValue) {
  if (value === "智能") {
    return null;
  }
  const [width, height] = value.split(":").map(Number);
  if (!Number.isFinite(width) || !Number.isFinite(height) || height <= 0) {
    return null;
  }
  return width / height;
}

export function videoAspectRatio(value: RatioOptionValue): AspectRatioValue {
  return value === "9:16" ? "9:16" : "16:9";
}

export function imageQualityLabel(item: { value: string; label?: string | null; width?: number; height?: number }) {
  const label = String(item.label ?? "");
  if (/\b4K\b/i.test(label)) {
    return "超清 4K";
  }
  if (/\b2K\b/i.test(label)) {
    return "高清 2K";
  }
  if (/\b1K\b/i.test(label)) {
    return "标准 1K";
  }
  const size = parseSize(item);
  if (!size) {
    return String(item.value ?? "");
  }
  const longest = Math.max(size.width, size.height);
  if (longest >= 2800) {
    return "超清 4K";
  }
  if (longest >= 1800) {
    return "高清 2K";
  }
  return "标准 1K";
}

function modelOptionDescription(model: { description?: string | null; provider?: string | null; family?: string | null; value: string }) {
  return model.description || model.provider || model.family || model.value;
}

function formatCreditBalance(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

export function resolveDefaultImageModel(models: GenerationTextAnalysisModelInfo[], current?: string | null) {
  const currentValue = String(current ?? "").trim();
  if (currentValue && models.some((item) => item.value === currentValue)) {
    return currentValue;
  }
  const gptModel = models.find((item) => [item.family, item.provider, item.value, item.label].map(normalizeModelName).some((value) => value.includes("gpt")));
  return gptModel?.value || models[0]?.value || null;
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export interface UseGenerationFormOptions {
  promptText: Ref<string>;
}

export function useGenerationForm(formOptions: UseGenerationFormOptions) {
  const { promptText } = formOptions;

  // ---------------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------------

  const authState = useAuthSessionState();

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const selectedModeValue = ref<ModeValue>("image");
  const loadingOptions = ref(false);
  const credits = ref<CreditSummary | null>(null);
  const seedMode = ref<"auto" | "manual">("auto");
  const seedInput = ref("");
  const autoSeed = ref(createRandomSeed());
  const durationMode = ref<"auto" | "manual">("auto");
  const selectedDurationSeconds = ref<number | null>(null);
  const imageOutputCount = ref(1);
  const options = ref<GenerationOptionsResponse | null>(null);
  const form = ref<WorkbenchForm>({
    title: "工作台生成任务",
    creativePrompt: "",
    aspectRatio: "16:9",
    textAnalysisModel: null,
    imageModel: null,
    videoModel: null,
    videoSize: null,
    imageSize: null,
    outputCount: "auto",
    seed: null,
    videoDurationSeconds: "auto",
    transcriptText: "",
  });

  // ---------------------------------------------------------------------------
  // Computed properties
  // ---------------------------------------------------------------------------

  const selectedMode = computed(() => modeOptions.find((item) => item.value === selectedModeValue.value) ?? modeOptions[0]);

  const promptLabel = computed(() => selectedMode.value.kind === "video" ? "文本 / 小说正文" : "图片提示词");

  const showPromptPlaceholder = computed(() => !promptText.value.trim());

  const textModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.textAnalysisModels ?? []);

  const imageModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.imageModels ?? []);

  const videoModelOptions = computed<GenerationVideoModelInfo[]>(() => options.value?.videoModels ?? []);

  const selectedImageModelOption = computed(() => {
    const selected = normalizeModelName(form.value.imageModel);
    return imageModelOptions.value.find((item) => normalizeModelName(item.value) === selected) ?? null;
  });

  const selectedVideoModelOption = computed(() => {
    const selected = normalizeModelName(form.value.videoModel);
    return videoModelOptions.value.find((item) => normalizeModelName(item.value) === selected) ?? null;
  });

  const selectedPrimaryModelLabel = computed(() => {
    if (selectedMode.value.kind === "video") {
      return selectedVideoModelOption.value?.label || selectedVideoModelOption.value?.value || "视频模型";
    }
    return selectedImageModelOption.value?.label || selectedImageModelOption.value?.value || "图片模型";
  });

  const creditLabel = computed(() => {
    if (!authState.isAuthenticated.value || !credits.value) {
      return "";
    }
    if (credits.value.exempt) {
      return "积分免扣";
    }
    return `积分 ${formatCreditBalance(credits.value.balance ?? 0)}`;
  });

  const ratioOptions = computed(() => {
    const values = selectedMode.value.kind === "image" ? availableImageRatios.value : availableVideoRatios.value;
    return [...values]
      .sort((a, b) => ratioDisplayOrder.indexOf(a) - ratioDisplayOrder.indexOf(b))
      .map((value) => ({
        value,
        label: value,
        shortLabel: value === "智能" ? "智能" : value,
        shape: ratioShape(value),
      }));
  });

  const availableVideoRatios = computed<RatioOptionValue[]>(() => {
    const catalog = options.value?.aspectRatios ?? [];
    const values = catalog
      .map((item) => item.value)
      .filter((value): value is AspectRatioValue => value === "16:9" || value === "9:16");
    return values.length ? [...new Set(values)] : ["16:9", "9:16"];
  });

  const availableImageRatios = computed<RatioOptionValue[]>(() => {
    const ratios = imageCandidateSizes.value
      .map((item) => sizeRatioLabel(item))
      .filter((value): value is RatioOptionValue => Boolean(value));
    const unique = [...new Set(ratios)];
    const available = unique.length ? unique : availableVideoRatios.value;
    return ["智能", ...available.filter((value) => value !== "智能")];
  });

  const imageCandidateSizes = computed<GenerationImageSizeOption[]>(() => {
    const source = options.value?.imageSizes ?? [];
    const selectedSizes = selectedImageModelOption.value?.supportedSizes ?? [];
    const normalizedSelectedSizes = selectedSizes.map(normalizeSizeValue);
    return source.filter((item) => {
      return !normalizedSelectedSizes.length || normalizedSelectedSizes.includes(normalizeSizeValue(item.value));
    });
  });

  const imageSizeOptions = computed<GenerationImageSizeOption[]>(() => {
    const filtered = imageCandidateSizes.value
      .filter((item) => imageSizeMatchesRatio(item, form.value.aspectRatio))
      .sort(compareSizeByArea);
    return filtered;
  });

  const videoSizeOptions = computed<GenerationVideoSizeOption[]>(() => {
    const selectedModel = normalizeModelName(form.value.videoModel);
    const ratio = videoAspectRatio(form.value.aspectRatio);
    return (options.value?.videoSizes ?? [])
      .filter((item) => resolveVideoSizeRatio(item) === ratio)
      .filter((item) => {
        const supportedModels = Array.isArray(item.supportedModels) ? item.supportedModels : [];
        return !selectedModel || !supportedModels.length || supportedModels.some((model) => normalizeModelName(model) === selectedModel);
      })
      .sort(compareSizeByArea);
  });

  const durationOptions = computed<GenerationVideoDurationOption[]>(() => {
    const modelDurations = selectedVideoModelOption.value?.supportedDurations ?? [];
    if (modelDurations.length) {
      return [...new Set(modelDurations)]
        .filter((item) => Number.isFinite(item) && item > 0)
        .sort((a, b) => a - b)
        .map((item) => ({ value: Math.trunc(item), label: `${Math.trunc(item)} 秒` }));
    }
    return [...(options.value?.videoDurations ?? [])].sort((a, b) => a.value - b.value);
  });

  const durationLabel = computed(() => {
    if (durationMode.value === "auto") {
      return "自动时长";
    }
    return selectedDurationSeconds.value ? `${selectedDurationSeconds.value}s` : "选择时长";
  });

  const outputCountLabel = computed(() => form.value.outputCount === "auto" ? "自动分镜" : `${form.value.outputCount} 段`);

  const selectedImageSizeOption = computed(() => {
    return imageSizeOptions.value.find((item) => item.value === form.value.imageSize) ?? null;
  });

  const selectedImageSizeDimensions = computed(() => {
    return selectedImageSizeOption.value ? parseSize(selectedImageSizeOption.value) : null;
  });

  const selectedVideoSizeOption = computed(() => {
    return videoSizeOptions.value.find((item) => item.value === form.value.videoSize) ?? null;
  });

  const selectedVideoSizeDimensions = computed(() => {
    return selectedVideoSizeOption.value ? parseSize(selectedVideoSizeOption.value) : null;
  });

  const selectedMaterialAssetType = computed(() => selectedMode.value.value === "character_sheet" ? "character_sheet" : "free");

  const ratioToolLabel = computed(() => {
    if (selectedMode.value.kind === "image") {
      const quality = selectedImageSizeOption.value ? imageQualityLabel(selectedImageSizeOption.value) : "";
      return [form.value.aspectRatio, quality].filter(Boolean).join(" | ") || form.value.aspectRatio;
    }
    return form.value.aspectRatio;
  });

  const parsedManualSeed = computed(() => parseSeed(seedInput.value));

  const seedCapabilityHint = computed(() => {
    if (selectedMode.value.kind === "image" && !selectedImageModelOption.value?.supportsSeed) {
      return "当前图片模型未声明支持种子，提交时不会传 seed。";
    }
    return "当前设置会记录到本次生成任务。";
  });

  const isSeedReady = computed(() => seedMode.value === "auto" || parsedManualSeed.value !== null);

  const isFormReady = computed(() => {
    if (!promptText.value.trim()) {
      return false;
    }
    if (!form.value.textAnalysisModel || !form.value.imageModel) {
      return false;
    }
    if (selectedMode.value.kind === "video" && (!form.value.videoModel || !form.value.videoSize)) {
      return false;
    }
    if (selectedMode.value.kind === "image" && !form.value.imageSize) {
      return false;
    }
    return isSeedReady.value;
  });

  const submitLabel = computed(() => {
    return selectedMode.value.kind === "video" ? "生成视频" : selectedMode.value.value === "character_sheet" ? "生成三视图" : "生成图片";
  });

  // ---------------------------------------------------------------------------
  // Functions
  // ---------------------------------------------------------------------------

  function refreshAutoSeed() {
    autoSeed.value = createRandomSeed();
  }

  function formatImageSizeOptionLabel(item: GenerationImageSizeOption) {
    const label = imageQualityLabel(item);
    const quality = label.includes("4K") ? `${label} ✦` : label;
    const ratio = sizeRatioLabel(item);
    return form.value.aspectRatio === "智能" && ratio ? `${quality} · ${ratio}` : quality;
  }

  function resolvedImageAspectRatioForSubmit() {
    if (form.value.aspectRatio !== "智能") {
      return form.value.aspectRatio;
    }
    return selectedImageSizeOption.value ? sizeRatioLabel(selectedImageSizeOption.value) ?? "1:1" : "1:1";
  }

  async function loadOptions() {
    loadingOptions.value = true;
    try {
      const result = await fetchGenerationOptions();
      options.value = result;
      form.value.aspectRatio = (result.defaultAspectRatio as AspectRatioValue | null) || "16:9";
      form.value.textAnalysisModel = result.defaultTextAnalysisModel || result.textAnalysisModels?.[0]?.value || null;
      form.value.imageModel = resolveDefaultImageModel(result.imageModels ?? [], form.value.imageModel);
      form.value.videoModel = result.defaultVideoModel || result.videoModels?.[0]?.value || null;
      selectedDurationSeconds.value = result.defaultVideoDurationSeconds ?? result.videoDurations?.[0]?.value ?? null;
    } catch (error) {
      throw error;
    } finally {
      loadingOptions.value = false;
    }
  }

  async function loadCredits() {
    if (!authState.isAuthenticated.value) {
      credits.value = null;
      return;
    }
    try {
      credits.value = await fetchCreditSummary();
    } catch {
      credits.value = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Watches
  // ---------------------------------------------------------------------------

  watch(
    () => [selectedModeValue.value, imageSizeOptions.value] as const,
    ([, items]) => {
      if (selectedMode.value.kind !== "image") {
        return;
      }
      if (!items.length) {
        form.value.imageSize = null;
        return;
      }
      const configured = options.value?.defaultImageSize;
      const currentValid = form.value.imageSize && items.some((item) => item.value === form.value.imageSize);
      if (!currentValid) {
        form.value.imageSize = items.find((item) => item.value === configured)?.value ?? items[0].value;
      }
    },
    { immediate: true },
  );

  watch(
    videoSizeOptions,
    (items) => {
      if (!items.length) {
        form.value.videoSize = null;
        return;
      }
      const configured = options.value?.defaultVideoSize;
      const currentValid = form.value.videoSize && items.some((item) => item.value === form.value.videoSize);
      if (!currentValid) {
        form.value.videoSize = items.find((item) => item.value === configured)?.value ?? items[0].value;
      }
    },
    { immediate: true },
  );

  watch(seedMode, (mode, previousMode) => {
    if (mode === "auto" && previousMode !== "auto") {
      refreshAutoSeed();
    }
  });

  // ---------------------------------------------------------------------------
  // Return
  // ---------------------------------------------------------------------------

  return {
    // Types / constants
    modeOptions,
    videoOutputCountOptions,
    imageOutputCountOptions,

    // State
    form,
    selectedModeValue,
    seedMode,
    seedInput,
    autoSeed,
    durationMode,
    selectedDurationSeconds,
    imageOutputCount,
    options,
    loadingOptions,
    credits,

    // Computed - mode & model
    selectedMode,
    promptLabel,
    showPromptPlaceholder,
    textModelOptions,
    imageModelOptions,
    videoModelOptions,
    selectedImageModelOption,
    selectedVideoModelOption,
    selectedPrimaryModelLabel,
    creditLabel,

    // Computed - ratio & size
    ratioOptions,
    availableVideoRatios,
    availableImageRatios,
    imageCandidateSizes,
    imageSizeOptions,
    videoSizeOptions,
    durationOptions,
    durationLabel,
    outputCountLabel,
    selectedImageSizeOption,
    selectedImageSizeDimensions,
    selectedVideoSizeOption,
    selectedVideoSizeDimensions,
    selectedMaterialAssetType,
    ratioToolLabel,

    // Computed - seed & form readiness
    parsedManualSeed,
    seedCapabilityHint,
    isSeedReady,
    isFormReady,
    submitLabel,

    // Functions
    normalizeModelName,
    normalizeSizeValue,
    parseSeed,
    createRandomSeed,
    refreshAutoSeed,
    parseSize,
    resolveVideoSizeRatio,
    imageSizeMatchesRatio,
    compareSizeByArea,
    sizeRatioLabel,
    ratioShape,
    ratioValue,
    videoAspectRatio,
    imageQualityLabel,
    formatImageSizeOptionLabel,
    resolvedImageAspectRatioForSubmit,
    loadOptions,
    loadCredits,
    resolveDefaultImageModel,
    modelOptionDescription,
    formatCreditBalance,
  };
}

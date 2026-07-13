import { computed, ref, watch, type Ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { fetchCreditSummary, fetchGenerationOptions } from "@/features/home";
import type { CreditSummary, GenerationOptionsResponse } from "@/types";
import {
  compareSizeByArea,
  createRandomSeed,
  formatCreditBalance,
  imageOutputCountOptions,
  imageQualityLabel,
  imageSizeMatchesRatio,
  isOpenAIModel,
  modeOptions,
  modelOptionDescription,
  normalizeModelName,
  normalizeSizeValue,
  parseSeed,
  parseSize,
  ratioShape,
  ratioValue,
  resolveDefaultImageModel,
  resolveVideoSizeRatio,
  sizeRatioLabel,
  videoAspectRatio,
  videoOutputCountOptions,
  type ModeValue,
  type RatioOptionValue,
  type WorkbenchForm,
} from "./generationFormOptions";
import { useGenerationFormCatalog } from "./useGenerationFormCatalog";
import { useGenerationFormPresentation } from "./useGenerationFormPresentation";

export * from "./generationFormOptions";

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

  const promptLabel = computed(() => selectedMode.value.kind === "video" ? "视频提示词" : "图片提示词");

  const showPromptPlaceholder = computed(() => !promptText.value.trim());

  const {
    textModelOptions,
    imageModelOptions,
    videoModelOptions,
    selectedImageModelOption,
    selectedVideoModelOption,
    ratioOptions,
    availableVideoRatios,
    availableImageRatios,
    imageCandidateSizes,
    imageSizeOptions,
    videoSizeOptions,
    durationOptions,
    selectedImageSizeOption,
    selectedImageSizeDimensions,
    selectedVideoSizeOption,
    selectedVideoSizeDimensions,
  } = useGenerationFormCatalog({ options, form, selectedMode });

  const {
    selectedPrimaryModelLabel,
    creditLabel,
    durationLabel,
    outputCountLabel,
    selectedMaterialAssetType,
    ratioToolLabel,
    parsedManualSeed,
    seedCapabilityHint,
    isSeedReady,
    isFormReady,
    submitLabel,
    formatImageSizeOptionLabel,
    resolvedImageAspectRatioForSubmit,
  } = useGenerationFormPresentation({
    authenticated: () => authState.isAuthenticated.value,
    promptText,
    form,
    selectedMode,
    selectedImageModel: selectedImageModelOption,
    selectedVideoModel: selectedVideoModelOption,
    credits,
    seedMode,
    seedInput,
    durationMode,
    selectedDurationSeconds,
  });

  // ---------------------------------------------------------------------------
  // Functions
  // ---------------------------------------------------------------------------

  function refreshAutoSeed() {
    autoSeed.value = createRandomSeed();
  }

  async function loadOptions() {
    loadingOptions.value = true;
    try {
      const result = await fetchGenerationOptions();
      options.value = result;
      form.value.aspectRatio = (result.defaultAspectRatio as RatioOptionValue | null) || "16:9";
      const openAITextModels = (result.textAnalysisModels ?? []).filter(isOpenAIModel);
      const openAIImageModels = (result.imageModels ?? []).filter(isOpenAIModel);
      form.value.textAnalysisModel = openAITextModels.some((item) => item.value === result.defaultTextAnalysisModel)
        ? result.defaultTextAnalysisModel || null
        : openAITextModels[0]?.value || null;
      form.value.imageModel = resolveDefaultImageModel(openAIImageModels, form.value.imageModel);
      form.value.videoModel = result.defaultVideoModel || result.videoModels?.[0]?.value || null;
      selectedDurationSeconds.value = result.defaultVideoDurationSeconds ?? result.videoDurations?.[0]?.value ?? null;
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
    selectedModeValue,
    () => {
      if (selectedMode.value.kind === "image") {
        form.value.imageSize = null;
        return;
      }
      if (form.value.aspectRatio !== "16:9" && form.value.aspectRatio !== "9:16") {
        form.value.aspectRatio = videoAspectRatio(form.value.aspectRatio);
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

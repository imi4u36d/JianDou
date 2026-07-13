import { computed, type ComputedRef, type Ref } from "vue";
import type {
  GenerationImageSizeOption,
  GenerationOptionsResponse,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";
import {
  compareSizeByArea,
  imageSizeMatchesRatio,
  isOpenAIModel,
  normalizeModelName,
  normalizeSizeValue,
  parseSize,
  ratioDisplayOrder,
  ratioShape,
  resolveVideoSizeRatio,
  sizeRatioLabel,
  videoAspectRatio,
  type AspectRatioValue,
  type ModeOption,
  type RatioOptionValue,
  type WorkbenchForm,
} from "./generationFormOptions";

interface GenerationFormCatalogOptions {
  options: Ref<GenerationOptionsResponse | null>;
  form: Ref<WorkbenchForm>;
  selectedMode: ComputedRef<ModeOption>;
}

export function useGenerationFormCatalog({ options, form, selectedMode }: GenerationFormCatalogOptions) {
  const textModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() =>
    (options.value?.textAnalysisModels ?? []).filter(isOpenAIModel),
  );
  const imageModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() =>
    (options.value?.imageModels ?? []).filter(isOpenAIModel),
  );
  const videoModelOptions = computed<GenerationVideoModelInfo[]>(() => options.value?.videoModels ?? []);
  const selectedImageModelOption = computed(() => {
    const selected = normalizeModelName(form.value.imageModel);
    return imageModelOptions.value.find((item) => normalizeModelName(item.value) === selected) ?? null;
  });
  const selectedVideoModelOption = computed(() => {
    const selected = normalizeModelName(form.value.videoModel);
    return videoModelOptions.value.find((item) => normalizeModelName(item.value) === selected) ?? null;
  });
  const availableVideoRatios = computed<RatioOptionValue[]>(() => {
    const values = (options.value?.aspectRatios ?? [])
      .map((item) => item.value)
      .filter((value): value is AspectRatioValue => value === "16:9" || value === "9:16");
    return values.length ? [...new Set(values)] : ["16:9", "9:16"];
  });
  const imageCandidateSizes = computed<GenerationImageSizeOption[]>(() => {
    const selectedSizes = selectedImageModelOption.value?.supportedSizes ?? [];
    const normalizedSelectedSizes = selectedSizes.map(normalizeSizeValue);
    return (options.value?.imageSizes ?? []).filter(
      (item) => !normalizedSelectedSizes.length || normalizedSelectedSizes.includes(normalizeSizeValue(item.value)),
    );
  });
  const availableImageRatios = computed<RatioOptionValue[]>(() => {
    const unique = [
      ...new Set(
        imageCandidateSizes.value
          .map((item) => sizeRatioLabel(item))
          .filter((value): value is RatioOptionValue => Boolean(value)),
      ),
    ];
    return (unique.length ? unique : availableVideoRatios.value).filter((value) => value !== "智能");
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
  const imageSizeOptions = computed<GenerationImageSizeOption[]>(() =>
    imageCandidateSizes.value
      .filter((item) => imageSizeMatchesRatio(item, form.value.aspectRatio))
      .sort(compareSizeByArea),
  );
  const videoSizeOptions = computed<GenerationVideoSizeOption[]>(() => {
    const selectedModel = normalizeModelName(form.value.videoModel);
    const ratio = videoAspectRatio(form.value.aspectRatio);
    return (options.value?.videoSizes ?? [])
      .filter((item) => resolveVideoSizeRatio(item) === ratio)
      .filter((item) => {
        const supportedModels = Array.isArray(item.supportedModels) ? item.supportedModels : [];
        return (
          !selectedModel ||
          !supportedModels.length ||
          supportedModels.some((model) => normalizeModelName(model) === selectedModel)
        );
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
  const selectedImageSizeOption = computed(
    () => imageSizeOptions.value.find((item) => item.value === form.value.imageSize) ?? null,
  );
  const selectedVideoSizeOption = computed(
    () => videoSizeOptions.value.find((item) => item.value === form.value.videoSize) ?? null,
  );

  return {
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
    selectedImageSizeDimensions: computed(() =>
      selectedImageSizeOption.value ? parseSize(selectedImageSizeOption.value) : null,
    ),
    selectedVideoSizeOption,
    selectedVideoSizeDimensions: computed(() =>
      selectedVideoSizeOption.value ? parseSize(selectedVideoSizeOption.value) : null,
    ),
  };
}

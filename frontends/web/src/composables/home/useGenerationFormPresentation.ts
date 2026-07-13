import { computed, type ComputedRef, type Ref } from "vue";
import type {
  CreditSummary,
  GenerationImageSizeOption,
  GenerationTextAnalysisModelInfo,
  GenerationVideoModelInfo,
} from "@/types";
import {
  formatCreditBalance,
  imageQualityLabel,
  parseSeed,
  sizeRatioLabel,
  type ModeOption,
  type WorkbenchForm,
} from "./generationFormOptions";

export interface GenerationFormPresentationOptions {
  authenticated: () => boolean;
  promptText: Ref<string>;
  form: Ref<WorkbenchForm>;
  selectedMode: ComputedRef<ModeOption>;
  selectedImageModel: ComputedRef<GenerationTextAnalysisModelInfo | null>;
  selectedVideoModel: ComputedRef<GenerationVideoModelInfo | null>;
  credits: Ref<CreditSummary | null>;
  seedMode: Ref<"auto" | "manual">;
  seedInput: Ref<string>;
  durationMode: Ref<"auto" | "manual">;
  selectedDurationSeconds: Ref<number | null>;
}

export function useGenerationFormPresentation(options: GenerationFormPresentationOptions) {
  const selectedPrimaryModelLabel = computed(() => {
    const model = options.selectedMode.value.kind === "video"
      ? options.selectedVideoModel.value
      : options.selectedImageModel.value;
    return model?.label || model?.value || (options.selectedMode.value.kind === "video" ? "视频模型" : "图片模型");
  });
  const creditLabel = computed(() => {
    if (!options.authenticated() || !options.credits.value) return "";
    if (options.credits.value.exempt) return "积分免扣";
    return `积分 ${formatCreditBalance(options.credits.value.balance ?? 0)}`;
  });
  const durationLabel = computed(() => {
    if (options.durationMode.value === "auto") return "自动时长";
    return options.selectedDurationSeconds.value
      ? `${options.selectedDurationSeconds.value}s`
      : "选择时长";
  });
  const outputCountLabel = computed(() =>
    options.form.value.outputCount === "auto" ? "自动分镜" : `${options.form.value.outputCount} 段`,
  );
  const selectedMaterialAssetType = computed(() =>
    options.selectedMode.value.value === "character_sheet" ? "character_sheet" : "free",
  );
  const ratioToolLabel = computed(() => options.form.value.aspectRatio);
  const parsedManualSeed = computed(() => parseSeed(options.seedInput.value));
  const seedCapabilityHint = computed(() => {
    if (options.selectedMode.value.kind === "video") return "视频任务会使用当前画幅创建阶段工作流。";
    if (!options.selectedImageModel.value?.supportsSeed) {
      return "当前图片模型未声明支持种子，提交时不会传 seed。";
    }
    return "当前设置会记录到本次 OpenAI 图片生成任务。";
  });
  const isSeedReady = computed(() =>
    options.seedMode.value === "auto" || parsedManualSeed.value !== null,
  );
  const isFormReady = computed(() => {
    const form = options.form.value;
    if (!options.promptText.value.trim() || !form.textAnalysisModel || !form.imageModel) return false;
    if (options.selectedMode.value.kind === "video" && (!form.videoModel || !form.videoSize)) return false;
    return isSeedReady.value;
  });
  const submitLabel = computed(() => {
    if (options.selectedMode.value.kind === "video") return "生成视频";
    return options.selectedMode.value.value === "character_sheet" ? "生成三视图" : "生成图片";
  });

  function formatImageSizeOptionLabel(item: GenerationImageSizeOption) {
    const label = imageQualityLabel(item);
    const quality = label.includes("4K") ? `${label} ✦` : label;
    const ratio = sizeRatioLabel(item);
    return options.form.value.aspectRatio === "智能" && ratio ? `${quality} · ${ratio}` : quality;
  }

  function resolvedImageAspectRatioForSubmit() {
    return options.form.value.aspectRatio === "智能" ? "1:1" : options.form.value.aspectRatio;
  }

  return {
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
  };
}

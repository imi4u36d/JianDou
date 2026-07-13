import { computed, ref } from "vue";
import { describe, expect, it } from "vitest";
import { useGenerationFormPresentation } from "@/composables/home/useGenerationFormPresentation";
import { modeOptions, type ModeValue, type WorkbenchForm } from "@/composables/home/generationFormOptions";
import type { CreditSummary, GenerationTextAnalysisModelInfo, GenerationVideoModelInfo } from "@/types";

describe("generation form presentation", () => {
  it("derives labels, seed policy and mode-specific readiness", () => {
    const selectedModeValue = ref<ModeValue>("image");
    const selectedMode = computed(
      () => modeOptions.find((item) => item.value === selectedModeValue.value) ?? modeOptions[0],
    );
    const form = ref({
      title: "task",
      creativePrompt: "",
      aspectRatio: "16:9",
      textAnalysisModel: "gpt-5.5",
      imageModel: "gpt-image-2",
      videoModel: "video-1",
      videoSize: null,
      imageSize: null,
      outputCount: "auto",
      seed: null,
      videoDurationSeconds: "auto",
      transcriptText: "",
    } as WorkbenchForm);
    const promptText = ref("生成一个雨夜镜头");
    const seedMode = ref<"auto" | "manual">("manual");
    const seedInput = ref("");
    const presentation = useGenerationFormPresentation({
      authenticated: () => true,
      promptText,
      form,
      selectedMode,
      selectedImageModel: computed(() => ({
        value: "gpt-image-2",
        label: "GPT Image",
        supportsSeed: true,
      }) as GenerationTextAnalysisModelInfo),
      selectedVideoModel: computed(() => ({ value: "video-1", label: "Video" }) as GenerationVideoModelInfo),
      credits: ref({ balance: 12, exempt: false } as CreditSummary),
      seedMode,
      seedInput,
      durationMode: ref("auto"),
      selectedDurationSeconds: ref(null),
    });

    expect(presentation.creditLabel.value).toBe("积分 12");
    expect(presentation.isFormReady.value).toBe(false);
    seedInput.value = "42";
    expect(presentation.isFormReady.value).toBe(true);

    selectedModeValue.value = "video";
    expect(presentation.selectedPrimaryModelLabel.value).toBe("Video");
    expect(presentation.isFormReady.value).toBe(false);
    form.value.videoSize = "1920x1080";
    expect(presentation.isFormReady.value).toBe(true);
    expect(presentation.submitLabel.value).toBe("生成视频");
  });
});

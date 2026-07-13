import { computed, ref } from "vue";
import { describe, expect, it } from "vitest";
import { useGenerationFormCatalog } from "@/composables/home/useGenerationFormCatalog";
import {
  modeOptions,
  type ModeValue,
  type WorkbenchForm,
} from "@/composables/home/generationFormOptions";
import type { GenerationOptionsResponse } from "@/types";

describe("generation form catalog", () => {
  it("derives model-specific image sizes and switches to video sizes", () => {
    const selectedModeValue = ref<ModeValue>("image");
    const selectedMode = computed(
      () => modeOptions.find((item) => item.value === selectedModeValue.value) ?? modeOptions[0],
    );
    const form = ref<WorkbenchForm>({
      title: "task",
      creativePrompt: "prompt",
      aspectRatio: "1:1",
      textAnalysisModel: "gpt-5.5",
      imageModel: "gpt-image-2",
      videoModel: "video-1",
      videoSize: null,
      imageSize: "1024x1024",
      outputCount: "auto",
      seed: null,
      videoDurationSeconds: "auto",
      transcriptText: "",
    });
    const options = ref({
      textAnalysisModels: [{ value: "gpt-5.5", label: "GPT" }],
      imageModels: [
        { value: "gpt-image-2", label: "GPT Image", supportedSizes: ["1024x1024"] },
      ],
      videoModels: [{ value: "video-1", label: "Video", supportedDurations: [5, 10] }],
      imageSizes: [
        { value: "1024x1024", label: "1K" },
        { value: "1536x1024", label: "3:2" },
      ],
      videoSizes: [
        { value: "1920x1080", label: "1080p", supportedModels: ["video-1"] },
        { value: "1080x1920", label: "1080p", supportedModels: ["video-1"] },
      ],
      videoDurations: [],
      aspectRatios: [{ value: "16:9" }, { value: "9:16" }],
    } as unknown as GenerationOptionsResponse);

    const catalog = useGenerationFormCatalog({ options, form, selectedMode });
    expect(catalog.imageSizeOptions.value.map((item) => item.value)).toEqual(["1024x1024"]);
    expect(catalog.availableImageRatios.value).toEqual(["1:1"]);
    expect(catalog.selectedImageSizeDimensions.value).toEqual({ width: 1024, height: 1024 });

    selectedModeValue.value = "video";
    form.value.aspectRatio = "9:16";
    expect(catalog.videoSizeOptions.value.map((item) => item.value)).toEqual(["1080x1920"]);
    expect(catalog.durationOptions.value.map((item) => item.value)).toEqual([5, 10]);
  });
});

import { describe, expect, it } from "vitest";
import type { GenerationOptionsResponse } from "@/types";
import {
  defaultTaskAspectRatio,
  preferredModelValue,
  preferredVideoSizeValue,
  toAspectRatioOptions,
  videoSizeAspectRatio,
} from "@/views/unified/features/create-task-options";

function catalog(overrides: Partial<GenerationOptionsResponse> = {}): GenerationOptionsResponse {
  return {
    imageSizes: [],
    videoModels: [],
    videoSizes: [],
    videoDurations: [],
    ...overrides,
  };
}

describe("create task option rules", () => {
  it("normalizes aspect-ratio options and rejects unavailable defaults", () => {
    const options = toAspectRatioOptions(catalog({
      aspectRatios: [{ value: "1:1", label: "方形" }, { value: "16:9", label: "横屏" }],
    }));

    expect(options).toEqual([{ value: "1:1", label: "方形" }, { value: "16:9", label: "横屏" }]);
    expect(defaultTaskAspectRatio(options, "9:16")).toBe("16:9");
    expect(defaultTaskAspectRatio(options, "1:1")).toBe("1:1");
  });

  it("prefers a model by searchable provider metadata", () => {
    const models = [
      { value: "fallback", label: "Fallback", provider: "local" },
      { value: "preferred", label: "Primary", provider: "OpenAI" },
    ];

    expect(preferredModelValue(models, "openai")).toBe("preferred");
    expect(preferredModelValue(models, "missing")).toBe("fallback");
  });

  it("derives orientation from explicit dimensions or encoded values", () => {
    expect(videoSizeAspectRatio("ignored", 1920, 1080)).toBe("16:9");
    expect(videoSizeAspectRatio("1080*1920")).toBe("9:16");
    expect(videoSizeAspectRatio("invalid")).toBe("");
  });

  it("selects a video size compatible with both model and aspect ratio", () => {
    const options = catalog({
      defaultVideoSize: "1920x1080",
      videoSizes: [
        { value: "1920x1080", label: "Landscape", supportedModels: ["other"] },
        { value: "1080x1920", label: "Portrait", supportedModels: ["agnes"] },
        { value: "1280x720", label: "Compatible", supportedModels: ["Agnes"] },
      ],
    });

    expect(preferredVideoSizeValue(options, "agnes", "16:9")).toBe("1280x720");
    expect(preferredVideoSizeValue(options, "agnes", "9:16")).toBe("1080x1920");
  });
});

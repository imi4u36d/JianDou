import { describe, expect, it } from "vitest";
import {
  imageQualityLabel,
  imageSizeMatchesRatio,
  normalizeModelName,
  parseSeed,
  parseSize,
  resolveDefaultImageModel,
  resolveVideoSizeRatio,
  sizeRatioLabel,
} from "@/composables/home/generationFormOptions";

describe("generation form options", () => {
  it("normalizes model names and validates seeds", () => {
    expect(normalizeModelName(" GPT_Image-2 ")).toBe("gptimage2");
    expect(parseSeed("42")).toBe(42);
    expect(parseSeed("-1")).toBeNull();
    expect(parseSeed("1.5")).toBeNull();
  });

  it("derives dimensions and aspect ratios from catalog sizes", () => {
    expect(parseSize({ value: "1920*1080" })).toEqual({ width: 1920, height: 1080 });
    expect(resolveVideoSizeRatio({ value: "1080x1920" })).toBe("9:16");
    expect(sizeRatioLabel({ value: "3504x2336" })).toBe("3:2");
    expect(imageSizeMatchesRatio({ value: "1024x1024", label: "1K" }, "1:1")).toBe(true);
  });

  it("labels image quality and prefers a GPT image model", () => {
    expect(imageQualityLabel({ value: "3840x2160" })).toBe("超清 4K");
    expect(
      resolveDefaultImageModel([
        { value: "other", label: "Other" },
        { value: "gpt-image-2", label: "GPT Image 2", family: "gpt-image" },
      ]),
    ).toBe("gpt-image-2");
  });
});

import { describe, it, expect } from "vitest";
import { clampProgress, formatDateTime, formatAspectRatioLabel, formatVideoSizeLabel } from "@/utils/presentation";
import { formatTaskOutputCount, getTaskResolutionRow } from "@/utils/task-request";

describe("clampProgress", () => {
  it("clamps values below 0 to 0", () => {
    expect(clampProgress(-5)).toBe(0);
  });

  it("clamps values above 100 to 100", () => {
    expect(clampProgress(150)).toBe(100);
  });

  it("returns the value when within range", () => {
    expect(clampProgress(42)).toBe(42);
  });

  it("rounds to the nearest integer", () => {
    expect(clampProgress(42.7)).toBe(43);
    expect(clampProgress(42.3)).toBe(42);
  });

  it("returns 0 for null or undefined", () => {
    expect(clampProgress(null)).toBe(0);
    expect(clampProgress(undefined)).toBe(0);
  });

  it("returns 0 for non-finite values", () => {
    expect(clampProgress(NaN)).toBe(0);
    expect(clampProgress(Infinity)).toBe(0);
  });
});

describe("formatDateTime", () => {
  it("returns '暂无' for empty input", () => {
    expect(formatDateTime(null)).toBe("暂无");
    expect(formatDateTime(undefined)).toBe("暂无");
    expect(formatDateTime("")).toBe("暂无");
  });

  it("formats valid ISO date strings", () => {
    const result = formatDateTime("2026-06-21T10:30:00Z");
    expect(result).toBeTruthy();
    expect(result).not.toBe("暂无");
  });

  it("returns original string for unparseable values", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });
});

describe("formatAspectRatioLabel", () => {
  it("returns default text for falsy values", () => {
    expect(formatAspectRatioLabel(null)).toBe("未指定比例");
    expect(formatAspectRatioLabel("")).toBe("未指定比例");
  });

  it("returns Chinese label for 9:16", () => {
    expect(formatAspectRatioLabel("9:16")).toBe("竖屏 9:16");
  });

  it("returns Chinese label for 16:9", () => {
    expect(formatAspectRatioLabel("16:9")).toBe("横屏 16:9");
  });

  it("returns the original value for unknown ratios", () => {
    expect(formatAspectRatioLabel("1:1")).toBe("1:1");
  });
});

describe("formatVideoSizeLabel", () => {
  it("returns fallback for empty input", () => {
    expect(formatVideoSizeLabel("")).toBe("未选择");
    expect(formatVideoSizeLabel(null)).toBe("未选择");
  });

  it("extracts pixel height from 1080p notation", () => {
    expect(formatVideoSizeLabel("1080p")).toBe("1080P");
    expect(formatVideoSizeLabel("720p")).toBe("720P");
  });

  it("extracts pixel height from dimension notation", () => {
    expect(formatVideoSizeLabel("1920x1080")).toBe("1080P");
    expect(formatVideoSizeLabel("1280*720")).toBe("720P");
  });

  it("returns normalized value for unrecognized format", () => {
    expect(formatVideoSizeLabel("4K")).toBe("4K");
  });
});

describe("formatTaskOutputCount", () => {
  it("formats structured auto output counts", () => {
    expect(formatTaskOutputCount({ outputCount: { auto: true } })).toBe("自动");
  });

  it("formats structured fixed output counts", () => {
    expect(formatTaskOutputCount({ outputCount: { auto: false, count: 3 } })).toBe("3 条");
  });
});

describe("getTaskResolutionRow", () => {
  it("uses imageSize for image tasks", () => {
    expect(getTaskResolutionRow({ taskType: "image_generation", imageSize: "3840x2160", videoSize: "" })).toEqual({
      label: "图片尺寸策略",
      value: "3840x2160",
    });
  });

  it("describes auto image dimensions when imageSize is omitted", () => {
    expect(getTaskResolutionRow({ taskType: "image_generation", imageSize: "", videoSize: "" })).toEqual({
      label: "图片尺寸策略",
      value: "按上游实际返回",
    });
  });

  it("uses actual image size from execution context when available", () => {
    expect(
      getTaskResolutionRow(
        { taskType: "image_generation", imageSize: "", videoSize: "" },
        { actualImageSize: "864x1821" },
      ),
    ).toEqual({
      label: "图片实际尺寸",
      value: "864x1821",
    });
  });

  it("uses videoSize for video tasks", () => {
    expect(getTaskResolutionRow({ taskType: "video_generation", imageSize: "1024x1024", videoSize: "720*1280" })).toEqual({
      label: "视频清晰度",
      value: "720*1280",
    });
  });
});

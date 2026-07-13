import { describe, expect, it } from "vitest";
import type { GenerateMediaRequest } from "@/types";
import {
  buildGenerationRunPayload,
  hasTerminalRunResult,
  normalizeGenerationOptions,
  normalizeMediaRunResult,
  parseImageSize,
  runErrorMessage,
} from "@/api/generation-normalizers";

const imageRequest: GenerateMediaRequest = {
  prompt: "雨夜街口",
  mediaKind: "image",
  version: 2,
  imageSize: "1280*720",
  providerModel: "image-model",
};

describe("generation normalizers", () => {
  it("parses valid sizes and uses safe defaults for invalid input", () => {
    expect(parseImageSize("1280x720")).toEqual({ width: 1280, height: 720 });
    expect(parseImageSize("invalid")).toEqual({ width: 1024, height: 1024 });
  });

  it("builds the provider-neutral run contract", () => {
    expect(buildGenerationRunPayload(imageRequest)).toEqual({
      kind: "image",
      input: { prompt: "雨夜街口", version: 2, width: 1280, height: 720 },
      model: { providerModel: "image-model", textAnalysisModel: undefined },
    });
  });

  it("normalizes catalog defaults without treating zero as missing", () => {
    const options = normalizeGenerationOptions({
      aspectRatios: [{ value: "16:9", label: "横屏" }],
      defaultVideoDurationSeconds: "0",
    });

    expect(options.aspectRatios).toHaveLength(1);
    expect(options.defaultVideoDurationSeconds).toBe(0);
    expect(options.videoModels).toEqual([]);
  });

  it("maps terminal results and extracts failure messages", () => {
    const raw = {
      id: "run-1",
      kind: "image",
      input: { version: 3 },
      result: {
        outputUrl: "/result.png",
        modelInfo: { provider: "openai", providerModel: "resolved-image" },
        callChain: [{
          timestamp: "2026-07-11T00:00:00Z",
          stage: "image",
          event: "completed",
          status: "SUCCEEDED",
          message: "done",
        }],
      },
    };

    expect(hasTerminalRunResult(raw)).toBe(true);
    expect(normalizeMediaRunResult(raw, imageRequest)).toMatchObject({
      id: "run-1",
      version: 3,
      outputUrl: "/result.png",
      providerModel: "resolved-image",
    });
    expect(runErrorMessage({ result: { metadata: { taskMessage: "provider failed" } } }))
      .toBe("provider failed");
  });
});

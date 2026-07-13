import { describe, expect, it } from "vitest";
import type { StageVersion, WorkflowSummary } from "@/types";
import {
  compactVideoVersionError,
  keyframePreviewFrames,
  workflowNavStatusLabel,
  workflowNavUpdatedLabel,
} from "@/features/workflows/stage-workflow-presenters";

describe("stage workflow presenters", () => {
  it("uses auto-pilot state ahead of the workflow status", () => {
    const workflow = {
      status: "DRAFT",
      autoPilotState: "RUNNING",
    } as WorkflowSummary;

    expect(workflowNavStatusLabel(workflow)).toBe("自动执行");
  });

  it("normalizes provider errors into concise user-facing messages", () => {
    const version = {
      outputSummary: { error: "Request timed out while waiting for provider" },
    } as StageVersion;

    expect(compactVideoVersionError(version)).toBe("生成超时");
  });

  it("builds first and last frame preview items", () => {
    const version = {
      clipIndex: 1,
      selected: true,
      outputSummary: {
        startFrameUrl: "https://example.test/start.png",
        endFrameUrl: "https://example.test/end.png",
      },
    } as StageVersion;

    expect(keyframePreviewFrames(version)).toEqual([
      {
        role: "first",
        label: "首帧",
        url: "https://example.test/start.png",
        selected: true,
        regenerable: true,
      },
      {
        role: "last",
        label: "尾帧",
        url: "https://example.test/end.png",
        selected: true,
        regenerable: true,
      },
    ]);
  });

  it("formats relative update time with an injectable clock", () => {
    const now = new Date("2026-07-10T12:00:00Z").getTime();

    expect(workflowNavUpdatedLabel("2026-07-10T11:30:00Z", now)).toBe("30分钟前");
  });
});

import { describe, expect, it } from "vitest";
import type { StageVersion, WorkflowClipSlot, WorkflowDetail } from "@/types";
import {
  canSelectVideoVersion,
  compactVideoVersionError,
  durationLabel,
  keyframePreviewFrames,
  stageStatusLabel,
  stageVersionDisplayTitle,
  videoSlotStatusLabel,
  videoVersionStatusLabel,
  workflowHeaderTags,
  workflowProgressPercent,
  workflowStatusLabel,
} from "@/views/unified/features/workflow-detail-presenters";

describe("workflow detail presenters", () => {
  it("formats stage versions and provider errors consistently", () => {
    const failed = {
      id: "v1",
      versionNo: 2,
      title: "V2：雨夜镜头",
      status: "FAILED",
      outputSummary: { error: "Request timed out while generating video" },
    } as unknown as StageVersion;

    expect(stageVersionDisplayTitle(failed)).toBe("雨夜镜头");
    expect(stageStatusLabel("PROCESSING")).toBe("生成中");
    expect(compactVideoVersionError(failed)).toBe("生成超时");
    expect(videoVersionStatusLabel(failed)).toBe("生成失败");
  });

  it("builds selectable video and keyframe preview states", () => {
    const completed = {
      id: "video-1",
      status: "COMPLETED",
      selected: false,
      downloadUrl: "/storage/video.mp4",
    } as unknown as StageVersion;
    const keyframe = {
      id: "keyframe-1",
      clipIndex: 1,
      selected: true,
      outputSummary: { startFrameUrl: "/storage/start.png", endFrameUrl: "/storage/end.png" },
    } as unknown as StageVersion;
    const slot = { videoVersions: [completed], keyframeVersions: [keyframe] } as unknown as WorkflowClipSlot;

    expect(canSelectVideoVersion(completed)).toBe(true);
    expect(videoSlotStatusLabel(slot)).toBe("待选择");
    expect(keyframePreviewFrames(keyframe, slot).map((frame) => frame.role)).toEqual(["first", "last"]);
    expect(durationLabel(6)).toBe("6.0s");
  });

  it("builds workflow header status and progress presentation", () => {
    const workflow = {
      status: "RUNNING",
      aspectRatio: "16:9",
    } as unknown as WorkflowDetail;

    const progress = workflowProgressPercent(workflow, [
      { ready: true },
      { ready: false },
      { ready: true },
    ]);

    expect(progress).toBe(67);
    expect(workflowStatusLabel(workflow.status)).toBe("执行中");
    expect(workflowHeaderTags(workflow, progress)).toContainEqual({ label: "进度", value: "67%" });
  });
});

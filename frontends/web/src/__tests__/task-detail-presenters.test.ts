import { describe, expect, it } from "vitest";
import type { TaskListItem } from "@/types";
import {
  buildImageTaskStages,
  buildVideoTaskStages,
  compactIdentifier,
  compactPath,
  firstNonBlank,
  normalizedTaskType,
  stageStateClass,
  taskFailureContext,
  taskTypeLabel,
} from "@/views/unified/features/task-detail-presenters";

describe("task detail presenters", () => {
  it("builds video and image stage states", () => {
    expect(buildVideoTaskStages("PAUSED").map((stage) => [stage.key, stage.state])).toEqual([
      ["ANALYZING", "done"],
      ["PLANNING", "done"],
      ["RENDERING", "paused"],
      ["COMPLETED", "pending"],
    ]);

    const imageTask = {
      createdAt: "2026-07-11T00:00:00Z",
      startedAt: "2026-07-11T00:00:02Z",
      finishedAt: "2026-07-11T00:00:05Z",
      updatedAt: "2026-07-11T00:00:05Z",
      attempts: [],
      stageRuns: [],
    } as unknown as TaskListItem;
    const stages = buildImageTaskStages(imageTask, "COMPLETED", "character_sheet");

    expect(stages.map((stage) => stage.state)).toEqual(["done", "done", "done"]);
    expect(stages[1]?.label).toBe("三视图生成");
    expect(stages[2]?.durationLabel).toBe("00:03秒");
  });

  it("formats compact task identity and failure context", () => {
    const task = {
      taskType: "video_generation",
      requestSnapshot: { taskType: "image_to_image" },
      failureStage: "render",
      failureClipIndex: 3,
    } as unknown as TaskListItem;

    expect(normalizedTaskType(task)).toBe("image_to_image");
    expect(taskTypeLabel(task)).toBe("图生图");
    expect(taskFailureContext(task)).toBe("阶段 render · 镜头 #3");
    expect(compactIdentifier("task_1234567890", 6)).toBe("#567890");
    expect(compactPath("/storage/tasks/task-1/running/video.mp4")).toBe(".../running/video.mp4");
    expect(firstNonBlank("", "  result ")).toBe("result");
    expect(stageStateClass("failed")).toBe("task-stage-row--failed");
  });
});

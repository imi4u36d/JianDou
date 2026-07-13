import { describe, expect, it } from "vitest";
import {
  ADMIN_TASK_SORT_OPTIONS,
  ADMIN_TASK_STATUS_OPTIONS,
  createAdminTaskPresenters,
} from "@/admin/features/tasks/task-management-presenters";
import type { AdminTaskListItem, TaskDetail } from "@/types";

function task(overrides: Partial<AdminTaskListItem> = {}): AdminTaskListItem {
  return {
    id: "task-1",
    title: "雨夜短片",
    taskType: "video_generation",
    status: "RENDERING",
    progress: 52,
    currentStage: "video",
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:05:00Z",
    ...overrides,
  } as AdminTaskListItem;
}

describe("admin task management presenters", () => {
  it("keeps status and sort filters in one typed catalog", () => {
    expect(ADMIN_TASK_STATUS_OPTIONS.find((item) => item.value === "COMPLETED")?.label).toBe("已完成");
    expect(ADMIN_TASK_SORT_OPTIONS.map((item) => item.value)).toContain("progress_desc");
  });

  it("combines list and loaded detail data into display rows", () => {
    const loadedDetail = {
      id: "task-1",
      status: "RENDERING",
      progress: 140,
      taskSeed: 42,
      requestSnapshot: {
        taskType: "video_generation",
        aspectRatio: "16:9",
        outputCount: { count: 2 },
        videoDurationSeconds: 8,
        videoModel: "sora-2",
      },
      monitoring: {
        currentStage: "video",
        activeAttemptStatus: "RUNNING",
        activeWorkerInstanceId: "worker-1",
        renderedClipCount: 2,
        plannedClipCount: 4,
      },
    } as TaskDetail;
    const presenters = createAdminTaskPresenters(() => loadedDetail);
    const current = task({ isQueued: true, queuePosition: 3 });

    expect(presenters.detailProgressValue(current)).toBe(100);
    expect(presenters.executionRows(current)).toEqual(
      expect.arrayContaining([
        { label: "当前阶段", value: "video" },
        { label: "Worker", value: "worker-1" },
        { label: "队列位置", value: "3" },
      ]),
    );
    expect(presenters.requestRows(current)).toEqual(
      expect.arrayContaining([
        { label: "画幅比例", value: "16:9" },
        { label: "视频模型", value: "sora-2" },
        { label: "输出数量", value: "2" },
        { label: "请求时长", value: "8 秒" },
        { label: "任务 Seed", value: "42" },
      ]),
    );
  });

  it("formats queue, completion and failure summaries consistently", () => {
    const presenters = createAdminTaskPresenters(() => undefined);

    expect(presenters.progressHint(task({ queuePosition: 2 }))).toBe("队列第 2 位");
    expect(presenters.progressHint(task({ status: "COMPLETED", completedOutputCount: 3 }))).toBe("已产出 3 个结果");
    expect(presenters.statusLabel("FAILED")).toBe("失败");
    expect(presenters.statusTagType("FAILED")).toBe("danger");
    expect(presenters.terminableStatus("RENDERING")).toBe(true);
    expect(presenters.terminableStatus("COMPLETED")).toBe(false);
  });
});

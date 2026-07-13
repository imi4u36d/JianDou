import { describe, expect, it } from "vitest";
import type { TaskListItem } from "@/types";
import {
  activeTaskProgress,
  activeTaskStageLabel,
  activeTaskTimestamp,
  formatActiveTaskTime,
} from "@/features/home/active-task-presenters";

function task(overrides: Partial<TaskListItem> = {}): TaskListItem {
  return {
    id: "task-1",
    title: "生成任务",
    status: "PENDING",
    progress: 0,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("active task presenters", () => {
  it("bounds and rounds progress", () => {
    expect(activeTaskProgress(task({ progress: 49.6 }))).toBe(50);
    expect(activeTaskProgress(task({ progress: -4 }))).toBe(0);
    expect(activeTaskProgress(task({ progress: 130 }))).toBe(100);
  });

  it("prefers explicit stage and describes queued tasks", () => {
    expect(activeTaskStageLabel(task({ currentStage: "正在渲染" }))).toBe("正在渲染");
    expect(activeTaskStageLabel(task({ queuePosition: 3 }))).toBe("队列第 3 位");
    expect(activeTaskStageLabel(task())).toBe("等待开始");
  });

  it("handles missing and invalid timestamps", () => {
    expect(activeTaskTimestamp("invalid")).toBe(0);
    expect(formatActiveTaskTime()).toBe("暂无时间");
    expect(formatActiveTaskTime("invalid")).toBe("invalid");
  });
});

/* eslint-disable vue/one-component-per-file -- mounts two production detail sections */
import { createApp, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import TaskMonitoringSummary from "@/views/unified/components/TaskMonitoringSummary.vue";
import TaskStageTimeline from "@/views/unified/components/TaskStageTimeline.vue";
import type { TaskStageDisplayItem } from "@/views/unified/features/task-detail-presenters";

const stages: TaskStageDisplayItem[] = [
  {
    key: "PENDING",
    label: "提交任务",
    state: "done",
    iconState: "done",
    stateLabel: "已完成",
    durationLabel: "00:02秒",
  },
  {
    key: "RENDERING",
    label: "图片生成",
    state: "active",
    iconState: "active",
    stateLabel: "进行中",
    durationLabel: "",
  },
];

describe("task detail sections", () => {
  it("renders image-task stages with state and duration semantics", async () => {
    const host = document.createElement("div");
    const app = createApp(TaskStageTimeline, { stages, imageMode: true });
    app.mount(host);
    await nextTick();

    expect(host.querySelectorAll(".detail-stage-step")).toHaveLength(2);
    expect(host.querySelector(".detail-stage-step-active")?.textContent).toContain("图片生成");
    expect(host.textContent).toContain("00:02秒");
    app.unmount();
  });

  it("renders monitoring and artifact rows independently", async () => {
    const host = document.createElement("div");
    const app = createApp(TaskMonitoringSummary, {
      monitoringRows: [{ label: "工作节点", value: "worker-1" }],
      artifactRows: [{ label: "视频", value: "1" }],
      artifactDirectoryHint: "/storage/tasks/task-1",
      shortArtifactDirectoryHint: ".../tasks/task-1",
    });
    app.mount(host);
    await nextTick();

    expect(host.querySelectorAll(".task-monitoring-card")).toHaveLength(2);
    expect(host.textContent).toContain("worker-1");
    expect(host.querySelector<HTMLElement>(".surface-chip")?.title).toBe("/storage/tasks/task-1");
    app.unmount();
  });
});

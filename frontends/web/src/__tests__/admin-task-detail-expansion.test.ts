/* eslint-disable vue/one-component-per-file -- lightweight Element Plus stubs exercise one production component */
import { createApp, defineComponent, h, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import AdminTaskDetailExpansion from "@/admin/components/AdminTaskDetailExpansion.vue";
import type { AdminTaskListItem, TaskDetail } from "@/types";

const passthrough = defineComponent({
  setup(_props, { slots }) {
    return () => h("div", slots.default?.());
  },
});

describe("admin task detail expansion", () => {
  it("renders loaded execution, request and output sections", async () => {
    const host = document.createElement("div");
    const task = {
      id: "task-1",
      title: "雨夜短片",
      taskType: "video_generation",
      status: "RENDERING",
      progress: 52,
      currentStage: "video",
    } as AdminTaskListItem;
    const detail = {
      ...task,
      taskSeed: 42,
      requestSnapshot: {
        taskType: "video_generation",
        aspectRatio: "16:9",
        videoModel: "sora-2",
      },
      monitoring: {
        currentStage: "video",
        activeAttemptStatus: "RUNNING",
        activeWorkerInstanceId: "worker-qa",
      },
    } as TaskDetail;
    const app = createApp(AdminTaskDetailExpansion, {
      task,
      detail,
      loading: false,
      error: "",
    });
    for (const name of ["el-skeleton", "el-alert", "el-tag", "el-progress", "el-collapse", "el-collapse-item"]) {
      app.component(name, passthrough);
    }
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("执行进度");
    expect(host.textContent).toContain("任务参数");
    expect(host.textContent).toContain("产物与监控");
    expect(host.textContent).toContain("worker-qa");
    expect(host.textContent).toContain("sora-2");
    app.unmount();
  });
});

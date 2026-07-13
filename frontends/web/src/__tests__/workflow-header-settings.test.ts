/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import {
  buildWorkflowSettingsPayload,
  validateWorkflowSettingsDraft,
  withWorkflowSetting,
  workflowSettingsDraftFromDetail,
  type WorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";
import type { WorkflowDetail } from "@/types";
import WorkflowHeaderSettings from "@/views/workflow/components/WorkflowHeaderSettings.vue";

function settings(): WorkflowSettingsDraft {
  return {
    aspectRatio: "16:9",
    textAnalysisModel: "gpt-4.1",
    imageModel: "gpt-image-1",
    videoModel: "sora-2",
    videoSize: "1280x720",
    keyframeSeed: "",
    videoSeed: "",
    durationMode: "manual",
    minDurationSeconds: "5",
    maxDurationSeconds: "12",
  };
}

function props(overrides: Record<string, unknown> = {}) {
  const options = [{ label: "默认", value: "default" }];
  return {
    title: "雨夜短片",
    parameterTags: [{ label: "状态", value: "进行中" }],
    open: false,
    settings: settings(),
    textModelOptions: options,
    imageModelOptions: options,
    videoModelOptions: options,
    aspectRatioOptions: options,
    videoSizeOptions: options,
    validationMessage: "",
    saving: false,
    ...overrides,
  };
}

describe("workflow header settings", () => {
  it("creates immutable settings updates", () => {
    const original = settings();
    const updated = withWorkflowSetting(original, "durationMode", "auto");

    expect(updated.durationMode).toBe("auto");
    expect(original.durationMode).toBe("manual");
    expect(updated).not.toBe(original);
  });

  it("maps workflow details into editable settings and API values", () => {
    const draft = workflowSettingsDraftFromDetail({
      aspectRatio: "9:16",
      textAnalysisModel: "gpt-4.1",
      imageModel: "gpt-image-1",
      videoModel: "sora-2",
      videoSize: "720x1280",
      keyframeSeed: 11,
      videoSeed: null,
      durationMode: "manual",
      minDurationSeconds: 6,
      maxDurationSeconds: 10,
    } as WorkflowDetail);

    expect(validateWorkflowSettingsDraft(draft)).toBe("");
    expect(buildWorkflowSettingsPayload(draft)).toMatchObject({
      keyframeSeed: 11,
      videoSeed: null,
      minDurationSeconds: 6,
      maxDurationSeconds: 10,
    });
  });

  it("validates manual duration ranges in one shared rule", () => {
    expect(validateWorkflowSettingsDraft({ ...settings(), minDurationSeconds: "12", maxDurationSeconds: "5" }))
      .toBe("最大时长不能小于最小时长");
    expect(buildWorkflowSettingsPayload({ ...settings(), durationMode: "auto" })).toMatchObject({
      minDurationSeconds: null,
      maxDurationSeconds: null,
    });
  });

  it("emits open state from the header action", async () => {
    const host = document.createElement("div");
    const onUpdateOpen = vi.fn();
    const app = createApp(WorkflowHeaderSettings, {
      ...props(),
      "onUpdate:open": onUpdateOpen,
    });
    app.mount(host);
    await nextTick();

    host.querySelector<HTMLButtonElement>('button[aria-label="编辑参数"]')?.click();

    expect(onUpdateOpen).toHaveBeenCalledWith(true);
    expect(host.textContent).toContain("雨夜短片");
    expect(host.textContent).toContain("进行中");
    app.unmount();
  });

  it("emits a new draft and save command from the settings form", async () => {
    const host = document.createElement("div");
    const onUpdateSettings = vi.fn();
    const onSave = vi.fn();
    const current = settings();
    const app = createApp(WorkflowHeaderSettings, {
      ...props({ open: true, settings: current }),
      "onUpdate:settings": onUpdateSettings,
      onSave,
    });
    app.mount(host);
    await nextTick();

    [...host.querySelectorAll("button")].find((button) => button.textContent?.trim() === "自动")?.click();
    host.querySelector("form")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await nextTick();

    expect(onUpdateSettings).toHaveBeenCalledWith(expect.objectContaining({ durationMode: "auto" }));
    expect(current.durationMode).toBe("manual");
    expect(onSave).toHaveBeenCalledOnce();
    app.unmount();
  });

});

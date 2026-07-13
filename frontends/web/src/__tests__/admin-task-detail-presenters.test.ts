import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { useAdminTaskDetailPresenters } from "@/admin/features/tasks/admin-task-detail-presenters";
import type { AdminTaskDiagnosis, TaskDetail, TaskTraceEvent } from "@/types";

describe("admin task detail presenters", () => {
  it("builds request, monitoring and trace summaries from task state", () => {
    const task = ref({
      id: "task-1",
      status: "RENDERING",
      minDurationSeconds: 5,
      maxDurationSeconds: 8,
      taskSeed: 42,
      requestSnapshot: {
        textAnalysisModel: "gpt-4.1",
        imageModel: "gpt-image-1",
        videoModel: "sora-2",
        outputCount: 2,
        videoDurationSeconds: 8,
        transcriptText: "雨夜追逐正文",
      },
      monitoring: {
        currentStage: "video",
        activeAttemptStatus: "RUNNING",
        activeWorkerInstanceId: "worker-qa",
        plannedClipCount: 4,
        renderedClipCount: 2,
      },
    } as TaskDetail);
    const traceEvents = ref([
      { timestamp: "2026-07-11T00:00:00Z", level: "INFO", stage: "plan", event: "start", message: "开始" },
      { timestamp: "2026-07-11T00:01:00Z", level: "INFO", stage: "video", event: "render", message: "渲染中" },
    ] as TaskTraceEvent[]);
    const diagnosis = ref<AdminTaskDiagnosis | null>(null);
    const presenters = useAdminTaskDetailPresenters({ task, traceEvents, diagnosis });

    expect(presenters.runningTask.value).toBe(true);
    expect(presenters.compactRequestRows.value).toEqual(
      expect.arrayContaining([
        { label: "文本模型", value: "gpt-4.1" },
        { label: "视频模型", value: "sora-2" },
        { label: "输出数量", value: "2" },
      ]),
    );
    expect(presenters.monitoringRows.value).toEqual(
      expect.arrayContaining([
        { label: "Attempt 状态", value: "RUNNING" },
        { label: "已生成镜头数", value: "2" },
      ]),
    );
    expect(presenters.traceFocus.value?.message).toBe("渲染中");
    expect(presenters.requestTranscriptPreview.value).toBe("雨夜追逐正文");
  });

  it("formats duration and diagnosis severity consistently", () => {
    const diagnosis = ref({
      taskId: "task-1",
      title: "雨夜短片",
      status: "FAILED",
      severity: "high",
      summary: "存在失败",
      findings: [],
      recovery: { recommendedAction: "retry", resumeFromStage: "video", resumeFromClipIndex: 2 },
      continuity: { plannedClipCount: 4, contiguousRenderedClipCount: 1, missingClipIndices: [2, 3] },
      outputs: {},
      queue: { isQueued: true, queuePosition: 2, activeAttemptStatus: "QUEUED" },
    } satisfies AdminTaskDiagnosis);
    const presenters = useAdminTaskDetailPresenters({
      task: ref(null),
      traceEvents: ref([]),
      diagnosis,
    });

    expect(presenters.diagnosisSeverityLabel.value).toBe("高风险");
    expect(presenters.diagnosisSeverityTag.value).toBe("danger");
    expect(presenters.diagnosisRecoveryStart.value).toBe("video / 镜头 2");
    expect(presenters.formatSecondsRange(5, 8, 6)).toBe("5s - 8s (目标 6s)");
  });
});

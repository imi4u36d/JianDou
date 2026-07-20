import { computed, type Ref } from "vue";
import type { WorkflowDetail } from "@/types";
import { canSelectVideoVersion } from "@/features/workflows/stage-workflow-presenters";
import { selectedCharacterSheetVersion } from "./useCharacterSheetUtils";

export function useWorkflowStageReadiness(workflow: Ref<WorkflowDetail | null>) {
  const workflowCharacterSheets = computed(() => workflow.value?.visualAssets ?? workflow.value?.characterSheets ?? []);
  const missingCharacterSheets = computed(() =>
    workflowCharacterSheets.value.filter((sheet) => !selectedCharacterSheetVersion(sheet)),
  );
  const videoReadiness = computed(() => {
    const slots = workflow.value?.clipSlots ?? [];
    return {
      total: slots.length,
      generated: slots.filter((slot) =>
        slot.videoVersions.some((version) => canSelectVideoVersion(version)),
      ).length,
      selected: slots.filter((slot) =>
        slot.videoVersions.some((version) => version.selected),
      ).length,
      missing: slots.filter((slot) =>
        !slot.videoVersions.some((version) => version.selected),
      ),
    };
  });
  const canFinalize = computed(() => {
    const slots = workflow.value?.clipSlots ?? [];
    return slots.length > 0 && slots.every((slot) =>
      slot.videoVersions.some((version) => version.selected),
    );
  });
  const finalizeButtonLabel = computed(() => workflow.value?.finalResult ? "重拼" : "拼接");
  const finalizeHint = computed(() => {
    if (!(workflow.value?.clipSlots ?? []).length) return "等待镜头";
    return canFinalize.value ? "可拼接" : `缺 ${videoReadiness.value.missing.length}`;
  });
  const canvasStageItems = computed(() => {
    const current = workflow.value;
    const storyboardCount = current?.storyboardVersions?.length ?? 0;
    const keyframeCount = current?.clipSlots?.reduce(
      (sum, slot) => sum + (slot.keyframeVersions?.length ?? 0),
      0,
    ) ?? 0;
    const videoCount = current?.clipSlots?.reduce(
      (sum, slot) => sum + (slot.videoVersions?.length ?? 0),
      0,
    ) ?? 0;
    const selectedCharacterCount = workflowCharacterSheets.value.filter(
      (sheet) => Boolean(selectedCharacterSheetVersion(sheet)),
    ).length;
    return [
      { key: "storyboard" as const, index: 1, label: "分镜脚本", status: storyboardCount ? "已有版本" : "待生成", count: `${storyboardCount} 版`, ready: storyboardCount > 0 },
      { key: "character" as const, index: 2, label: "公共素材", status: selectedCharacterCount ? "已有素材" : storyboardCount ? "可生成" : "等分镜", count: `${selectedCharacterCount}/${workflowCharacterSheets.value.length || 0}`, ready: selectedCharacterCount > 0 },
      { key: "keyframe" as const, index: 3, label: "关键帧", status: keyframeCount ? "已有关键帧" : storyboardCount ? "可生成" : "等素材", count: `${keyframeCount} 版`, ready: keyframeCount > 0 },
      { key: "video" as const, index: 4, label: "视频片段", status: videoCount ? "已有视频" : keyframeCount ? "可生成" : "等关键帧", count: `${videoCount} 版`, ready: videoCount > 0 },
      { key: "final" as const, index: 5, label: "成片", status: current?.finalResult ? "已拼接" : canFinalize.value ? "可拼接" : "未就绪", count: current?.finalResult ? "已完成" : `${videoReadiness.value.selected}/${videoReadiness.value.total || 0}`, ready: Boolean(current?.finalResult || canFinalize.value) },
    ];
  });

  return {
    workflowCharacterSheets,
    missingCharacterSheets,
    videoReadiness,
    canFinalize,
    finalizeButtonLabel,
    finalizeHint,
    canvasStageItems,
  };
}

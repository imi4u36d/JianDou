import { computed, reactive, ref, type Ref } from "vue";
import { characterSheetKey, characterSheetVersions, selectedCharacterSheetVersion } from "@/composables/workflow/useCharacterSheetUtils";
import type { WorkflowCharacterSheet, WorkflowDetail } from "@/types";

export function useWorkflowStagePreviews(selectedWorkflow: Ref<WorkflowDetail | null>) {
  const previewStoryboardVersionId = ref("");
  const previewCharacterSheetVersionIds = reactive<Record<string, string>>({});
  const selectedCanvasClipIndex = ref<number | null>(null);
  const previewKeyframeVersionIds = reactive<Record<number, string>>({});
  const previewVideoVersionIds = reactive<Record<number, string>>({});
  const storyboardAdjustmentDrafts = reactive<Record<string, string>>({});

  const selectedStoryboardVersion = computed(() => {
    const versions = selectedWorkflow.value?.storyboardVersions ?? [];
    return versions.find((version) => version.id === previewStoryboardVersionId.value) ?? versions.find((version) => version.selected) ?? versions[0] ?? null;
  });

  const selectedStoryboardAdjustment = computed(() => (selectedStoryboardVersion.value ? (storyboardAdjustmentDrafts[selectedStoryboardVersion.value.id] ?? "") : ""));

  const selectedCanvasClip = computed(() => {
    const slots = selectedWorkflow.value?.clipSlots ?? [];
    return slots.find((slot) => slot.clipIndex === selectedCanvasClipIndex.value) ?? slots[0] ?? null;
  });

  const previewKeyframeVersion = computed(() => {
    const clip = selectedCanvasClip.value;
    if (!clip) return null;
    const previewId = previewKeyframeVersionIds[clip.clipIndex] || "";
    return clip.keyframeVersions.find((version) => version.id === previewId) ?? clip.keyframeVersions.find((version) => version.selected) ?? clip.keyframeVersions[0] ?? null;
  });

  const previewVideoVersion = computed(() => {
    const clip = selectedCanvasClip.value;
    if (!clip) return null;
    const previewId = previewVideoVersionIds[clip.clipIndex] || "";
    return clip.videoVersions.find((version) => version.id === previewId) ?? clip.videoVersions.find((version) => version.selected) ?? clip.videoVersions[0] ?? null;
  });

  function previewCharacterSheetVersion(sheet: WorkflowCharacterSheet) {
    const versions = characterSheetVersions(sheet);
    const previewId = previewCharacterSheetVersionIds[characterSheetKey(sheet)] || "";
    return versions.find((version) => version.id === previewId) ?? selectedCharacterSheetVersion(sheet) ?? versions[0] ?? null;
  }

  function updateSelectedStoryboardAdjustment(value: string) {
    if (selectedStoryboardVersion.value) {
      storyboardAdjustmentDrafts[selectedStoryboardVersion.value.id] = value;
    }
  }

  function storyboardAdjustment(versionId: string) {
    return storyboardAdjustmentDrafts[versionId] ?? "";
  }

  function setStoryboardAdjustment(versionId: string, value: string) {
    storyboardAdjustmentDrafts[versionId] = value;
  }

  function selectCanvasClip(clipIndex: number) {
    selectedCanvasClipIndex.value = clipIndex;
  }

  function setPreviewStoryboardVersion(versionId: string) {
    previewStoryboardVersionId.value = versionId;
  }

  function setPreviewCharacterSheetVersion(sheetKey: string, versionId: string) {
    previewCharacterSheetVersionIds[sheetKey] = versionId;
  }

  function setPreviewKeyframeVersion(clipIndex: number, versionId: string) {
    previewKeyframeVersionIds[clipIndex] = versionId;
  }

  function setPreviewVideoVersion(clipIndex: number, versionId: string) {
    previewVideoVersionIds[clipIndex] = versionId;
  }

  function applyPreviewSelections(workflow: WorkflowDetail) {
    const storyboardVersions = workflow.storyboardVersions ?? [];
    for (const version of storyboardVersions) storyboardAdjustmentDrafts[version.id] ??= "";
    previewStoryboardVersionId.value = storyboardVersions.find((version) => version.id === previewStoryboardVersionId.value)?.id ?? storyboardVersions.find((version) => version.selected)?.id ?? storyboardVersions[0]?.id ?? "";

    for (const sheet of workflow.visualAssets ?? workflow.characterSheets ?? []) {
      const sheetKey = characterSheetKey(sheet);
      const versions = characterSheetVersions(sheet);
      previewCharacterSheetVersionIds[sheetKey] = versions.find((version) => version.id === previewCharacterSheetVersionIds[sheetKey])?.id ?? versions.find((version) => version.selected)?.id ?? versions[0]?.id ?? "";
    }

    for (const slot of workflow.clipSlots ?? []) {
      previewKeyframeVersionIds[slot.clipIndex] =
        slot.keyframeVersions.find((version) => version.id === previewKeyframeVersionIds[slot.clipIndex])?.id ?? slot.keyframeVersions.find((version) => version.selected)?.id ?? slot.keyframeVersions[0]?.id ?? "";
      previewVideoVersionIds[slot.clipIndex] = slot.videoVersions.find((version) => version.id === previewVideoVersionIds[slot.clipIndex])?.id ?? slot.videoVersions.find((version) => version.selected)?.id ?? slot.videoVersions[0]?.id ?? "";
    }
  }

  return {
    previewStoryboardVersionId,
    previewCharacterSheetVersionIds,
    selectedCanvasClipIndex,
    previewKeyframeVersionIds,
    previewVideoVersionIds,
    storyboardAdjustmentDrafts,
    selectedStoryboardVersion,
    selectedStoryboardAdjustment,
    selectedCanvasClip,
    previewKeyframeVersion,
    previewVideoVersion,
    previewCharacterSheetVersion,
    updateSelectedStoryboardAdjustment,
    storyboardAdjustment,
    setStoryboardAdjustment,
    selectCanvasClip,
    setPreviewStoryboardVersion,
    setPreviewCharacterSheetVersion,
    setPreviewKeyframeVersion,
    setPreviewVideoVersion,
    applyPreviewSelections,
  };
}

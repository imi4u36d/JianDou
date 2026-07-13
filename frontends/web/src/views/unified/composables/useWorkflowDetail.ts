/**
 * 工作流详情组合式逻辑。
 * 从 StageWorkflowView 提取，管理工作流画布的全部状态和操作。
 */
import { computed, onMounted, reactive, ref, watch } from "vue";
import type { WorkflowCanvasStageKey } from "@/features/workflows/summary";
import type { StageVersion, WorkflowDetail } from "@/types";
import {
  buildWorkflowSettingsPayload as createWorkflowSettingsPayload,
  createWorkflowSettingsDraft,
  validateWorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";
import { useWorkflowOptions } from "@/composables/workflow/useWorkflowOptions";
import { useCharacterAssetPicker } from "@/composables/workflow/useCharacterAssetPicker";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import {
  characterSheetKey,
  characterSheetClipIndex,
  characterSheetTitle,
  characterSheetAppearanceSummary,
  characterSheetVersions,
  selectedCharacterSheetVersion,
  hasMissingCharacterSheets,
  characterSheetPreviewFrames,
} from "@/composables/workflow/useCharacterSheetUtils";
import type { AppSelectOption } from "@/components/common/app-select";
import { useWorkflowVersionCommands } from "./useWorkflowVersionCommands";
import { useWorkflowGenerationCommands } from "./useWorkflowGenerationCommands";
import { useWorkflowDetailLoader } from "./useWorkflowDetailLoader";
import { useWorkflowPreviewInteractions } from "./useWorkflowPreviewInteractions";
import { useWorkflowStageReadiness } from "@/composables/workflow/useWorkflowStageReadiness";
import { useWorkflowStagePreviews } from "@/composables/workflow/useWorkflowStagePreviews";
import {
  canSelectVideoVersion,
  clipSceneSummary,
  compactModelLabel,
  compactVideoSizeLabel,
  compactVideoVersionError,
  durationLabel,
  formatDateTime,
  isLandscapeKeyframeVersion as isLandscapeKeyframeVersionForAspect,
  keyframePreviewFrames,
  stageStatusLabel,
  stageVersionDisplayTitle,
  storyboardPreviewHtml,
  versionSeed,
  videoSlotStatusLabel,
  videoVersionErrorMessage,
  videoVersionStatusLabel,
} from "../features/workflow-detail-presenters";

type CanvasStageKey = WorkflowCanvasStageKey;
function toAppSelectOptions<T extends { label: string; value: unknown }>(items: T[]): AppSelectOption[] {
  return items.map((item) => ({ label: item.label, value: item.value }));
}

export interface UseWorkflowDetailOptions {
  selectedWorkflowId: () => string;
  reloadWorkflows: () => Promise<void>;
}

export function useWorkflowDetail(detailOptions: UseWorkflowDetailOptions) {
  // ── Composables ──
  const workflowOptions = useWorkflowOptions();
  const previewInteractions = useWorkflowPreviewInteractions();
  const characterAssetPickerState = useCharacterAssetPicker();
  const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

  const {
    loadingOptions, aspectRatioOptions,
    textModelOptions, imageModelOptions, videoModelOptions, catalogVideoSizeOptions,
    filterVideoSizeOptions, syncVideoSizeSelection, valueOptionLabel, loadOptions,
  } = workflowOptions;

  const {
    imagePreviewOverlayRef, imagePreviewTriggerRef, imagePreviewState,
    imagePreviewCaption, openImagePreview, closeImagePreview, switchImagePreviewFrame,
    imagePreviewLoadFailed, characterSummaryPreviewState,
    isPreviewImageFailed, isPreviewImageAvailable, markPreviewImageFailed,
    openCharacterSummaryPreview, closeCharacterSummaryPreview, openKeyframeImagePreview,
    positionVersionMenu,
  } = previewInteractions;

  const {
    characterAssetPicker, materialAssetPreviewUrl, materialAssetModelLabel,
    isCharacterAssetPickerOpen, openCharacterAssetPicker, closeCharacterAssetPicker,
    loadCharacterAssetCandidates,
  } = characterAssetPickerState;

  // ── Core State ──
  const selectedWorkflowId = computed(() => detailOptions.selectedWorkflowId());
  const loadingDetail = ref(false);
  const busyActionKey = ref("");
  const activeCanvasStage = ref<CanvasStageKey>("storyboard");
  const selectedWorkflow = ref<WorkflowDetail | null>(null);
  const workflowSettingsOpen = ref(false);
  const workflowSettingsDraft = reactive(createWorkflowSettingsDraft());
  const {
    selectedCanvasClipIndex,
    storyboardAdjustmentDrafts,
    selectedStoryboardVersion,
    selectedCanvasClip,
    previewKeyframeVersion,
    previewVideoVersion,
    previewCharacterSheetVersion,
    selectCanvasClip,
    setPreviewStoryboardVersion,
    setPreviewCharacterSheetVersion,
    setPreviewKeyframeVersion,
    setPreviewVideoVersion,
    applyPreviewSelections,
  } = useWorkflowStagePreviews(selectedWorkflow);

  const {
    applyWorkflowDrafts,
    loadWorkflowDetail,
    pollCurrentWorkflow,
    reloadCurrentWorkflow,
    switchCanvasStage,
  } = useWorkflowDetailLoader({
    selectedWorkflowId,
    selectedWorkflow,
    loadingDetail,
    activeCanvasStage,
    selectedCanvasClipIndex,
    workflowSettingsOpen,
    workflowSettingsDraft,
    applyPreviewSelections,
    syncVideoSizeSelection,
    closeCharacterAssetPicker,
    reloadWorkflows: detailOptions.reloadWorkflows,
  });

  // ── Select Options ──
  const textModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(textModelOptions.value));
  const imageModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(imageModelOptions.value));
  const videoModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(videoModelOptions.value));
  const aspectRatioSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(aspectRatioOptions.value));
  const workflowSettingsVideoSizeOptions = computed(() =>
    filterVideoSizeOptions(catalogVideoSizeOptions.value, workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio)
  );
  const workflowSettingsVideoSizeSelectOptions = computed<AppSelectOption[]>(() =>
    toAppSelectOptions(workflowSettingsVideoSizeOptions.value)
  );

  // ── Computed: Workflow Data ──
  const {
    workflowCharacterSheets,
    missingCharacterSheets,
    videoReadiness,
    canFinalize,
    finalizeButtonLabel,
    finalizeHint,
    canvasStageItems,
  } = useWorkflowStageReadiness(selectedWorkflow);
  const workflowParameterTags = computed(() => {
    const wf = selectedWorkflow.value;
    if (!wf) return [];
    return [
      { label: "关键帧模型", value: compactModelLabel(valueOptionLabel(imageModelOptions.value, wf.imageModel, wf.imageModel || "未设置")) },
      { label: "视频模型", value: compactModelLabel(valueOptionLabel(videoModelOptions.value, wf.videoModel, wf.videoModel || "未设置")) },
      { label: "尺寸", value: compactVideoSizeLabel(valueOptionLabel(catalogVideoSizeOptions.value, wf.videoSize, wf.videoSize || "未设置"), wf.aspectRatio) },
    ];
  });

  const workflowSettingsValidationMessage = computed(() => validateWorkflowSettingsDraft(workflowSettingsDraft));

  // ── Helper Functions ──

  function isLandscapeKeyframeVersion(version: StageVersion) {
    return isLandscapeKeyframeVersionForAspect(version, selectedWorkflow.value?.aspectRatio);
  }
  function buildWorkflowSettingsPayload() {
    return createWorkflowSettingsPayload(workflowSettingsDraft);
  }

  // ── Action Handlers ──

  const {
    handleUpdateWorkflowSettings,
    handleGenerateStoryboard,
    handleAdjustStoryboard,
    handleSelectStoryboard,
    handleGenerateKeyframe,
    handleGenerateMissingCharacterSheets,
    handleGenerateCharacterSheet,
    handleGenerateKeyframeFrame,
    handleSelectKeyframe,
    handleSelectCharacterSheetVersion,
    handleSelectKeyframeFrame,
    handleSelectCharacterSheetAsset,
    handleGenerateVideo,
    handleSelectVideo,
    handleFinalize,
  } = useWorkflowGenerationCommands({
    selectedWorkflowId,
    selectedWorkflow,
    busyActionKey,
    workflowSettingsValidationMessage,
    workflowSettingsOpen,
    storyboardAdjustmentDrafts,
    missingCharacterSheets,
    applyWorkflowDrafts,
    reloadWorkflows: detailOptions.reloadWorkflows,
    buildWorkflowSettingsPayload,
    closeCharacterAssetPicker,
    reloadCurrentWorkflow,
  });

  const { handleDeleteStageVersion, handleClearStageVersions, handleReuseAsset } = useWorkflowVersionCommands({
    selectedWorkflowId,
    selectedWorkflow,
    busyActionKey,
    workflowCharacterSheets,
    applyWorkflowDrafts,
    reloadWorkflows: detailOptions.reloadWorkflows,
    requestConfirm,
  });

  // ── Watchers: auto-load when selectedWorkflowId changes ──

  watch(selectedWorkflowId, (workflowId) => {
    if (!workflowId) { selectedWorkflow.value = null; return; }
    closeCharacterAssetPicker();
    workflowSettingsOpen.value = false;
    void loadWorkflowDetail(workflowId);
  }, { immediate: true });

  watch(
    () => [workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio, catalogVideoSizeOptions.value] as const,
    () => { syncVideoSizeSelection(workflowSettingsDraft, workflowSettingsDraft.videoSize); }
  );

  // ── Lifecycle ──

  onMounted(loadOptions);

  return {
    // Core state
    selectedWorkflow,
    selectedWorkflowId,
    loadingDetail,
    loadingOptions,
    busyActionKey,
    activeCanvasStage,
    workflowSettingsOpen,
    workflowSettingsDraft,
    workflowSettingsValidationMessage,
    storyboardAdjustmentDrafts,
    characterSummaryPreviewState,
    // Confirm dialog
    confirmDialog,
    acceptConfirm,
    cancelConfirm,
    // Computed
    canvasStageItems,
    workflowParameterTags,
    workflowCharacterSheets,
    missingCharacterSheets,
    selectedStoryboardVersion,
    selectedCanvasClip,
    previewKeyframeVersion,
    previewVideoVersion,
    canFinalize,
    finalizeButtonLabel,
    finalizeHint,
    videoReadiness,
    // Select options
    textModelSelectOptions,
    imageModelSelectOptions,
    videoModelSelectOptions,
    aspectRatioSelectOptions,
    workflowSettingsVideoSizeSelectOptions,
    // Image preview
    imagePreviewOverlayRef,
    imagePreviewTriggerRef,
    imagePreviewState,
    imagePreviewCaption,
    imagePreviewLoadFailed,
    openImagePreview,
    closeImagePreview,
    switchImagePreviewFrame,
    // Character asset picker
    characterAssetPicker,
    materialAssetPreviewUrl,
    materialAssetModelLabel,
    isCharacterAssetPickerOpen,
    openCharacterAssetPicker,
    closeCharacterAssetPicker,
    loadCharacterAssetCandidates,
    // Helper functions
    stageVersionDisplayTitle,
    stageStatusLabel,
    videoVersionErrorMessage,
    compactVideoVersionError,
    canSelectVideoVersion,
    videoVersionStatusLabel,
    videoSlotStatusLabel,
    selectCanvasClip,
    storyboardPreviewHtml,
    isLandscapeKeyframeVersion,
    keyframePreviewFrames,
    isPreviewImageFailed,
    isPreviewImageAvailable,
    markPreviewImageFailed,
    versionSeed,
    durationLabel,
    clipSceneSummary,
    formatDateTime,
    openCharacterSummaryPreview,
    closeCharacterSummaryPreview,
    openKeyframeImagePreview,
    positionVersionMenu,
    previewCharacterSheetVersion,
    // Character sheet utils
    characterSheetKey,
    characterSheetClipIndex,
    characterSheetTitle,
    characterSheetAppearanceSummary,
    characterSheetVersions,
    selectedCharacterSheetVersion,
    hasMissingCharacterSheets,
    characterSheetPreviewFrames,
    // Preview setters
    setPreviewStoryboardVersion,
    setPreviewCharacterSheetVersion,
    setPreviewKeyframeVersion,
    setPreviewVideoVersion,
    // Actions
    switchCanvasStage,
    loadWorkflowDetail,
    reloadCurrentWorkflow,
    pollCurrentWorkflow,
    handleUpdateWorkflowSettings,
    handleGenerateStoryboard,
    handleAdjustStoryboard,
    handleSelectStoryboard,
    handleGenerateKeyframe,
    handleGenerateMissingCharacterSheets,
    handleGenerateCharacterSheet,
    handleGenerateKeyframeFrame,
    handleSelectKeyframe,
    handleSelectCharacterSheetVersion,
    handleSelectKeyframeFrame,
    handleSelectCharacterSheetAsset,
    handleGenerateVideo,
    handleSelectVideo,
    handleFinalize,
    handleDeleteStageVersion,
    handleClearStageVersions,
    handleReuseAsset,
  };
}

<template>
  <section class="workflow-canvas-view" :class="{ 'workflow-canvas-view-detail': selectedWorkflowId }">
    <WorkflowProjectDrawer
      v-model:search="workflowSearch"
      v-model:filter="workflowFilter"
      :workflows="workflows"
      :filtered-workflows="filteredWorkflows"
      :selected-workflow-id="selectedWorkflowId"
      :loading="loadingWorkflows"
      :loading-more="loadingMoreWorkflows"
      :refreshing="refreshingWorkflows"
      :has-more="hasMoreWorkflows"
      :busy-action-key="busyActionKey"
      :completion-percentage="workflowCompletionPercentage"
      @refresh="handleRefreshWorkflows"
      @open="openWorkflow"
      @delete="handleDeleteWorkflow"
      @load-more="loadMoreWorkflows"
      @page-size="setWorkflowPageSize"
    />

    <section class="workflow-canvas-main">
      <div v-if="showDetailLoadFailed" class="surface-panel workflow-banner workflow-banner-error">
        <p>工作流详情加载失败</p>
        <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="loadingDetail" @click="reloadCurrentWorkflow">重新加载</button>
      </div>

      <div v-else-if="loadingDetail" class="surface-panel workflow-empty workflow-empty-large">加载中</div>

      <template v-else-if="selectedWorkflow">
        <WorkflowHeaderSettings
          v-model:open="workflowSettingsOpen"
          :title="selectedWorkflow.title"
          :parameter-tags="workflowParameterTags"
          :settings="workflowSettingsDraft"
          :text-model-options="textModelSelectOptions"
          :image-model-options="imageModelSelectOptions"
          :video-model-options="videoModelSelectOptions"
          :aspect-ratio-options="aspectRatioSelectOptions"
          :video-size-options="workflowSettingsVideoSizeSelectOptions"
          :validation-message="workflowSettingsValidationMessage"
          :saving="busyActionKey === 'workflow-settings'"
          @update:settings="applyWorkflowSettingsDraft"
          @save="handleUpdateWorkflowSettings"
        />

        <WorkflowStagePipeline :stages="canvasStageItems" :active-stage="activeCanvasStage" @switch="switchCanvasStage" />

        <section class="workflow-canvas-grid">
          <main class="workflow-stage-canvas">
            <WorkflowStoryboardBoard
              v-if="activeCanvasStage === 'storyboard'"
              :versions="selectedWorkflow.storyboardVersions ?? []"
              :selected-version="selectedStoryboardVersion"
              :adjustment="selectedStoryboardAdjustment"
              :busy-action-key="busyActionKey"
              @update:adjustment="updateSelectedStoryboardAdjustment"
              @clear="handleClearStageVersions('storyboard')"
              @generate="handleGenerateStoryboard"
              @preview="setPreviewStoryboardVersion"
              @select="handleSelectStoryboard"
              @reuse="handleReuseAsset"
              @delete="handleDeleteStageVersion"
              @adjust="handleAdjustStoryboard"
              @position-menu="positionVersionMenu"
            />

            <WorkflowCharacterBoard
              v-else-if="activeCanvasStage === 'character'"
              :sheets="workflowCharacterSheets"
              :missing-count="missingCharacterSheets.length"
              :preview-version-ids="previewCharacterSheetVersionIds"
              :busy-action-key="busyActionKey"
              @generate-missing="handleGenerateMissingCharacterSheets"
              @preview-version="setPreviewCharacterSheetVersion"
              @preview-image="openImagePreview"
              @summary="openCharacterSummaryPreview"
              @generate="handleGenerateCharacterSheet"
              @select-asset="handleSelectCharacterSheetAsset"
            />

            <WorkflowKeyframeBoard
              v-else-if="activeCanvasStage === 'keyframe'"
              :slots="selectedWorkflow.clipSlots ?? []"
              :selected-clip="selectedCanvasClip"
              :preview-version="previewKeyframeVersion"
              :aspect-ratio="selectedWorkflow.aspectRatio"
              :busy-action-key="busyActionKey"
              @clear="handleClearStageVersions('keyframe')"
              @generate="handleGenerateKeyframe"
              @select-clip="selectCanvasClip"
              @preview-version="setPreviewKeyframeVersion"
              @select-version="handleSelectKeyframe"
              @reuse="handleReuseAsset"
              @delete="handleDeleteStageVersion"
              @position-menu="positionVersionMenu"
              @preview-image="openKeyframeImagePreview"
              @select-frame="handleSelectKeyframeFrame"
              @generate-frame="handleGenerateKeyframeFrame"
            />

            <WorkflowVideoBoard
              v-else-if="activeCanvasStage === 'video'"
              :slots="selectedWorkflow.clipSlots ?? []"
              :selected-clip="selectedCanvasClip"
              :preview-version="previewVideoVersion"
              :readiness="videoReadiness"
              :can-finalize="canFinalize"
              :busy-action-key="busyActionKey"
              @clear="handleClearStageVersions('video')"
              @generate="handleGenerateVideo"
              @select-clip="selectCanvasClip"
              @preview-version="setPreviewVideoVersion"
              @select-version="handleSelectVideo"
              @reuse="handleReuseAsset"
              @download="handleDownloadVideo"
              @delete="handleDeleteStageVersion"
              @position-menu="positionVersionMenu"
            />

            <WorkflowFinalBoard
              v-else
              :final-result="selectedWorkflow.finalResult ?? null"
              :readiness="videoReadiness"
              :can-finalize="canFinalize"
              :finalize-hint="finalizeHint"
              :finalize-button-label="finalizeButtonLabel"
              :busy-action-key="busyActionKey"
              @finalize="handleFinalize"
              @download="handleDownloadVideo"
              @open-missing="openMissingVideoClip"
            />
          </main>
        </section>
      </template>

      <section v-else class="workflow-selection-empty" aria-labelledby="workflow-selection-empty-title">
        <div class="workflow-selection-empty__icon" aria-hidden="true">
          <IconVideo size="xl" />
        </div>
        <div class="workflow-selection-empty__copy">
          <p class="workflow-selection-empty__eyebrow">视频工作流</p>
          <h2 id="workflow-selection-empty-title">选择一个视频任务开始创作</h2>
          <p>从左侧列表打开任务，即可继续分镜、公共素材、关键帧、视频片段与成片制作。</p>
        </div>
        <ol class="workflow-selection-empty__stages" aria-label="视频制作阶段">
          <li><span>1</span>分镜</li>
          <li><span>2</span>公共素材</li>
          <li><span>3</span>关键帧</li>
          <li><span>4</span>视频</li>
          <li><span>5</span>成片</li>
        </ol>
      </section>
    </section>
  </section>

  <CharacterSummaryDialog v-bind="characterSummaryPreviewState" @close="closeCharacterSummaryPreview" />
  <ImagePreviewOverlay
    ref="imagePreviewOverlayRef"
    :open="imagePreviewState.open"
    :url="imagePreviewState.url"
    :alt="imagePreviewState.alt"
    :caption="imagePreviewCaption"
    :gallery-size="imagePreviewState.gallery.length"
    @close="closeImagePreview"
    @switch-frame="switchImagePreviewFrame"
  />

  <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { requireAuth } from "@/auth/modal";
import {
  summaryUrlListValue,
  summaryUrlValue,
  workflowStageLabel,
  workflowSummaryCharacterCountLabel,
} from "@/features/workflows/summary";
import type { WorkflowCanvasStageKey, WorkflowDetailRouteStageKey } from "@/features/workflows/summary";
import {
  clipSceneText,
  compactModelLabel,
  compactVideoSizeLabel,
  formatDateTime,
  formatWorkflowStatus,
  keyframePreviewFrames,
  normalizedStageVersionStatus,
  parseStoryboardDurationSeconds,
  stageVersionDisplayTitle,
  storyboardPreview,
  versionSeed,
} from "@/features/workflows/stage-workflow-presenters";
import {
  createWorkflowSettingsDraft,
  validateWorkflowSettingsDraft,
  type WorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";
import { formatApiErrorMessage } from "@/utils/api-error";
import { messageApi } from "@/composables/useMessage";
import type { StageVersion, WorkflowDetail } from "@/types";
import { useWorkflowOptions } from "@/composables/workflow/useWorkflowOptions";
import { useWorkflowList } from "@/composables/workflow/useWorkflowList";
import { useWorkflowPreviewInteractions } from "@/composables/workflow/useWorkflowPreviewInteractions";
import { useWorkflowStagePreviews } from "@/composables/workflow/useWorkflowStagePreviews";
import { useWorkflowStageCommands } from "@/composables/workflow/useWorkflowStageCommands";
import { useStageWorkflowManagementCommands } from "@/composables/workflow/useStageWorkflowManagementCommands";
import { useStageWorkflowDetailLoader } from "@/composables/workflow/useStageWorkflowDetailLoader";
import { useStageWorkflowInteractions } from "@/composables/workflow/useStageWorkflowInteractions";
import { useWorkflowStageReadiness } from "@/composables/workflow/useWorkflowStageReadiness";
import { useWorkflowVersionCommands } from "./unified/composables/useWorkflowVersionCommands";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import WorkflowStagePipeline from "./workflow/components/WorkflowStagePipeline.vue";
import WorkflowProjectDrawer from "./workflow/components/WorkflowProjectDrawer.vue";
import WorkflowHeaderSettings from "./workflow/components/WorkflowHeaderSettings.vue";
import WorkflowStoryboardBoard from "./workflow/components/WorkflowStoryboardBoard.vue";
import WorkflowCharacterBoard from "./workflow/components/WorkflowCharacterBoard.vue";
import WorkflowKeyframeBoard from "./workflow/components/WorkflowKeyframeBoard.vue";
import WorkflowVideoBoard from "./workflow/components/WorkflowVideoBoard.vue";
import WorkflowFinalBoard from "./workflow/components/WorkflowFinalBoard.vue";
import ImagePreviewOverlay from "./workflow/components/ImagePreviewOverlay.vue";
import CharacterSummaryDialog from "./workflow/components/CharacterSummaryDialog.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { IconVideo } from "@/components/icons";

type DetailRouteStageKey = WorkflowDetailRouteStageKey;
type CanvasStageKey = WorkflowCanvasStageKey;

// --- Composables ---
const workflowOptions = useWorkflowOptions();
const workflowList = useWorkflowList();
const previewInteractions = useWorkflowPreviewInteractions({
  keyframePreviewFrames,
  stageVersionDisplayTitle,
});
const { handleDownloadVideo, positionVersionMenu } = useStageWorkflowInteractions();

const { aspectRatioOptions, textModelOptions, imageModelOptions, videoModelOptions, catalogVideoSizeOptions, filterVideoSizeOptions, syncVideoSizeSelection, loadOptions } = workflowOptions;

const { loadingWorkflows, loadingMoreWorkflows, workflowSearch, workflowFilter, workflows, filteredWorkflows, hasMoreWorkflows, workflowCompletionPercentage, loadWorkflows, loadMoreWorkflows, setWorkflowPageSize } = workflowList;

const refreshingWorkflows = ref(false);

function toAppSelectOptions<T extends { label: string; value: unknown }>(items: T[]): AppSelectOption[] {
  return items.map((item) => ({
    label: item.label,
    value: item.value,
  }));
}

const textModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(textModelOptions.value));
const imageModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(imageModelOptions.value));
const videoModelSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(videoModelOptions.value));
const aspectRatioSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(aspectRatioOptions.value));
const {
  imagePreviewOverlayRef,
  imagePreviewState,
  imagePreviewCaption,
  openImagePreview,
  closeImagePreview,
  switchImagePreviewFrame,
  characterSummaryPreviewState,
  openCharacterSummaryPreview,
  closeCharacterSummaryPreview,
  openKeyframeImagePreview,
} = previewInteractions;

const loadingDetail = ref(false);
const busyActionKey = ref("");
const activeCreateStage = ref<DetailRouteStageKey>("storyboard");
const activeCanvasStage = ref<CanvasStageKey>("storyboard");
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const selectedWorkflow = ref<WorkflowDetail | null>(null);
const {
  previewStoryboardVersionId,
  previewCharacterSheetVersionIds,
  selectedCanvasClipIndex,
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
} = useWorkflowStagePreviews(selectedWorkflow);
const workflowSettingsOpen = ref(false);
const workflowSettingsDraft = reactive<WorkflowSettingsDraft>(createWorkflowSettingsDraft());

const {
  applyWorkflowDrafts,
  loadWorkflowDetail,
  navigateToTaskList,
  openWorkflow,
  reloadCurrentWorkflow,
  selectedWorkflowId,
  showDetailLoadFailed,
  switchCanvasStage,
  switchWorkflowStage,
} = useStageWorkflowDetailLoader({
  selectedWorkflow,
  loadingDetail,
  activeCreateStage,
  activeCanvasStage,
  selectedCanvasClipIndex,
  previewStoryboardVersionId,
  workflowSettingsOpen,
  workflowSettingsDraft,
  syncVideoSizeSelection,
  applyPreviewSelections,
  loadWorkflows,
});

function applyWorkflowSettingsDraft(settings: WorkflowSettingsDraft) {
  Object.assign(workflowSettingsDraft, settings);
}
const {
  workflowCharacterSheets,
  missingCharacterSheets,
  videoReadiness,
  canvasStageItems,
  canFinalize,
  finalizeButtonLabel,
  finalizeHint,
} = useWorkflowStageReadiness(selectedWorkflow);

const workflowSettingsVideoSizeOptions = computed(() => filterVideoSizeOptions(catalogVideoSizeOptions.value, workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio));
const workflowSettingsVideoSizeSelectOptions = computed<AppSelectOption[]>(() => toAppSelectOptions(workflowSettingsVideoSizeOptions.value));
const workflowParameterTags = computed(() => {
  const workflow = selectedWorkflow.value;
  if (!workflow) {
    return [];
  }
  return [
    { label: "类型", value: "视频生成" },
    { label: "状态", value: formatWorkflowStatus(workflow.status) },
    { label: "画幅", value: workflow.aspectRatio || "未设置" },
    { label: "进度", value: `${workflowCompletionPercentage(workflow)}%` },
  ];
});
const workflowSettingsValidationMessage = computed(() => validateWorkflowSettingsDraft(workflowSettingsDraft));

function openMissingVideoClip(clipIndex: number) {
  selectCanvasClip(clipIndex);
  switchCanvasStage("video");
}

async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>) {
  const authenticated = await requireAuth({
    title: "登录后操作工作流",
    message: "工作流操作会修改你的个人数据，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续操作工作流。");
    return false;
  }
  busyActionKey.value = actionKey;
  try {
    selectedWorkflow.value = await runner();
    applyWorkflowDrafts(selectedWorkflow.value);
    await loadWorkflows();
    return true;
  } catch (error) {
    messageApi.error(formatApiErrorMessage(error, "操作失败"));
    return false;
  } finally {
    busyActionKey.value = "";
  }
}

const {
  handleGenerateStoryboard,
  handleAdjustStoryboard,
  handleSelectStoryboard,
  handleGenerateKeyframe,
  handleGenerateCharacterSheet,
  handleGenerateKeyframeFrame,
  handleSelectKeyframe,
  handleSelectKeyframeFrame,
  handleGenerateVideo,
  handleSelectVideo,
  handleFinalize,
} = useWorkflowStageCommands({
  selectedWorkflowId,
  runAndRefresh,
  storyboardAdjustment,
  setStoryboardAdjustment,
});

const {
  handleDeleteStageVersion,
  handleClearStageVersions,
  handleReuseAsset,
} = useWorkflowVersionCommands({
  selectedWorkflowId,
  selectedWorkflow,
  busyActionKey,
  workflowCharacterSheets,
  applyWorkflowDrafts,
  reloadWorkflows: loadWorkflows,
  requestConfirm,
  deleteVersionConfirmMessage,
  onReused: (workflow) => openWorkflow(workflow.id, workflow.currentStage),
});

const {
  handleUpdateWorkflowSettings,
  handleGenerateMissingCharacterSheets,
  handleSelectCharacterSheetAsset,
  handleDeleteWorkflow,
} = useStageWorkflowManagementCommands({
  selectedWorkflowId,
  selectedWorkflow,
  busyActionKey,
  workflowSettingsOpen,
  workflowSettingsValidationMessage,
  workflowSettingsDraft,
  missingCharacterSheets,
  applyWorkflowDrafts,
  loadWorkflows,
  reloadCurrentWorkflow,
  runAndRefresh,
  requestConfirm,
  navigateAfterSelectedDelete: navigateToTaskList,
});

function stageTypeLabel(stageType: StageVersion["stageType"]) {
  switch (stageType) {
    case "storyboard":
      return "分镜";
    case "keyframe":
      return "关键帧";
    case "video":
      return "视频";
    default:
      return "版本";
  }
}

function deleteVersionConfirmMessage(version: StageVersion) {
  const stageLabel = stageTypeLabel(version.stageType);
  if (version.stageType === "storyboard") {
    return `删除后不可恢复。删除该${stageLabel}版本时，与它关联的关键帧和视频版本也会一并删除。确认继续吗？`;
  }
  if (version.stageType === "keyframe") {
    return `删除后不可恢复。删除该${stageLabel}版本时，依赖它生成的视频版本也会一并删除。确认继续吗？`;
  }
  return `删除后不可恢复，确认删除这个${stageLabel}版本吗？`;
}

watch(
  () => [workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio, catalogVideoSizeOptions.value] as const,
  () => {
    syncVideoSizeSelection(workflowSettingsDraft, workflowSettingsDraft.videoSize);
  },
);

async function handleRefreshWorkflows() {
  if (refreshingWorkflows.value || loadingWorkflows.value || loadingMoreWorkflows.value) {
    return;
  }
  refreshingWorkflows.value = true;
  try {
    await loadWorkflows({ mode: "refresh" });
  } finally {
    refreshingWorkflows.value = false;
  }
}

onMounted(async () => {
  await loadOptions();
  await loadWorkflows();
});
</script>

<style scoped src="./stage-workflow-view.css"></style>

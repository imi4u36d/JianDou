<template>
  <section class="workflow-canvas-main">
    <div v-if="loadingDetail" class="surface-panel workflow-empty workflow-empty-large">加载中</div>
    <div v-else-if="!selectedWorkflow" class="surface-panel workflow-empty workflow-empty-large">
      <h3>选择工作流</h3>
    </div>

    <template v-else>
      <WorkflowHeaderSettings
        v-model:open="workflowSettingsOpen"
        :title="selectedWorkflow.title"
        :parameter-tags="workflowHeaderTags"
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
      >
        <template #actions>
          <button
            v-if="showReturnButton"
            class="jd-button jd-button--secondary jd-button--sm"
            type="button"
            :title="returnButtonLabel"
            @click="$emit('return')"
          >
            <IconTask size="sm" />
            <span>{{ returnButtonLabel }}</span>
          </button>
          <button
            v-if="canOpenResultView"
            class="jd-button jd-button--secondary jd-button--sm workflow-task-view-btn"
            type="button"
            title="切换到任务视图"
            @click="$emit('openResult')"
          >
            <IconVideo size="sm" />
            <span>任务视图</span>
          </button>
        </template>
      </WorkflowHeaderSettings>

      <WorkflowAutoPilotBar
        :auto-pilot="autoPilot"
        :execution-mode="executionMode"
        :queue-position="selectedWorkflow.queuePosition"
        :recent-log="recentLog"
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

          <!-- ── 公共素材 ── -->
          <section v-else-if="activeCanvasStage === 'character'" class="workflow-stage-board character-board">
            <div class="stage-board__head">
              <h3>公共素材</h3>
              <div class="stage-board__meta">
                <span class="surface-chip">{{ workflowCharacterSheets.length }} 个角色</span>
                <button
                  v-if="workflowCharacterSheets.some((sheet) => characterSheetVersions(sheet).length > 0)"
                  class="jd-button jd-button--secondary jd-button--sm workflow-menu-danger"
                  type="button"
                  :disabled="busyActionKey === 'clear-character-versions'"
                  @click="handleClearStageVersions('character')"
                >
                  <IconLoading v-if="busyActionKey === 'clear-character-versions'" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === 'clear-character-versions' ? '清空中' : '清空素材版本' }}</span>
                </button>
                <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="!missingCharacterSheets.length || busyActionKey === 'character-missing'" @click="handleGenerateMissingCharacterSheets">
                  <IconLoading v-if="busyActionKey === 'character-missing'" size="xs" />
                  <span>{{ busyActionKey === "character-missing" ? "补齐中" : "补齐" }}</span>
                </button>
              </div>
            </div>
            <div v-if="!workflowCharacterSheets.length" class="workflow-empty workflow-empty-nested">暂无公共素材</div>
            <div v-else class="character-strip__list">
              <article v-for="sheet in workflowCharacterSheets" :key="characterSheetKey(sheet)" class="character-mini-card">
                <div class="character-mini-card__head">
                  <strong>{{ characterSheetTitle(sheet) }}</strong>
                  <button
                    class="workflow-icon-action"
                    type="button"
                    title="重新生成"
                    :disabled="characterSheetClipIndex(sheet) === null || busyActionKey === `character-sheet-${characterSheetClipIndex(sheet)}`"
                    @click="handleGenerateCharacterSheet(sheet)"
                  >
                    <IconLoading v-if="busyActionKey === `character-sheet-${characterSheetClipIndex(sheet)}`" size="xs" />
                    <IconRefresh v-else size="xs" />
                  </button>
                </div>
                <div v-if="characterSheetVersions(sheet).length" class="version-switcher character-version-switcher">
                  <div class="version-switcher__tabs">
                    <article
                      v-for="version in characterSheetVersions(sheet)"
                      :key="version.id"
                      class="version-switcher__tab"
                      :class="{ 'version-switcher__tab-active': previewCharacterSheetVersion(sheet)?.id === version.id }"
                    >
                      <button type="button" class="version-switcher__tab-main" @click="setPreviewCharacterSheetVersion(characterSheetKey(sheet), version.id)">
                        <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                        <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                        <span class="compact-version-card__status">{{ version.selected ? "当前" : stageStatusLabel(version.status) }}</span>
                      </button>
                      <div class="workflow-more-menu compact-version-menu">
                        <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`wfd-char-${version.id}`"><IconMore size="sm" /></button>
                        <div :id="`wfd-char-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                          <button type="button" :disabled="version.selected || busyActionKey === version.id || characterSheetClipIndex(sheet) === null" @click="handleSelectCharacterSheetVersion(sheet, version.id)"><IconCheck size="xs" /><span>{{ version.selected ? "当前" : "设为当前" }}</span></button>
                          <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="handleDeleteStageVersion(version)"><IconDelete size="xs" /><span>删除</span></button>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>
                <button type="button" class="character-mini-card__summary" @click="openCharacterSummaryPreview(sheet)">
                  <span class="character-mini-card__summary-label">角色定义</span>
                  <p>{{ characterSheetAppearanceSummary(sheet) }}</p>
                </button>
                <div v-if="previewCharacterSheetVersion(sheet)" class="character-mini-card__frames">
                  <button
                    v-for="frame in characterSheetPreviewFrames(previewCharacterSheetVersion(sheet)!)"
                    :key="`${characterSheetKey(sheet)}-${frame.role}`"
                    type="button"
                    class="character-mini-frame"
                    @click="openImagePreview(frame.url, `${characterSheetTitle(sheet)} ${frame.label}`)"
                  >
                    <img v-if="isPreviewImageAvailable(frame.url)" :src="frame.url" :alt="`${characterSheetTitle(sheet)} ${frame.label}`" @error="markPreviewImageFailed(frame.url)" />
                    <span v-else class="workflow-image-fallback" aria-hidden="true"><IconEmpty size="sm" /></span>
                    <span>{{ frame.label }}</span>
                  </button>
                </div>
                <div class="character-mini-card__actions">
                  <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="characterSheetClipIndex(sheet) === null" @click="openCharacterAssetPicker(sheet)">
                    <IconSearch size="xs" /><span>素材</span>
                  </button>
                </div>
                <WorkflowCharacterAssetPicker
                  v-if="isCharacterAssetPickerOpen(sheet)"
                  :title="characterSheetTitle(sheet)"
                  :picker="characterAssetPicker"
                  :busy="busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}`"
                  :is-preview-image-available="isPreviewImageAvailable"
                  @close="closeCharacterAssetPicker"
                  @search="loadCharacterAssetCandidates(sheet)"
                  @update:keyword="characterAssetPicker.keyword = $event"
                  @preview="openImagePreview"
                  @image-error="markPreviewImageFailed"
                  @select="handleSelectCharacterSheetAsset(sheet, $event)"
                />
              </article>
            </div>
          </section>

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
  </section>
</template>

<script setup lang="ts">
/**
 * 工作流详情面板组件。
 * 从 StageWorkflowView 提取，展示工作流的阶段流水线编辑器。
 */
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import { computed } from "vue";
import WorkflowAutoPilotBar from "./WorkflowAutoPilotBar.vue";
import WorkflowCharacterAssetPicker from "./WorkflowCharacterAssetPicker.vue";
import WorkflowStagePipeline from "@/views/workflow/components/WorkflowStagePipeline.vue";
import WorkflowFinalBoard from "@/views/workflow/components/WorkflowFinalBoard.vue";
import WorkflowKeyframeBoard from "@/views/workflow/components/WorkflowKeyframeBoard.vue";
import WorkflowStoryboardBoard from "@/views/workflow/components/WorkflowStoryboardBoard.vue";
import WorkflowVideoBoard from "@/views/workflow/components/WorkflowVideoBoard.vue";
import WorkflowHeaderSettings from "@/views/workflow/components/WorkflowHeaderSettings.vue";
import CharacterSummaryDialog from "@/views/workflow/components/CharacterSummaryDialog.vue";
import ImagePreviewOverlay from "@/views/workflow/components/ImagePreviewOverlay.vue";
import type { WorkflowSettingsDraft } from "@/features/workflows/workflow-settings";
import {
  IconCheck,
  IconDelete,
  IconEmpty,
  IconLoading,
  IconMore,
  IconRefresh,
  IconSearch,
  IconTask,
  IconVideo,
} from "@/components/icons";
import { useWorkflowDetail } from "../composables/useWorkflowDetail";
import { useWorkflowDetailHeader } from "../composables/useWorkflowDetailHeader";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";

const props = defineProps<{
  selectedWorkflowId: string;
  reloadWorkflows: () => Promise<void>;
  showReturnButton?: boolean;
  returnButtonLabel?: string;
}>();

defineEmits<{
  openResult: [];
  return: [];
}>();

const detail = useWorkflowDetail({
  selectedWorkflowId: () => props.selectedWorkflowId,
  reloadWorkflows: props.reloadWorkflows,
});

function applyWorkflowSettingsDraft(settings: WorkflowSettingsDraft) {
  Object.assign(detail.workflowSettingsDraft, settings);
}

const {
  autoPilot,
  executionMode,
  recentLog,
  showReturnButton,
  returnButtonLabel,
  canOpenResultView,
  workflowHeaderTags,
} = useWorkflowDetailHeader({
  workflowId: () => props.selectedWorkflowId,
  workflow: detail.selectedWorkflow,
  stages: detail.canvasStageItems,
  pollWorkflow: detail.pollCurrentWorkflow,
  showReturnButton: () => props.showReturnButton === true,
  returnButtonLabel: () => props.returnButtonLabel,
});

const {
  selectedWorkflow,
  loadingDetail,
  busyActionKey,
  activeCanvasStage,
  workflowSettingsOpen,
  workflowSettingsDraft,
  workflowSettingsValidationMessage,
  storyboardAdjustmentDrafts,
  characterSummaryPreviewState,
  confirmDialog,
  acceptConfirm,
  cancelConfirm,
  canvasStageItems,
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
  textModelSelectOptions,
  imageModelSelectOptions,
  videoModelSelectOptions,
  aspectRatioSelectOptions,
  workflowSettingsVideoSizeSelectOptions,
  imagePreviewOverlayRef,
  imagePreviewState,
  imagePreviewCaption,
  openImagePreview,
  closeImagePreview,
  switchImagePreviewFrame,
  characterAssetPicker,
  isCharacterAssetPickerOpen,
  openCharacterAssetPicker,
  closeCharacterAssetPicker,
  loadCharacterAssetCandidates,
  stageVersionDisplayTitle,
  stageStatusLabel,
  selectCanvasClip,
  isPreviewImageAvailable,
  markPreviewImageFailed,
  openCharacterSummaryPreview,
  closeCharacterSummaryPreview,
  openKeyframeImagePreview,
  positionVersionMenu,
  previewCharacterSheetVersion,
  characterSheetKey,
  characterSheetClipIndex,
  characterSheetTitle,
  characterSheetAppearanceSummary,
  characterSheetVersions,
  characterSheetPreviewFrames,
  setPreviewStoryboardVersion,
  setPreviewCharacterSheetVersion,
  setPreviewKeyframeVersion,
  setPreviewVideoVersion,
  switchCanvasStage,
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
} = detail;

const selectedStoryboardAdjustment = computed(() => {
  const versionId = selectedStoryboardVersion.value?.id;
  return versionId ? storyboardAdjustmentDrafts[versionId] ?? "" : "";
});

function updateSelectedStoryboardAdjustment(value: string) {
  const versionId = selectedStoryboardVersion.value?.id;
  if (versionId) storyboardAdjustmentDrafts[versionId] = value;
}

function openMissingVideoClip(clipIndex: number) {
  selectCanvasClip(clipIndex);
  switchCanvasStage("video");
}

async function handleDownloadVideo(url: string, title: string) {
  try {
    const result = await downloadMedia({ url, title, mediaType: "video" });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}
</script>

<style scoped src="./workflow-detail-panel.css"></style>

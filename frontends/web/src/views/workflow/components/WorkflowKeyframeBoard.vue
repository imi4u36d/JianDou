<template>
  <section class="workflow-stage-board keyframe-board">
    <div class="stage-board__head">
      <h3>关键帧</h3>
      <div class="stage-board__head-actions">
        <button
          v-if="hasVersions"
          class="jd-button jd-button--secondary jd-button--sm workflow-menu-danger"
          type="button"
          :disabled="busyActionKey === 'clear-keyframe-versions'"
          @click="$emit('clear')"
        >
          <IconLoading v-if="busyActionKey === 'clear-keyframe-versions'" size="xs" /><IconDelete v-else size="xs" />
          <span>{{ busyActionKey === "clear-keyframe-versions" ? "清空中" : "清空关键帧版本" }}</span>
        </button>
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="!selectedClip || busyActionKey === `keyframe-${selectedClip.clipIndex}`"
          @click="selectedClip && $emit('generate', selectedClip.clipIndex)"
        >
          <IconLoading v-if="selectedClip && busyActionKey === `keyframe-${selectedClip.clipIndex}`" size="xs" />
          <span>{{ selectedClip && busyActionKey === `keyframe-${selectedClip.clipIndex}` ? "生成中" : "生成" }}</span>
        </button>
      </div>
    </div>

    <section class="clip-workbench">
      <nav class="clip-timeline" aria-label="镜头列表">
        <button
          v-for="slot in slots"
          :key="slot.clipIndex"
          type="button"
          class="clip-timeline__item"
          :class="{ 'clip-timeline__item-active': selectedClip?.clipIndex === slot.clipIndex }"
          @click="$emit('select-clip', slot.clipIndex)"
        >
          <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong>
          <span>{{ slot.keyframeVersions.length ? `${slot.keyframeVersions.length} 版` : "未生成" }}</span>
        </button>
      </nav>

      <article v-if="selectedClip" class="clip-detail-card">
        <div class="clip-detail-card__head">
          <div>
            <h4>{{ selectedClip.shotLabel || `镜头 #${selectedClip.clipIndex}` }}</h4>
            <p>{{ clipSceneSummary(selectedClip) }}</p>
          </div>
          <span class="surface-chip">{{
            selectedClip.durationHint || `${selectedClip.targetDurationSeconds || 0}s`
          }}</span>
        </div>

        <div v-if="selectedClip.keyframeVersions.length" class="version-tabs">
          <article
            v-for="version in selectedClip.keyframeVersions"
            :key="version.id"
            class="version-tab"
            :class="{ 'version-tab-active': previewVersion?.id === version.id }"
          >
            <button
              type="button"
              class="version-tab__main"
              @click="$emit('preview-version', selectedClip.clipIndex, version.id)"
            >
              <span class="version-badge">V{{ version.versionNo }}</span
              ><strong>{{ stageVersionDisplayTitle(version) }}</strong
              ><span v-if="keyframeVersionHasSelectedFrame(version)" class="surface-chip">当前</span>
            </button>
            <div class="more-menu workflow-more-menu">
              <button
                type="button"
                class="more-menu__trigger workflow-more-menu__trigger"
                aria-label="版本操作"
                :popovertarget="`kfm-${version.id}`"
              >
                <IconMore size="sm" />
              </button>
              <div
                :id="`kfm-${version.id}`"
                popover
                class="more-menu__popover workflow-more-menu__popover"
                @beforetoggle="$emit('position-menu', $event)"
              >
                <button
                  type="button"
                  :disabled="version.selected || busyActionKey === version.id"
                  @click="$emit('select-version', selectedClip.clipIndex, version.id)"
                >
                  <IconCheck size="xs" /><span>设为当前</span>
                </button>
                <button
                  type="button"
                  :disabled="!version.asset || busyActionKey === `reuse-${version.id}`"
                  @click="$emit('reuse', version.asset?.id || '', version.id)"
                >
                  <IconPlus size="xs" /><span>复用</span>
                </button>
                <button
                  type="button"
                  class="workflow-menu-danger"
                  :disabled="busyActionKey === `delete-${version.id}`"
                  @click="$emit('delete', version)"
                >
                  <IconDelete size="xs" /><span>删除</span>
                </button>
              </div>
            </div>
          </article>
        </div>

        <div
          v-if="previewVersion"
          class="frame-grid"
          :class="isLandscape(previewVersion) ? 'frame-grid-landscape' : 'frame-grid-portrait'"
        >
          <article
            v-for="frame in keyframePreviewFrames(previewVersion, selectedClip)"
            :key="`${selectedClip.clipIndex}-${frame.role}`"
            class="frame-card"
          >
            <div class="frame-card__head">
              <span class="surface-chip surface-chip-quiet">{{ frame.label }}</span
              ><span v-if="frame.selected" class="surface-chip">已选</span>
            </div>
            <button
              v-if="frame.url && isImageAvailable(frame.url)"
              type="button"
              class="frame-card__preview"
              :aria-label="`查看${frame.label}原图`"
              @click="$emit('preview-image', previewVersion, frame)"
            >
              <img :src="frame.url" :alt="frame.label" @error="markImageFailed(frame.url)" />
            </button>
            <div v-else class="frame-card__failure" :title="frame.errorMessage || frame.label">
              <IconWarning v-if="frame.errorMessage" size="sm" /><IconEmpty v-else size="sm" /><strong>{{
                frame.errorMessage ? "生成失败" : frame.label
              }}</strong>
            </div>
            <div class="frame-card__actions">
              <button
                v-if="!frame.selected"
                class="icon-action"
                type="button"
                :disabled="busyActionKey === `${previewVersion.id}-${frame.role}`"
                aria-label="设为当前"
                @click="$emit('select-frame', selectedClip.clipIndex, previewVersion.id, frame.role)"
              >
                <IconCheck size="xs" />
              </button>
              <button
                class="icon-action"
                type="button"
                :disabled="!frame.regenerable || busyActionKey === `keyframe-${selectedClip.clipIndex}-${frame.role}`"
                aria-label="重新生成"
                @click="$emit('generate-frame', selectedClip.clipIndex, frame.role)"
              >
                <IconRefresh size="xs" />
              </button>
            </div>
          </article>
        </div>
        <WorkflowStageEmptyState
          v-else
          title="还没有关键帧"
          description="为当前镜头生成首尾关键帧，确认画面后即可进入视频生成。"
        />
      </article>
      <WorkflowStageEmptyState
        v-else
        title="选择分镜版本"
        description="从左侧镜头列表选择要处理的镜头，再生成或查看关键帧。"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  clipSceneSummary,
  isLandscapeKeyframeVersion,
  keyframePreviewFrames,
  keyframeVersionHasSelectedFrame,
  stageVersionDisplayTitle,
} from "@/features/workflows/stage-workflow-presenters";
import type { WorkflowPreviewFrame } from "@/features/workflows/stage-workflow-presenters";
import type { StageVersion, WorkflowClipSlot } from "@/types";
import {
  IconCheck,
  IconDelete,
  IconEmpty,
  IconLoading,
  IconMore,
  IconPlus,
  IconRefresh,
  IconWarning,
} from "@/components/icons";
import WorkflowStageEmptyState from "./WorkflowStageEmptyState.vue";

const props = defineProps<{
  slots: WorkflowClipSlot[];
  selectedClip: WorkflowClipSlot | null;
  previewVersion: StageVersion | null;
  aspectRatio: string;
  busyActionKey: string;
}>();
defineEmits<{
  clear: [];
  generate: [clipIndex: number];
  "select-clip": [clipIndex: number];
  "preview-version": [clipIndex: number, versionId: string];
  "select-version": [clipIndex: number, versionId: string];
  reuse: [assetId: string, versionId: string];
  delete: [version: StageVersion];
  "position-menu": [event: ToggleEvent];
  "preview-image": [version: StageVersion, frame: WorkflowPreviewFrame];
  "select-frame": [clipIndex: number, versionId: string, frameRole: string];
  "generate-frame": [clipIndex: number, frameRole: string];
}>();

const failedImageUrls = ref(new Set<string>());
const hasVersions = computed(() => props.slots.some((slot) => slot.keyframeVersions.length > 0));
const isLandscape = (version: StageVersion) => isLandscapeKeyframeVersion(version, props.aspectRatio);
const isImageAvailable = (url: string) => !failedImageUrls.value.has(url);
const markImageFailed = (url: string) => failedImageUrls.value.add(url);
</script>

<style scoped src="./workflow-keyframe-board.css"></style>

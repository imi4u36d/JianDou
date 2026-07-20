<template>
  <section class="workflow-stage-board video-board">
    <div class="stage-board__head">
      <h3>视频片段</h3>
      <div class="stage-board__meta">
        <div class="readiness-strip">
          <span>{{ readiness.total }} 镜头</span><span>{{ readiness.generated }} 片段</span
          ><span>{{ readiness.selected }} 已选</span
          ><span>{{ canFinalize ? "可拼接" : `差 ${readiness.missing.length}` }}</span>
        </div>
        <button
          v-if="readiness.generated > 0"
          class="jd-button jd-button--secondary jd-button--sm workflow-menu-danger"
          type="button"
          :disabled="busyActionKey === 'clear-video-versions'"
          @click="$emit('clear')"
        >
          <IconLoading v-if="busyActionKey === 'clear-video-versions'" size="xs" /><IconDelete
            v-else
            size="xs"
          /><span>{{ busyActionKey === "clear-video-versions" ? "清空中" : "清空视频版本" }}</span>
        </button>
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="
            !selectedClip ||
            !selectedKeyframeVersion(selectedClip) ||
            busyActionKey === `video-${selectedClip.clipIndex}`
          "
          @click="selectedClip && $emit('generate', selectedClip.clipIndex)"
        >
          <IconLoading v-if="selectedClip && busyActionKey === `video-${selectedClip.clipIndex}`" size="xs" /><span>{{
            selectedClip && busyActionKey === `video-${selectedClip.clipIndex}` ? "生成中" : "生成"
          }}</span>
        </button>
      </div>
    </div>

    <section class="clip-workbench">
      <nav class="clip-timeline" aria-label="视频镜头列表">
        <button
          v-for="slot in slots"
          :key="slot.clipIndex"
          type="button"
          class="clip-timeline__item"
          :class="{ 'clip-timeline__item-active': selectedClip?.clipIndex === slot.clipIndex }"
          @click="$emit('select-clip', slot.clipIndex)"
        >
          <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong
          ><span>{{ videoSlotStatusLabel(slot) }}</span>
        </button>
      </nav>

      <article v-if="selectedClip" class="clip-detail-card">
        <div class="clip-detail-card__head">
          <div>
            <h4>{{ selectedClip.shotLabel || `镜头 #${selectedClip.clipIndex}` }}</h4>
            <p>{{ clipSceneSummary(selectedClip) }}</p>
          </div>
          <span class="surface-chip">{{
            selectedKeyframeVersion(selectedClip)
              ? stageVersionDisplayTitle(selectedKeyframeVersion(selectedClip)!)
              : "缺关键帧"
          }}</span>
        </div>

        <div v-if="selectedKeyframePreviewFrames(selectedClip).length" class="keyframe-thumbs">
          <article
            v-for="frame in selectedKeyframePreviewFrames(selectedClip)"
            :key="frame.role"
            class="keyframe-thumb"
          >
            <img
              v-if="isImageAvailable(frame.url)"
              :src="frame.url"
              :alt="frame.label"
              @error="markImageFailed(frame.url)"
            />
            <div v-else class="image-fallback"><IconEmpty size="sm" /></div>
            <span class="surface-chip surface-chip-quiet">{{ frame.label }}</span>
          </article>
        </div>

        <WorkflowStageEmptyState
          v-if="!selectedClip.videoVersions.length"
          title="暂无视频版本"
          :description="
            selectedKeyframeVersion(selectedClip)
              ? '点击右上角“生成”，将当前镜头的关键帧转成视频片段。'
              : '请先在关键帧阶段为当前镜头选择关键帧。'
          "
        />
        <div v-else class="video-version-panel">
          <div class="version-tabs">
            <article
              v-for="version in selectedClip.videoVersions"
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
                ><span v-if="version.selected" class="surface-chip">当前</span>
              </button>
              <div class="more-menu workflow-more-menu">
                <button
                  type="button"
                  class="more-menu__trigger workflow-more-menu__trigger"
                  aria-label="版本操作"
                  :popovertarget="`vm-${version.id}`"
                >
                  <IconMore size="sm" />
                </button>
                <div
                  :id="`vm-${version.id}`"
                  popover
                  class="more-menu__popover workflow-more-menu__popover"
                  @beforetoggle="$emit('position-menu', $event)"
                >
                  <button
                    type="button"
                    :disabled="!canSelectVideoVersion(version) || version.selected || busyActionKey === version.id"
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
                    v-if="version.downloadUrl"
                    type="button"
                    @click="$emit('download', version.downloadUrl, stageVersionDisplayTitle(version))"
                  >
                    <IconDownload size="xs" /><span>下载</span>
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

          <article v-if="previewVersion" class="video-card" :class="{ 'video-card-active': previewVersion.selected }">
            <div class="video-card__head">
              <div>
                <span class="version-badge">V{{ previewVersion.versionNo }}</span
                ><strong>{{ stageVersionDisplayTitle(previewVersion) }}</strong>
              </div>
              <span v-if="previewVersion.selected" class="surface-chip">当前</span>
            </div>
            <div
              v-if="videoVersionErrorMessage(previewVersion)"
              class="workflow-error"
              :title="videoVersionErrorMessage(previewVersion)"
            >
              {{ compactVideoVersionError(previewVersion) }}
            </div>
            <video
              v-else-if="previewVersion.previewUrl && canSelectVideoVersion(previewVersion)"
              :src="previewVersion.previewUrl"
              controls
              playsinline
              preload="metadata"
            ></video>
            <div v-else class="workflow-empty">{{ videoVersionStatusLabel(previewVersion) }}</div>
            <div class="video-card__actions">
              <button
                class="icon-action"
                type="button"
                :disabled="
                  !canSelectVideoVersion(previewVersion) ||
                  previewVersion.selected ||
                  busyActionKey === previewVersion.id
                "
                aria-label="设为当前"
                @click="$emit('select-version', selectedClip.clipIndex, previewVersion.id)"
              >
                <IconCheck size="xs" />
              </button>
              <button
                v-if="previewVersion.downloadUrl"
                class="icon-action"
                type="button"
                aria-label="下载视频"
                @click="$emit('download', previewVersion.downloadUrl, stageVersionDisplayTitle(previewVersion))"
              >
                <IconDownload size="xs" />
              </button>
            </div>
          </article>
        </div>
      </article>
      <WorkflowStageEmptyState
        v-else
        title="先选择一个镜头"
        description="从左侧镜头列表选择要处理的镜头，再生成或查看视频片段。"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  canSelectVideoVersion,
  clipSceneSummary,
  compactVideoVersionError,
  keyframePreviewFrames,
  stageVersionDisplayTitle,
  videoSlotStatusLabel,
  videoVersionErrorMessage,
  videoVersionStatusLabel,
} from "@/features/workflows/stage-workflow-presenters";
import type { WorkflowPreviewFrame } from "@/features/workflows/stage-workflow-presenters";
import type { StageVersion, WorkflowClipSlot } from "@/types";
import { IconCheck, IconDelete, IconDownload, IconEmpty, IconLoading, IconMore, IconPlus } from "@/components/icons";
import WorkflowStageEmptyState from "./WorkflowStageEmptyState.vue";

defineProps<{
  slots: WorkflowClipSlot[];
  selectedClip: WorkflowClipSlot | null;
  previewVersion: StageVersion | null;
  readiness: { total: number; generated: number; selected: number; missing: WorkflowClipSlot[] };
  canFinalize: boolean;
  busyActionKey: string;
}>();
defineEmits<{
  clear: [];
  generate: [clipIndex: number];
  "select-clip": [clipIndex: number];
  "preview-version": [clipIndex: number, versionId: string];
  "select-version": [clipIndex: number, versionId: string];
  reuse: [assetId: string, versionId: string];
  download: [url: string, title: string];
  delete: [version: StageVersion];
  "position-menu": [event: ToggleEvent];
}>();

const failedImageUrls = ref(new Set<string>());
const selectedKeyframeVersion = (slot: WorkflowClipSlot) =>
  slot.keyframeVersions.find((version) => version.selected) ?? null;
function selectedKeyframeFrameVersion(slot: WorkflowClipSlot, frameRole: "first" | "last") {
  const selectionKey = frameRole === "first" ? "selectedFirstFrame" : "selectedLastFrame";
  return (
    slot.keyframeVersions.find((version) => Boolean(version.outputSummary?.[selectionKey])) ??
    selectedKeyframeVersion(slot)
  );
}
function selectedKeyframePreviewFrames(slot: WorkflowClipSlot): WorkflowPreviewFrame[] {
  const frames: WorkflowPreviewFrame[] = [];
  const firstVersion = selectedKeyframeFrameVersion(slot, "first");
  const firstFrame = firstVersion
    ? keyframePreviewFrames(firstVersion, slot).find((frame) => frame.role === "first")
    : null;
  if (firstFrame) frames.push(firstFrame);
  const lastVersion = selectedKeyframeFrameVersion(slot, "last");
  const lastFrame = lastVersion
    ? keyframePreviewFrames(lastVersion, slot).find((frame) => frame.role === "last")
    : null;
  if (lastFrame && (!firstFrame || lastFrame.url !== firstFrame.url || slot.clipIndex === 1)) frames.push(lastFrame);
  return frames;
}
const isImageAvailable = (url: string) => Boolean(url && !failedImageUrls.value.has(url));
const markImageFailed = (url: string) => failedImageUrls.value.add(url);
</script>

<style scoped src="./workflow-video-board.css"></style>

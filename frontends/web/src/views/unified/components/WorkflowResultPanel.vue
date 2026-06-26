<template>
  <main class="workflow-result-panel">
    <section v-if="loading" class="workflow-result-empty">加载中</section>
    <section v-else-if="!workflow" class="workflow-result-empty">结果不存在</section>
    <section v-else class="workflow-result-content" aria-labelledby="workflow-result-title">
      <header class="workflow-result-header">
        <div>
          <h2 id="workflow-result-title">{{ workflow.title || "任务结果" }}</h2>
          <div class="workflow-result-header__meta">
            <span class="surface-chip">视频生成</span>
            <span class="surface-chip">{{ statusLabel }}</span>
            <span class="surface-chip">{{ workflow.aspectRatio || "未设置画幅" }}</span>
            <span class="surface-chip">{{ progressPercent }}%</span>
          </div>
        </div>
        <div class="workflow-result-header__actions">
          <button class="workflow-result-download" type="button" :disabled="loading" @click="loadWorkflow">
            <IconRefresh size="xs" />
            刷新
          </button>
          <button class="workflow-result-stage-btn" type="button" @click="$emit('openStage')">
            <IconWorkflow size="xs" />
            阶段工作流
          </button>
        </div>
      </header>

      <section class="workflow-stage-card" aria-label="任务阶段">
        <div class="workflow-stage-line">
          <div v-for="stage in taskStages" :key="stage.key" class="workflow-stage-line__item" :class="`workflow-stage-line__item-${stage.state}`">
            <span class="workflow-stage-line__dot" :class="stageStateClass(stage.state)" aria-hidden="true"></span>
            <span class="workflow-stage-line__copy">
              <strong>{{ stage.label }}</strong>
              <small>{{ stage.stateLabel }}</small>
            </span>
          </div>
        </div>
      </section>

      <div class="workflow-result-grid workflow-result-grid-primary">
        <section class="workflow-result-preview detail-section-card">
          <div class="workflow-result-preview__head">
            <h3>结果预览</h3>
            <button
              v-if="previewFileUrl"
              class="workflow-result-download"
              type="button"
              @click="handleDownloadPreview"
            >
              <IconDownload size="xs" />
              下载
            </button>
          </div>
          <div v-if="previewMedia?.type === 'video'" class="workflow-result-media">
            <video
              class="workflow-result-video"
              :src="previewMedia.url"
              controls
              playsinline
              preload="metadata"
              @loadstart="markFinalPreviewLoading"
              @loadedmetadata="markFinalPreviewReady"
              @loadeddata="markFinalPreviewReady"
              @canplay="markFinalPreviewReady"
              @error="markFinalPreviewFailed"
            ></video>
            <div v-if="finalPreviewLoading" class="workflow-result-media__loading" role="status" aria-live="polite">
              <IconLoading size="md" />
              <span>加载预览中</span>
            </div>
            <div v-else-if="finalPreviewLoadState === 'failed'" class="workflow-result-media__loading workflow-result-media__loading-error">
              <IconDownload size="sm" />
              <span>预览加载失败，可尝试下载查看</span>
            </div>
          </div>
          <button
            v-else-if="previewMedia?.type === 'image'"
            class="workflow-result-image-button"
            type="button"
            @click="handleDownloadPreview"
          >
            <img :src="previewMedia.url" :alt="previewMedia.title" />
          </button>
          <div v-else class="workflow-result-placeholder">{{ previewPlaceholder }}</div>
        </section>

        <section class="workflow-result-summary detail-section-card">
          <div class="workflow-result-preview__head">
            <h3>参数</h3>
            <span class="surface-chip">{{ durationModeLabel }}</span>
          </div>
          <div class="workflow-param-tags" aria-label="任务参数">
            <div class="workflow-param-tag workflow-param-tag-progress">
              <span class="workflow-param-tag__label">进度</span>
              <div class="workflow-param-tag__progress">
                <div class="workflow-progress">
                  <div class="workflow-progress__fill" :style="{ width: `${progressPercent}%` }"></div>
                </div>
                <strong class="workflow-param-tag__value">{{ progressPercent }}%</strong>
              </div>
            </div>
            <div v-for="item in parameterRows" :key="item.label" class="workflow-param-tag">
              <span class="workflow-param-tag__label">{{ item.label }}</span>
              <strong class="workflow-param-tag__value" :title="item.value">{{ item.value }}</strong>
            </div>
          </div>
          <div v-if="workflow.transcriptText" class="workflow-note-block">
            <span>Prompt</span>
            <p>{{ workflow.transcriptText }}</p>
          </div>
        </section>
      </div>

      <section v-if="resultItems.length" class="detail-section-card">
        <div class="workflow-result-preview__head">
          <h3>结果素材</h3>
          <span class="surface-chip">{{ resultItems.length }} 个</span>
        </div>
        <div class="workflow-result-list">
          <button
            v-for="item in resultItems"
            :key="`${item.type}-${item.title}-${item.url}`"
            class="workflow-result-item"
            type="button"
            @click="handleDownloadMedia(item.url, item.title, item.type)"
          >
            <span class="workflow-result-item__icon" aria-hidden="true">
              <IconVideo v-if="item.type === 'video'" size="xs" />
              <IconImage v-else size="xs" />
            </span>
            <span class="workflow-result-item__copy">
              <strong>{{ item.title }}</strong>
              <small>{{ item.kind }}</small>
            </span>
          </button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fetchWorkflow } from "@/features/workflows";
import { IconDownload, IconImage, IconLoading, IconRefresh, IconVideo, IconWorkflow } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";
import type { WorkflowDetail } from "@/types";

const props = defineProps<{
  selectedWorkflowId: string;
}>();

defineEmits<{
  openStage: [];
}>();

const workflow = ref<WorkflowDetail | null>(null);
const loading = ref(false);

const finalPreviewUrl = computed(() => workflow.value?.finalResult?.previewUrl || workflow.value?.finalResult?.fileUrl || "");
const finalPreviewLoadState = ref<"idle" | "loading" | "ready" | "failed">("idle");
const finalPreviewLoading = computed(() => Boolean(previewMedia.value?.url) && finalPreviewLoadState.value === "loading");

type WorkflowTaskStageState = "pending" | "active" | "paused" | "done" | "failed";
type WorkflowResultMediaKind = "image" | "video";
type WorkflowTaskStageItem = {
  key: string;
  label: string;
  state: WorkflowTaskStageState;
  stateLabel: string;
};

const stageStateLabels: Record<WorkflowTaskStageState, string> = {
  pending: "等待",
  active: "进行中",
  paused: "已暂停",
  done: "已完成",
  failed: "失败",
};

const statusLabel = computed(() => {
  const status = String(workflow.value?.status ?? "").toUpperCase();
  if (status === "COMPLETED") return "已完成";
  if (status === "FAILED") return "失败";
  if (status === "RUNNING") return "生成中";
  if (status === "PAUSED") return "已暂停";
  return status || "未知";
});

const autoPilotLabel = computed(() => {
  const state = String(workflow.value?.autoPilotState ?? "").toLowerCase();
  if (state === "completed") return "已完成";
  if (state === "running") return "执行中";
  if (state === "queued") return "排队中";
  if (state === "paused") return "已暂停";
  if (state === "failed") return "失败";
  return workflow.value?.executionMode === "auto" ? "可继续" : "手动";
});

const progressPercent = computed(() => {
  const current = workflow.value;
  if (!current) return 0;
  const status = String(current.status || "").toUpperCase();
  if (status === "COMPLETED") return 100;
  if (status === "FAILED") return 0;
  const hasStoryboard = current.storyboardVersions.length > 0;
  const totalClips = current.clipSlots.length;
  const keyframeReady = current.clipSlots.filter((slot) => slot.keyframeVersions.some((version) => version.selected || version.asset)).length;
  const videoReady = current.clipSlots.filter((slot) => slot.videoVersions.some((version) => version.selected || version.asset)).length;
  const storyboardPart = hasStoryboard ? 20 : 6;
  const keyframePart = totalClips ? Math.round((keyframeReady / totalClips) * 35) : 0;
  const videoPart = totalClips ? Math.round((videoReady / totalClips) * 35) : 0;
  const finalPart = current.finalResult ? 10 : 0;
  return Math.max(0, Math.min(99, storyboardPart + keyframePart + videoPart + finalPart));
});

const durationModeLabel = computed(() => workflow.value?.durationMode === "manual" ? "手动时长" : "自动时长");

const parameterRows = computed(() => {
  const current = workflow.value;
  if (!current) return [];
  return [
    { label: "镜头数量", value: `${current.clipSlots.length} 个` },
    { label: "分镜版本", value: `${current.storyboardVersions.length} 个` },
    { label: "关键帧", value: `${current.clipSlots.reduce((sum, slot) => sum + slot.keyframeVersions.length, 0)} 个` },
    { label: "视频片段", value: `${current.clipSlots.reduce((sum, slot) => sum + slot.videoVersions.length, 0)} 个` },
    { label: "文本模型", value: current.textAnalysisModel || "未设置" },
    { label: "关键帧模型", value: current.imageModel || "未设置" },
    { label: "视频模型", value: current.videoModel || "未设置" },
    { label: "输出尺寸", value: current.videoSize || "未设置" },
    { label: "自动模式", value: autoPilotLabel.value },
  ];
});

const taskStages = computed(() => {
  const current = workflow.value;
  if (!current) return [];
  const status = String(current.status || "").toUpperCase();
  const state = String(current.autoPilotState || "").toLowerCase();
  const failed = status === "FAILED" || state === "failed";
  const paused = status === "PAUSED" || state === "paused";
  const hasStoryboard = current.storyboardVersions.length > 0;
  const totalClips = current.clipSlots.length;
  const keyframesReady = totalClips > 0 && current.clipSlots.every((slot) => slot.keyframeVersions.length > 0);
  const videosReady = totalClips > 0 && current.clipSlots.every((slot) => slot.videoVersions.length > 0);
  const finalReady = Boolean(current.finalResult) || status === "COMPLETED";
  const activeStage = String(current.currentStage || "").toLowerCase();
  const itemState = (key: string, done: boolean): WorkflowTaskStageState => {
    if (failed && activeStage === key) return "failed";
    if (paused && activeStage === key) return "paused";
    if (done) return "done";
    if (!failed && !paused && activeStage === key) return "active";
    return "pending";
  };
  const stages: Array<Omit<WorkflowTaskStageItem, "stateLabel">> = [
    { key: "storyboard", label: "分镜脚本", state: itemState("storyboard", hasStoryboard) },
    { key: "keyframe", label: "关键帧", state: itemState("keyframe", keyframesReady) },
    { key: "video", label: "视频生成", state: itemState("video", videosReady) },
    { key: "joined", label: "任务完成", state: finalReady ? "done" : failed ? "failed" : "pending" as WorkflowTaskStageState },
  ];
  return stages.map((item) => ({ ...item, stateLabel: stageStateLabels[item.state] }));
});

const resultItems = computed(() => {
  const current = workflow.value;
  if (!current) return [];
  const items: Array<{ title: string; url: string; type: WorkflowResultMediaKind; kind: string }> = [];
  const finalResult = current.finalResult;
  const finalUrl = finalResult?.fileUrl || finalResult?.previewUrl || "";
  if (finalUrl) {
    items.push({
      title: finalResult?.title || "成片",
      url: finalUrl,
      type: "video",
      kind: "成片",
    });
  }
  for (const slot of current.clipSlots) {
    for (const version of slot.videoVersions) {
      const url = version.asset?.fileUrl || version.asset?.previewUrl || version.downloadUrl || version.previewUrl || "";
      if (url) {
        items.push({ title: version.title || `镜头 ${slot.clipIndex} 视频`, url, type: "video", kind: `镜头 ${slot.clipIndex}` });
      }
    }
  }
  for (const slot of current.clipSlots) {
    const selected = slot.keyframeVersions.find((version) => version.selected) || slot.keyframeVersions[0];
    const url = selected?.asset?.fileUrl || selected?.asset?.previewUrl || selected?.downloadUrl || selected?.previewUrl || "";
    if (url) {
      items.push({ title: selected?.title || `镜头 ${slot.clipIndex} 关键帧`, url, type: "image", kind: `镜头 ${slot.clipIndex}` });
    }
  }
  return items.slice(0, 24);
});

const previewMedia = computed(() => {
  const finalUrl = finalPreviewUrl.value;
  if (finalUrl) {
    return { url: finalUrl, title: workflow.value?.finalResult?.title || workflow.value?.title || "成片", type: "video" as const };
  }
  const firstVideo = resultItems.value.find((item) => item.type === "video");
  if (firstVideo) return firstVideo;
  return resultItems.value.find((item) => item.type === "image") || null;
});

const previewFileUrl = computed(() => previewMedia.value?.url || "");
const previewPlaceholder = computed(() => {
  const status = String(workflow.value?.status || "").toUpperCase();
  if (status === "COMPLETED") return "暂无可预览结果";
  if (status === "FAILED") return "生成失败，进入阶段工作流查看原因";
  if (String(workflow.value?.autoPilotState || "").toLowerCase() === "queued") return "排队中";
  return "生成中";
});

async function loadWorkflow() {
  if (!props.selectedWorkflowId) {
    workflow.value = null;
    return;
  }
  loading.value = true;
  try {
    workflow.value = await fetchWorkflow(props.selectedWorkflowId);
  } catch (error) {
    workflow.value = null;
    messageApi.error(error instanceof Error ? error.message : "工作流结果加载失败");
  } finally {
    loading.value = false;
  }
}

function markFinalPreviewLoading() {
  if (previewFileUrl.value) {
    finalPreviewLoadState.value = "loading";
  }
}

function markFinalPreviewReady() {
  if (previewFileUrl.value) {
    finalPreviewLoadState.value = "ready";
  }
}

function markFinalPreviewFailed() {
  if (previewFileUrl.value) {
    finalPreviewLoadState.value = "failed";
  }
}

function stageStateClass(state: WorkflowTaskStageState) {
  switch (state) {
    case "done": return "workflow-stage-row--done";
    case "active": return "workflow-stage-row--active";
    case "paused": return "workflow-stage-row--paused";
    case "failed": return "workflow-stage-row--failed";
    default: return "workflow-stage-row--pending";
  }
}

async function handleDownloadPreview() {
  const media = previewMedia.value;
  if (!media) return;
  await handleDownloadMedia(media.url, media.title, media.type);
}

async function handleDownloadMedia(url: string, title: string, mediaType: WorkflowResultMediaKind) {
  try {
    const result = await downloadMedia({ url, title, mediaType });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

watch(() => props.selectedWorkflowId, () => void loadWorkflow(), { immediate: true });

watch(previewFileUrl, (url) => {
  finalPreviewLoadState.value = url ? "loading" : "idle";
}, { immediate: true });
</script>

<style scoped>
.workflow-result-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 14px;
  overflow: auto;
}

.workflow-result-empty {
  display: grid;
  place-items: center;
  min-height: 220px;
  color: var(--text-muted);
}

.workflow-result-content {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.workflow-result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 12px 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 60%, rgba(255, 255, 255, 0));
}

.workflow-result-header h2 {
  margin: 0;
  color: var(--text-strong);
  font-size: 1.15rem;
  font-weight: 600;
}

.workflow-result-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.workflow-result-header__actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.workflow-result-stage-btn,
.workflow-result-download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: var(--glass-border);
  border-radius: 10px;
  background: var(--bg-surface);
  color: var(--text-strong);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.workflow-result-stage-btn {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.05), 0 8px 22px rgba(20, 184, 166, 0.12);
}

.workflow-result-stage-btn::before {
  content: "";
  position: absolute;
  inset: -2px;
  z-index: -1;
  background: linear-gradient(
    115deg,
    rgba(99, 102, 241, 0) 0%,
    rgba(99, 102, 241, 0.18) 18%,
    rgba(20, 184, 166, 0.42) 34%,
    rgba(245, 158, 11, 0.34) 50%,
    rgba(236, 72, 153, 0.36) 66%,
    rgba(99, 102, 241, 0.2) 82%,
    rgba(99, 102, 241, 0) 100%
  );
  background-size: 260% 100%;
  animation: workflow-result-button-shine 2.6s linear infinite;
}

.workflow-result-stage-btn > svg,
.workflow-result-stage-btn > span {
  position: relative;
  z-index: 1;
}

.workflow-result-stage-btn:hover,
.workflow-result-download:hover {
  background: var(--bg-soft);
}

.workflow-result-stage-btn:hover {
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.12), 0 10px 28px rgba(99, 102, 241, 0.2);
}

@keyframes workflow-result-button-shine {
  from {
    background-position: 160% 0;
  }
  to {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workflow-result-stage-btn::before {
    animation: none;
    background-position: 50% 0;
  }
}

.detail-section-card {
  padding: 14px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
}

.workflow-stage-card {
  padding: 12px;
  border: var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.64);
  box-shadow: var(--shadow-soft);
}

.workflow-stage-line {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.workflow-stage-line__item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgba(80, 90, 110, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.54);
}

.workflow-stage-line__item-done {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.16);
}

.workflow-stage-line__item-active,
.workflow-stage-line__item-paused {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.28);
}

.workflow-stage-line__item-failed {
  background: rgba(229, 72, 101, 0.08);
  border-color: rgba(229, 72, 101, 0.22);
}

.workflow-stage-line__dot {
  position: relative;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--text-muted);
}

.workflow-stage-line__dot.workflow-stage-row--done,
.workflow-stage-line__dot.workflow-stage-row--active {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
}

.workflow-stage-line__dot.workflow-stage-row--active {
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  animation: workflow-stage-dot-breathe 1.8s ease-in-out infinite;
}

.workflow-stage-line__dot.workflow-stage-row--active::before {
  content: "";
  position: absolute;
  inset: -7px;
  border-radius: inherit;
  background: rgba(99, 102, 241, 0.2);
  opacity: 0;
  animation: workflow-stage-dot-pulse 1.8s ease-out infinite;
  pointer-events: none;
}

.workflow-stage-line__dot.workflow-stage-row--paused {
  background: var(--accent-warning);
  border-color: var(--accent-warning);
}

.workflow-stage-line__dot.workflow-stage-row--failed {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
}

.workflow-stage-line__copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.workflow-stage-line__copy strong {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-stage-line__copy small {
  font-size: 0.68rem;
  color: var(--text-muted);
}

@keyframes workflow-stage-dot-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.12); }
}

@keyframes workflow-stage-dot-pulse {
  0% {
    opacity: 0.55;
    transform: scale(0.45);
  }
  70%, 100% {
    opacity: 0;
    transform: scale(1);
  }
}

.workflow-result-grid {
  display: grid;
  gap: 16px;
}

.workflow-result-grid-primary {
  grid-template-columns: minmax(360px, 1.25fr) minmax(280px, 0.75fr);
  align-items: stretch;
}

.workflow-result-preview {
  display: grid;
  gap: 12px;
}

.workflow-result-preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.workflow-result-preview__head h3,
.workflow-result-summary h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 0.9rem;
  font-weight: 700;
}

.workflow-result-media {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: #111827;
}

.workflow-result-video {
  width: 100%;
  max-height: min(58vh, 520px);
  background: #111827;
}

.workflow-result-media__loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  min-height: 220px;
  padding: 18px;
  background: rgba(15, 23, 42, 0.68);
  color: #fff;
  text-align: center;
  backdrop-filter: blur(8px);
}

.workflow-result-media__loading span {
  font-size: 0.82rem;
  font-weight: 700;
}

.workflow-result-media__loading-error {
  color: #fecaca;
}

.workflow-result-placeholder {
  display: grid;
  place-items: center;
  min-height: 220px;
  border-radius: 10px;
  background: var(--bg-softer);
  color: var(--text-muted);
}

.workflow-result-image-button {
  overflow: hidden;
  min-height: 220px;
  border: 0;
  border-radius: 10px;
  background: var(--bg-softer);
  cursor: pointer;
}

.workflow-result-image-button img {
  display: block;
  width: 100%;
  max-height: min(58vh, 520px);
  object-fit: contain;
}

.workflow-result-summary {
  display: grid;
  gap: 10px;
}

.workflow-param-tags {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
}

.workflow-param-tag {
  display: grid;
  align-content: center;
  gap: 5px;
  min-height: 64px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgba(80, 90, 110, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.58);
}

.workflow-param-tag-progress {
  grid-column: 1 / -1;
}

.workflow-param-tag__label {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.workflow-param-tag__value {
  overflow: hidden;
  color: var(--text-strong);
  font-size: 0.86rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-param-tag__progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workflow-progress {
  flex: 1;
  height: 7px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--bg-softer);
}

.workflow-progress__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-indigo), #14b8a6);
  transition: width 220ms ease;
}

.workflow-note-block {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.06);
}

.workflow-note-block span {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-muted);
}

.workflow-note-block p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--text-body);
  font-size: 0.82rem;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.workflow-result-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.workflow-result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 56px;
  padding: 10px 12px;
  border: 1px solid rgba(80, 90, 110, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.58);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.workflow-result-item:hover {
  background: var(--bg-soft);
}

.workflow-result-item__icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
  color: var(--accent-indigo);
}

.workflow-result-item__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.workflow-result-item__copy strong {
  overflow: hidden;
  color: var(--text-strong);
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-result-item__copy small {
  color: var(--text-muted);
  font-size: 0.72rem;
}

@media (max-width: 640px) {
  .workflow-result-header {
    flex-direction: column;
  }

  .workflow-result-stage-btn {
    width: 100%;
  }

  .workflow-result-header__actions {
    width: 100%;
  }

  .workflow-result-download {
    flex: 1;
  }

  .workflow-result-grid-primary {
    grid-template-columns: 1fr;
  }
}
</style>

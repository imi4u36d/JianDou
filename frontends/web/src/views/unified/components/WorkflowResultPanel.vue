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
            <button
              v-if="shareableFinalResult"
              class="workflow-result-download"
              type="button"
              :disabled="sharingFinalResult"
              @click="openWorkflowShareConfirm"
            >
              <IconShare size="xs" />
              {{ workflowShareId ? "已分享" : "分享" }}
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

      <section class="detail-section-card detail-trace-section" :class="{ 'detail-trace-section-open': workflowTraceOpen }">
        <button
          type="button"
          class="detail-trace-summary"
          :aria-expanded="workflowTraceOpen"
          aria-controls="workflow-result-traces"
          @click="workflowTraceOpen = !workflowTraceOpen"
        >
          <span class="detail-trace-summary__copy">
            <strong>追踪</strong>
            <small>{{ workflowTraceItems[0]?.message || "暂无记录" }}</small>
          </span>
          <span class="surface-chip">{{ workflowTraceItems.length }} 条</span>
          <span class="detail-trace-summary__chevron" aria-hidden="true">
            <IconChevronDown size="xs" />
          </span>
        </button>
        <div v-if="workflowTraceOpen" id="workflow-result-traces" class="detail-traces">
          <div v-if="workflowTraceItems.length === 0" class="detail-traces__empty">暂无记录</div>
          <div v-for="event in workflowTraceItems" :key="`${event.timestamp}-${event.event}-${event.stage}-${event.message}`" class="detail-traces__item">
            <div class="detail-traces__body">
              <p>{{ event.message }}</p>
              <small>
                <span class="detail-traces__stage">{{ formatWorkflowTraceStage(event.stage) }}</span>
                <span class="detail-traces__event">{{ formatWorkflowTraceEvent(event.event) }}</span>
              </small>
            </div>
            <time class="detail-traces__time" :datetime="event.timestamp || undefined">{{ formatDateTime(event.timestamp) }}</time>
          </div>
        </div>
      </section>
    </section>
    <AppConfirmDialog v-bind="shareConfirmDialog" @confirm="acceptWorkflowShareConfirm" @cancel="cancelWorkflowShareConfirm" />
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fetchWorkflow } from "@/features/workflows";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import { IconChevronDown, IconDownload, IconImage, IconLoading, IconRefresh, IconShare, IconVideo, IconWorkflow } from "@/components/icons";
import { createPublicShare, deletePublicShare } from "@/api/public-shares";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";
import type { StageVersion, WorkflowDetail } from "@/types";

const props = defineProps<{
  selectedWorkflowId: string;
}>();

defineEmits<{
  openStage: [];
}>();

const workflow = ref<WorkflowDetail | null>(null);
const loading = ref(false);
const sharingFinalResult = ref(false);
const workflowShareId = ref("");
const workflowTraceOpen = ref(false);
const shareConfirmDialog = ref({
  open: false,
  title: "分享生成结果",
  message: "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
  confirmText: "确认分享",
  cancelText: "取消",
  tone: "primary" as "primary" | "danger",
});

const finalPreviewUrl = computed(() => materialPublicUrl(workflow.value?.finalResult));
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
type WorkflowTraceItem = {
  timestamp: string;
  stage: string;
  event: string;
  message: string;
};

const stageStateLabels: Record<WorkflowTaskStageState, string> = {
  pending: "等待",
  active: "进行中",
  paused: "已暂停",
  done: "已完成",
  failed: "失败",
};

function materialPublicUrl(asset?: { publicUrl?: string | null; fileUrl?: string | null } | null) {
  return asset?.publicUrl || asset?.fileUrl || "";
}

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
  const finalUrl = materialPublicUrl(finalResult);
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
      const url = materialPublicUrl(version.asset) || version.downloadUrl || version.previewUrl || "";
      if (url) {
        items.push({ title: version.title || `镜头 ${slot.clipIndex} 视频`, url, type: "video", kind: `镜头 ${slot.clipIndex}` });
      }
    }
  }
  for (const slot of current.clipSlots) {
    const selected = slot.keyframeVersions.find((version) => version.selected) || slot.keyframeVersions[0];
    const url = materialPublicUrl(selected?.asset) || selected?.downloadUrl || selected?.previewUrl || "";
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
const finalMaterialAssetId = computed(() => workflow.value?.finalResult?.id || "");
const shareableFinalResult = computed(() => Boolean(finalMaterialAssetId.value && materialPublicUrl(workflow.value?.finalResult)));
const previewPlaceholder = computed(() => {
  const status = String(workflow.value?.status || "").toUpperCase();
  if (status === "COMPLETED") return "暂无可预览结果";
  if (status === "FAILED") return "生成失败，进入阶段工作流查看原因";
  if (String(workflow.value?.autoPilotState || "").toLowerCase() === "queued") return "排队中";
  return "生成中";
});

const workflowTraceItems = computed<WorkflowTraceItem[]>(() => {
  const current = workflow.value;
  if (!current) return [];
  const items: WorkflowTraceItem[] = [];
  const push = (item: WorkflowTraceItem) => {
    if (!item.message.trim()) return;
    items.push(item);
  };

  push({
    timestamp: current.updatedAt || current.createdAt || "",
    stage: current.currentStage || "workflow",
    event: `workflow.${String(current.status || "updated").toLowerCase()}`,
    message: workflowStateMessage(current),
  });

  const autoPilotState = String(current.autoPilotState || "").toLowerCase();
  if (autoPilotState) {
    push({
      timestamp: current.updatedAt || current.autoPilotStartedAt || current.createdAt || "",
      stage: "auto_pilot",
      event: `auto_pilot.${autoPilotState}`,
      message: current.autoPilotErrorMessage || current.autoPilotCurrentTask || autoPilotStateMessage(autoPilotState),
    });
  }

  for (const version of workflowStageVersions(current)) {
    push({
      timestamp: version.updatedAt || version.createdAt || "",
      stage: version.stageType || "workflow",
      event: `stage.${String(version.status || "updated").toLowerCase()}`,
      message: stageVersionTraceMessage(version),
    });
  }

  return items
    .sort((a, b) => timestampValue(b.timestamp) - timestampValue(a.timestamp))
    .slice(0, 24);
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

function workflowStageVersions(current: WorkflowDetail) {
  const versions: StageVersion[] = [...current.storyboardVersions];
  for (const sheet of current.characterSheets ?? []) {
    versions.push(...(sheet.versions ?? sheet.keyframeVersions ?? []));
  }
  for (const slot of current.clipSlots) {
    versions.push(...slot.keyframeVersions, ...slot.videoVersions);
  }
  return versions;
}

function workflowStateMessage(current: WorkflowDetail) {
  const status = String(current.status || "").toUpperCase();
  if (status === "FAILED") return current.autoPilotErrorMessage || "工作流生成失败";
  if (status === "COMPLETED") return "工作流已完成";
  if (String(current.autoPilotState || "").toLowerCase() === "queued") return "工作流已加入自动生成队列";
  return current.autoPilotCurrentTask || "工作流状态已更新";
}

function autoPilotStateMessage(state: string) {
  if (state === "queued") return "自动生成排队中";
  if (state === "running") return "自动生成执行中";
  if (state === "paused") return "自动生成已暂停";
  if (state === "failed") return "自动生成失败";
  if (state === "completed") return "自动生成已完成";
  return "自动生成状态已更新";
}

function stageVersionTraceMessage(version: StageVersion) {
  const status = String(version.status || "").toUpperCase();
  const error = stageVersionErrorMessage(version);
  if (error) return error;
  const label = formatWorkflowTraceStage(version.stageType);
  const suffix = version.clipIndex > 0 && version.clipIndex < 1000 ? ` ${version.clipIndex}` : "";
  if (status === "FAILED") return `${label}${suffix}生成失败`;
  if (status === "COMPLETED" || version.asset || version.selected) return `${label}${suffix}已完成`;
  if (status === "RUNNING" || status === "PROCESSING") return `${label}${suffix}生成中`;
  return `${label}${suffix}已更新`;
}

function stageVersionErrorMessage(version: StageVersion) {
  const output = version.outputSummary ?? {};
  const frameFailure = Array.isArray(output.frameFailures)
    ? output.frameFailures.find((item) => item?.errorMessage)
    : null;
  return stringValue(output.error)
    || stringValue(output.taskMessage)
    || stringValue(frameFailure?.errorMessage)
    || "";
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function timestampValue(value: string) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDateTime(timestamp: string) {
  if (!timestamp) return "刚刚";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleString();
}

function formatWorkflowTraceStage(stage: string) {
  const normalized = String(stage || "").toLowerCase();
  const labels: Record<string, string> = {
    workflow: "工作流",
    auto_pilot: "自动生成",
    storyboard: "分镜",
    keyframe: "关键帧",
    video: "视频",
    joined: "拼接",
  };
  return labels[normalized] ?? (stage || "系统");
}

function formatWorkflowTraceEvent(event: string) {
  const normalized = String(event || "").toLowerCase();
  const labels: Record<string, string> = {
    "workflow.ready": "状态更新",
    "workflow.running": "生成中",
    "workflow.failed": "失败",
    "workflow.completed": "完成",
    "auto_pilot.queued": "排队",
    "auto_pilot.running": "执行中",
    "auto_pilot.paused": "暂停",
    "auto_pilot.failed": "失败",
    "auto_pilot.completed": "完成",
    "stage.completed": "阶段完成",
    "stage.failed": "阶段失败",
    "stage.running": "阶段执行",
    "stage.processing": "阶段执行",
  };
  return labels[normalized] ?? (event || "事件");
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

function openWorkflowShareConfirm() {
  const shared = Boolean(workflowShareId.value);
  shareConfirmDialog.value = {
    open: true,
    title: shared ? "取消分享" : "分享生成结果",
    message: shared
      ? "取消分享后，这个生成结果将不再展示在首页分享区。"
      : "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
    confirmText: shared ? "取消分享" : "确认分享",
    cancelText: "取消",
    tone: shared ? "danger" : "primary",
  };
}

function cancelWorkflowShareConfirm() {
  shareConfirmDialog.value = { ...shareConfirmDialog.value, open: false };
}

async function acceptWorkflowShareConfirm() {
  const materialAssetId = finalMaterialAssetId.value;
  if (!materialAssetId || sharingFinalResult.value) return;
  sharingFinalResult.value = true;
  try {
    if (workflowShareId.value) {
      await deletePublicShare(workflowShareId.value);
      workflowShareId.value = "";
      messageApi.success("已取消分享");
    } else {
      const share = await createPublicShare({
        materialAssetId,
        sourceType: "workflow",
        sourceId: props.selectedWorkflowId,
      });
      workflowShareId.value = share.shareId;
      messageApi.success("已分享到首页");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "分享失败");
  } finally {
    sharingFinalResult.value = false;
    cancelWorkflowShareConfirm();
  }
}

watch(() => props.selectedWorkflowId, () => void loadWorkflow(), { immediate: true });

watch(workflow, (current) => {
  const status = String(current?.status || "").toUpperCase();
  const autoPilotState = String(current?.autoPilotState || "").toLowerCase();
  workflowTraceOpen.value = status === "FAILED" || autoPilotState === "failed";
}, { immediate: true });

watch(finalMaterialAssetId, () => {
  workflowShareId.value = "";
});

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

.detail-trace-section {
  gap: 0;
  padding: 0;
  overflow: hidden;
}

.detail-trace-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  padding: 14px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.detail-trace-summary:hover {
  background: rgba(99, 102, 241, 0.045);
}

.detail-trace-summary__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.detail-trace-summary__copy strong {
  font-size: 0.88rem;
  font-weight: 650;
  color: var(--text-strong);
}

.detail-trace-summary__copy small {
  min-width: 0;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.76rem;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-trace-summary__chevron {
  display: grid;
  place-items: center;
  color: var(--text-muted);
  transition: transform 0.18s ease;
}

.detail-trace-section-open .detail-trace-summary__chevron {
  transform: rotate(180deg);
}

.detail-traces {
  display: grid;
  max-height: 360px;
  padding: 4px 16px 14px;
  border-top: 1px solid rgba(80, 90, 110, 0.08);
  overflow: auto;
}

.detail-traces__empty {
  padding: 16px;
  color: var(--text-muted);
  font-size: 0.82rem;
  text-align: center;
}

.detail-traces__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: 14px;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid rgba(80, 90, 110, 0.08);
}

.detail-traces__item:last-child {
  border-bottom: 0;
}

.detail-traces__body {
  min-width: 0;
}

.detail-traces__item p {
  margin: 0;
  color: var(--text-body);
  font-size: 0.82rem;
  line-height: 1.5;
  word-break: break-word;
}

.detail-traces__item small {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 0.7rem;
}

.detail-traces__stage {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-softer);
  font-size: 0.68rem;
  font-weight: 600;
}

.detail-traces__event {
  color: var(--text-body);
}

.detail-traces__time {
  padding-top: 1px;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.72rem;
  line-height: 1.5;
  white-space: nowrap;
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

  .detail-trace-summary {
    align-items: flex-start;
  }

  .detail-traces__item {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .detail-traces__time {
    white-space: normal;
  }
}
</style>

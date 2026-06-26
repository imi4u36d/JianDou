<template>
  <main class="workflow-result-panel">
    <section v-if="loading" class="workflow-result-empty">加载中</section>
    <section v-else-if="!workflow" class="workflow-result-empty">结果不存在</section>
    <section v-else class="workflow-result-content" aria-labelledby="workflow-result-title">
      <header class="workflow-result-header">
        <div>
          <h2 id="workflow-result-title">{{ workflow.title || "任务结果" }}</h2>
          <div class="workflow-result-header__meta">
            <span class="surface-chip">阶段任务</span>
            <span class="surface-chip">{{ statusLabel }}</span>
            <span class="surface-chip">{{ workflow.aspectRatio || "未设置画幅" }}</span>
          </div>
        </div>
        <button class="workflow-result-stage-btn" type="button" @click="$emit('openStage')">
          <IconWorkflow size="xs" />
          阶段工作流
        </button>
      </header>

      <section class="workflow-result-preview detail-section-card">
        <div class="workflow-result-preview__head">
          <h3>结果预览</h3>
          <button
            v-if="finalFileUrl"
            class="workflow-result-download"
            type="button"
            @click="handleDownloadFinal"
          >
            <IconDownload size="xs" />
            下载
          </button>
        </div>
        <div v-if="finalPreviewUrl" class="workflow-result-media">
          <video
            class="workflow-result-video"
            :src="finalPreviewUrl"
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
        <div v-else class="workflow-result-placeholder">暂无可预览结果</div>
      </section>

      <section class="workflow-result-summary detail-section-card">
        <h3>生成摘要</h3>
        <div class="workflow-result-rows">
          <div class="workflow-result-row"><span>分镜版本</span><strong>{{ workflow.storyboardVersions.length }}</strong></div>
          <div class="workflow-result-row"><span>角色三视图</span><strong>{{ workflow.characterSheets?.length ?? 0 }}</strong></div>
          <div class="workflow-result-row"><span>镜头数量</span><strong>{{ workflow.clipSlots.length }}</strong></div>
          <div class="workflow-result-row"><span>自动模式</span><strong>{{ autoPilotLabel }}</strong></div>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fetchWorkflow } from "@/features/workflows";
import { IconDownload, IconLoading, IconWorkflow } from "@/components/icons";
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
const finalFileUrl = computed(() => workflow.value?.finalResult?.fileUrl || workflow.value?.finalResult?.previewUrl || "");
const finalPreviewLoadState = ref<"idle" | "loading" | "ready" | "failed">("idle");
const finalPreviewLoading = computed(() => Boolean(finalPreviewUrl.value) && finalPreviewLoadState.value === "loading");

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
  if (finalPreviewUrl.value) {
    finalPreviewLoadState.value = "loading";
  }
}

function markFinalPreviewReady() {
  if (finalPreviewUrl.value) {
    finalPreviewLoadState.value = "ready";
  }
}

function markFinalPreviewFailed() {
  if (finalPreviewUrl.value) {
    finalPreviewLoadState.value = "failed";
  }
}

async function handleDownloadFinal() {
  try {
    const result = await downloadMedia({ url: finalFileUrl.value, title: workflow.value?.finalResult?.title || workflow.value?.title || "成片", mediaType: "video" });
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

watch(finalPreviewUrl, (url) => {
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

.workflow-result-stage-btn,
.workflow-result-download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  background: var(--bg-surface);
  color: var(--text-strong);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.workflow-result-stage-btn:hover,
.workflow-result-download:hover {
  background: var(--bg-soft);
}

.detail-section-card {
  padding: 14px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
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

.workflow-result-summary {
  display: grid;
  gap: 10px;
}

.workflow-result-rows {
  display: grid;
  gap: 8px;
}

.workflow-result-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-body);
  font-size: 0.84rem;
}

.workflow-result-row strong {
  color: var(--text-strong);
}

@media (max-width: 640px) {
  .workflow-result-header {
    flex-direction: column;
  }

  .workflow-result-stage-btn {
    width: 100%;
  }
}
</style>

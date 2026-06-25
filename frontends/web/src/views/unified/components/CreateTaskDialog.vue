<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="create-task-dialog-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-task-dialog-title"
      @click.self="requestClose"
      @keydown.esc.stop.prevent="requestClose"
    >
      <div class="create-task-dialog">
        <header class="create-task-dialog__head">
          <h2 id="create-task-dialog-title">开始新任务</h2>
        </header>
        <button type="button" class="create-task-dialog__close" aria-label="关闭" @click="requestClose">
          <IconClose size="sm" />
        </button>

        <form class="create-task-dialog__body" @submit.prevent="submitWorkflow">
          <label class="create-field">
            <span>标题</span>
            <input ref="titleInputRef" v-model="workflowTitle" required placeholder="标题" />
          </label>
          <label class="create-field">
            <span>灵感创作</span>
            <textarea v-model="workflowTranscript" rows="6" placeholder="灵感创作"></textarea>
          </label>
          <label class="create-field">
            <span>画幅</span>
            <AppSelect v-model="workflowAspectRatio" :options="aspectRatioOptions" />
          </label>

          <div class="create-task-dialog__footer">
            <span class="create-status-text" :class="{ 'create-status-text--error': isStatusError }">{{ workflowStatusText }}</span>
            <button class="btn-primary" type="submit" :disabled="submitting || !workflowTitle.trim()">
              <IconLoading v-if="submitting" size="xs" />
              <span>{{ submitting ? "创建中" : "开始" }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 创建工作流弹窗组件。
 */
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch } from "vue";
import { requireAuth } from "@/auth/modal";
import { createWorkflow, fetchGenerationOptions } from "@/features/workflows";
import { formatApiErrorMessage } from "@/utils/api-error";
import AppSelect from "@/components/common/AppSelect.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { IconClose, IconLoading } from "@/components/icons";
import type { GenerationOptionsResponse } from "@/types";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  created: [id: string];
}>();

const titleInputRef = ref<HTMLInputElement | null>(null);
let returnFocusTarget: HTMLElement | null = null;

function close() {
  emit("close");
}

function requestClose() {
  if (submitting.value) {
    return;
  }
  close();
}

function restoreFocus() {
  const target = returnFocusTarget;
  returnFocusTarget = null;
  target?.focus({ preventScroll: true });
}

// ── Shared state ──
const submitting = ref(false);
const options = ref<GenerationOptionsResponse | null>(null);

onMounted(async () => {
  try {
    options.value = await fetchGenerationOptions();
  } catch {
    // 静默处理
  }
});

watch(
  () => props.open,
  async (open) => {
    if (open) {
      returnFocusTarget = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      await nextTick();
      titleInputRef.value?.focus({ preventScroll: true });
      return;
    }
    restoreFocus();
  },
);

onBeforeUnmount(restoreFocus);

// ── Workflow form ──

const workflowTitle = ref("");
const workflowTranscript = ref("");
const workflowAspectRatio = ref("16:9");
const workflowStatusText = ref("");

const isStatusError = computed(() => workflowStatusText.value && !workflowStatusText.value.includes("成功"));

const aspectRatioOptions = computed<AppSelectOption[]>(() => {
  const ratios = options.value?.aspectRatios ?? ["16:9", "9:16"];
  return ratios.map((r: string | { value: string; label: string }) =>
    typeof r === "string" ? { label: r, value: r } : r
  );
});

async function submitWorkflow() {
  if (!workflowTitle.value.trim()) return;
  const authenticated = await requireAuth({ title: "登录后创建画布", message: "阶段工作流会保存到你的账号下，请先登录或使用邀请码注册。" });
  if (!authenticated) return;
  submitting.value = true;
  workflowStatusText.value = "";
  try {
    const workflow = await createWorkflow({
      title: workflowTitle.value.trim(),
      transcriptText: workflowTranscript.value.trim() || null,
      aspectRatio: workflowAspectRatio.value,
      textAnalysisModel: options.value?.defaultTextAnalysisModel || "",
      imageModel: options.value?.defaultImageModel || "",
      videoModel: options.value?.defaultVideoModel || "",
      videoSize: options.value?.defaultVideoSize || null,
    });
    workflowTitle.value = "";
    workflowTranscript.value = "";
    workflowStatusText.value = "创建成功";
    emit("created", workflow.id);
  } catch (error) {
    workflowStatusText.value = formatApiErrorMessage(error, "创建工作流失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.create-task-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 150;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.35);
  padding: 24px;
}

.create-task-dialog {
  position: relative;
  width: min(100%, 560px);
  max-height: 85vh;
  overflow: auto;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
  display: grid;
  gap: 0;
}

.create-task-dialog__close {
  position: absolute;
  top: 12px;
  right: 14px;
  z-index: 10;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.create-task-dialog__close:hover {
  background: var(--bg-softer);
  color: var(--text-strong);
}

.create-task-dialog__close > svg {
  width: 16px;
  height: 16px;
}

.create-task-dialog__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--bg-softer);
}

.create-task-dialog__head h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-strong);
}

.create-task-dialog__body {
  display: grid;
  gap: 14px;
  padding: 18px 20px;
}

.create-field {
  display: grid;
  gap: 6px;
}

.create-field span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.create-field textarea,
.create-field input {
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  background: var(--bg-softer);
  color: var(--text-strong);
  font-size: 0.9rem;
  resize: vertical;
  font-family: inherit;
}

.create-field textarea:focus,
.create-field input:focus {
  outline: none;
  border-color: var(--accent-indigo);
  background: #fff;
}

.create-task-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--bg-softer);
}

.create-status-text {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.create-status-text--error {
  color: var(--accent-danger);
  font-weight: 600;
}

.create-task-dialog__footer .btn-primary {
  margin-left: auto;
}

@media (max-width: 640px) {
  .create-task-dialog {
    width: 100%;
    max-height: 90vh;
  }
}
</style>

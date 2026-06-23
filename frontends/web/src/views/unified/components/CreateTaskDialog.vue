<template>
  <Teleport to="body">
    <div v-if="open" class="create-task-dialog-overlay" role="dialog" aria-modal="true" @click.self="close">
      <div class="create-task-dialog">
        <header class="create-task-dialog__head">
          <h2>新建</h2>
          <div class="create-task-dialog__modes">
            <button
              type="button"
              class="create-task-dialog__mode-btn"
              :class="{ 'create-task-dialog__mode-btn-active': dialogMode === 'task' }"
              @click="dialogMode = 'task'"
            >
              快速任务
            </button>
            <button
              type="button"
              class="create-task-dialog__mode-btn"
              :class="{ 'create-task-dialog__mode-btn-active': dialogMode === 'workflow' }"
              @click="dialogMode = 'workflow'"
            >
              阶段工作流
            </button>
          </div>
          <button type="button" class="create-task-dialog__close" aria-label="关闭" @click="close">
            <IconClose size="sm" />
          </button>
        </header>

        <!-- ── 快速任务模式 ── -->
        <form v-if="dialogMode === 'task'" class="create-task-dialog__body" @submit.prevent="submitQuickTask">
          <div class="create-field">
            <span>创作类型</span>
            <div class="create-type-chips">
              <button
                v-for="mode in taskModes"
                :key="mode.value"
                type="button"
                class="create-type-chip"
                :class="{ 'create-type-chip-active': selectedTaskMode === mode.value }"
                @click="selectedTaskMode = mode.value"
              >
                <span class="create-type-chip__icon"><IconVideo v-if="mode.value === 'video'" /><IconImage v-else-if="mode.value === 'image'" /><IconCharacter v-else /></span>
                {{ mode.label }}
              </button>
            </div>
          </div>
          <label class="create-field">
            <span>{{ selectedTaskMode === 'video' ? '正文 / 创作输入' : '提示词' }}</span>
            <textarea v-model="taskPrompt" rows="5" :placeholder="selectedTaskMode === 'video' ? '粘贴正文或输入创作想法' : '描述你想生成的内容'"></textarea>
          </label>
          <label class="create-field">
            <span>画幅</span>
            <AppSelect v-model="taskAspectRatio" :options="aspectRatioOptions" />
          </label>
          <div class="create-task-dialog__footer">
            <span class="create-status-text">{{ taskStatusText }}</span>
            <button class="btn-primary" type="submit" :disabled="submitting || !taskPrompt.trim()">
              <IconLoading v-if="submitting" size="xs" />
              <span>{{ submitting ? "创建中" : submitLabel }}</span>
            </button>
          </div>
        </form>

        <!-- ── 阶段工作流模式 ── -->
        <form v-else class="create-task-dialog__body" @submit.prevent="submitWorkflow">
          <label class="create-field">
            <span>画布标题</span>
            <input v-model="workflowTitle" required placeholder="画布标题" />
          </label>
          <label class="create-field">
            <span>正文 / 创作输入</span>
            <textarea v-model="workflowTranscript" rows="6" placeholder="粘贴正文、剧情设定或脚本"></textarea>
          </label>
          <label class="create-field">
            <span>画幅</span>
            <AppSelect v-model="workflowAspectRatio" :options="aspectRatioOptions" />
          </label>
          <div class="create-task-dialog__footer">
            <span class="create-status-text">{{ workflowStatusText }}</span>
            <button class="btn-primary" type="submit" :disabled="submitting || !workflowTitle.trim()">
              <IconLoading v-if="submitting" size="xs" />
              <span>{{ submitting ? "创建中" : "创建画布" }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 创建任务弹窗组件。
 * 支持快速任务和阶段工作流两种模式。
 */
import { ref, computed, onMounted } from "vue";
import { requireAuth } from "@/auth/modal";
import { createGenerationTask } from "@/features/home";
import { createWorkflow, fetchGenerationOptions } from "@/features/workflows";
import { formatApiErrorMessage } from "@/utils/api-error";
import AppSelect from "@/components/common/AppSelect.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { IconCharacter, IconClose, IconImage, IconLoading, IconVideo } from "@/components/icons";
import type { GenerationOptionsResponse } from "@/types";

defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  created: [id: string, kind: "task" | "workflow"];
}>();

function close() {
  emit("close");
}

// ── Shared state ──
const dialogMode = ref<"task" | "workflow">("task");
const submitting = ref(false);
const options = ref<GenerationOptionsResponse | null>(null);

onMounted(async () => {
  try {
    options.value = await fetchGenerationOptions();
  } catch {
    // 静默处理
  }
});

// ── Quick Task mode ──

const taskModes = [
  { value: "video", label: "视频" },
  { value: "image", label: "图片" },
  { value: "character_sheet", label: "角色三视图" },
] as const;

const selectedTaskMode = ref<"video" | "image" | "character_sheet">("video");
const taskPrompt = ref("");
const taskAspectRatio = ref("16:9");
const taskStatusText = ref("");

const aspectRatioOptions = computed<AppSelectOption[]>(() => {
  const ratios = options.value?.aspectRatios ?? ["16:9", "9:16"];
  return ratios.map((r: string | { value: string; label: string }) =>
    typeof r === "string" ? { label: r, value: r } : r
  );
});

const submitLabel = computed(() => {
  switch (selectedTaskMode.value) {
    case "video": return "生成视频";
    case "character_sheet": return "生成三视图";
    default: return "生成图片";
  }
});

async function submitQuickTask() {
  if (!taskPrompt.value.trim()) return;
  const authenticated = await requireAuth({ title: "登录后创建任务", message: "生成结果会保存到你的任务和素材库中，请先登录或使用邀请码注册。" });
  if (!authenticated) return;
  submitting.value = true;
  taskStatusText.value = "";
  try {
    const isCharacterSheet = selectedTaskMode.value === "character_sheet";
    const taskType = isCharacterSheet ? "character_sheet" : selectedTaskMode.value === "video" ? "video_generation" : "image_generation";
    const task = await createGenerationTask({
      title: taskPrompt.value.trim().slice(0, 32),
      taskType,
      assetType: isCharacterSheet ? "character_sheet" : undefined,
      creativePrompt: taskPrompt.value.trim(),
      aspectRatio: taskAspectRatio.value,
      textAnalysisModel: options.value?.defaultTextAnalysisModel || "",
      imageModel: options.value?.defaultImageModel || "",
      videoModel: options.value?.defaultVideoModel || "",
      videoSize: options.value?.defaultVideoSize || null,
      seed: null,
      videoDurationSeconds: null,
      outputCount: selectedTaskMode.value === "video" ? 1 : 1,
    });
    taskPrompt.value = "";
    taskStatusText.value = "创建成功";
    emit("created", task.id, "task");
  } catch (error) {
    taskStatusText.value = formatApiErrorMessage(error, "创建失败");
  } finally {
    submitting.value = false;
  }
}

// ── Workflow mode ──

const workflowTitle = ref("");
const workflowTranscript = ref("");
const workflowAspectRatio = ref("16:9");
const workflowStatusText = ref("");

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
    emit("created", workflow.id, "workflow");
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
  width: min(100%, 560px);
  max-height: 85vh;
  overflow: auto;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
  display: grid;
  gap: 0;
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

.create-task-dialog__modes {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.create-task-dialog__mode-btn {
  padding: 6px 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: transparent;
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.create-task-dialog__mode-btn:hover:not(.create-task-dialog__mode-btn-active) { background: var(--bg-softer); }
.create-task-dialog__mode-btn-active:hover { background: #5558e3; }

.create-task-dialog__mode-btn-active {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  color: white;
}

.create-task-dialog__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.create-task-dialog__close:hover { background: var(--bg-softer); }

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

.create-type-chips {
  display: flex;
  gap: 8px;
}

.create-type-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: transparent;
  color: var(--text-body);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.create-type-chip:hover:not(.create-type-chip-active) { background: var(--bg-softer); }
.create-type-chip-active:hover { background: rgba(99, 102, 241, 0.12); }

.create-type-chip-active {
  background: rgba(99, 102, 241, 0.06);
  border-color: var(--accent-indigo);
  color: var(--accent-indigo);
}

.create-type-chip__icon {
  display: grid;
  place-items: center;
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

.create-task-dialog__footer .btn-primary {
  margin-left: auto;
}

@media (max-width: 640px) {
  .create-task-dialog {
    width: 100%;
    max-height: 90vh;
  }

  .create-type-chips {
    flex-wrap: wrap;
  }
}
</style>

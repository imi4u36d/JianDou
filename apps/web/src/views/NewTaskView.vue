<template>
  <section class="new-task-view">
    <div class="new-task-layout">
      <div class="new-task-main surface-panel surface-panel-warm p-6">
        <PageHeader eyebrow="创建任务" title="文本生成 Task" description="文本驱动视频生成，统一进入 Task 链路" />
        <div class="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <HintBell title="模型参数" :items="['文本模型用于提示词理解', '视频模型决定生成质量', '分辨率与时长直接影响成本']" />
          <HintBell title="TXT 能力" text="支持上传小说 TXT，自动填充文本并辅助生成提示词。" />
        </div>

        <form class="mt-6 grid gap-5" @submit.prevent="submitTask">
          <div class="surface-tile grid gap-4 p-4 md:grid-cols-[2fr,1fr]">
            <label class="grid gap-2 text-sm text-slate-700">
              任务标题
              <input v-model="form.title" class="field-input" required placeholder="例如：都市小说第 3 章视频预告" />
            </label>
            <label class="grid gap-2 text-sm text-slate-700">
              画幅比例
              <select v-model="form.aspectRatio" class="field-select">
                <option value="9:16">竖版 9:16</option>
                <option value="16:9">横版 16:9</option>
              </select>
            </label>
          </div>

          <div class="surface-tile grid gap-4 p-4 sm:grid-cols-2">
            <label class="grid gap-2 text-sm text-slate-700">
              文本模型
              <select v-model="form.textAnalysisModel" class="field-select">
                <option v-for="item in textModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="grid gap-2 text-sm text-slate-700">
              视频模型
              <select v-model="form.videoModel" class="field-select">
                <option v-for="item in videoModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="grid gap-2 text-sm text-slate-700">
              分辨率
              <select v-model="form.videoSize" class="field-select">
                <option v-for="item in videoSizeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="grid gap-2 text-sm text-slate-700">
              视频总时长限制
              <select v-model="durationLimitMode" class="field-select">
                <option value="auto">自动</option>
                <option value="manual">手动输入最大时长</option>
              </select>
            </label>
            <label v-if="durationLimitMode === 'manual'" class="grid gap-2 text-sm text-slate-700">
              最大总时长（秒）
              <input
                v-model="manualMaxDurationSeconds"
                class="field-input"
                type="number"
                min="1"
                max="120"
                step="1"
                placeholder="请输入 1-120"
              />
            </label>
          </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-sm font-semibold text-slate-900">全局提示词</p>
              <div class="flex items-center gap-2">
                <button type="button" class="btn-primary btn-sm" :disabled="generatingPrompt" @click="handleGeneratePrompt">
                  {{ generatingPrompt ? "生成中..." : "AI 生成提示词" }}
                </button>
                <button type="button" class="btn-ghost btn-sm" @click="form.creativePrompt = ''">清空</button>
              </div>
            </div>
            <textarea
              v-model="form.creativePrompt"
              rows="6"
              class="field-textarea mt-3"
              placeholder="描述人物关系、冲突推进、镜头语气、情绪节奏；留空则使用系统默认提示词。"
            ></textarea>
            <p class="mt-2 text-xs text-slate-500">提示词来源：{{ promptSourceLabel }}</p>
          </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-sm font-semibold text-slate-900">小说 TXT 输入</p>
              <button type="button" class="btn-secondary btn-sm" :disabled="uploadingText" @click="textFileInput?.click()">
                {{ uploadingText ? "上传中..." : "上传 TXT" }}
              </button>
            </div>
            <input
              ref="textFileInput"
              type="file"
              accept=".txt,text/plain"
              class="hidden"
              @change="handleTextFileChange"
            />
            <p class="mt-2 text-xs text-slate-500">{{ uploadedTextLabel }}</p>
            <textarea
              v-model="form.transcriptText"
              rows="8"
              class="field-textarea mt-3 font-mono text-sm"
              placeholder="可直接粘贴小说正文或上传 TXT 后自动填充。"
            ></textarea>
          </div>

          <div class="submit-row">
            <div class="submit-actions">
              <button class="btn-primary" type="submit" :disabled="submitting || !isFormReady">{{ submitLabel }}</button>
              <button class="btn-secondary" type="button" :disabled="submitting" @click="goToTasks">查看任务列表</button>
              <button class="btn-ghost" type="button" :disabled="!progressTaskId" @click="goToCurrentTask">查看当前任务</button>
            </div>
            <p class="submit-status">{{ statusText }}</p>
          </div>
        </form>
      </div>

      <aside class="new-task-side">
        <TaskProgressCard
          :state="progressState"
          :task-id="progressTaskId"
          :trace-count="progressTraceCount"
          :elapsed-label="progressElapsedLabel"
          :result-title="previewResultTitle"
          :result-meta="previewResultMeta"
          :output-url="previewOutputUrl"
          :poster-url="previewPosterUrl"
        />

        <section class="surface-panel p-5">
          <div class="panel-head">
            <p class="panel-eyebrow">Runtime Snapshot</p>
            <h3>当前任务摘要</h3>
          </div>
          <div class="summary-grid">
            <div v-for="item in summaryRows" :key="item.label" class="summary-item">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <section class="surface-panel p-5">
          <div class="panel-head">
            <p class="panel-eyebrow">Trace Feed</p>
            <h3>最近追踪</h3>
          </div>
          <ul v-if="recentTraceEvents.length" class="trace-list">
            <li v-for="(item, index) in recentTraceEvents" :key="`${item.timestamp}-${item.event}-${index}`" class="trace-item">
              <p class="trace-main">
                <span class="trace-stage">{{ item.stage }}</span>
                <span>{{ item.message }}</span>
              </p>
              <p class="trace-meta">{{ formatTraceTime(item.timestamp) }} · {{ item.level }}</p>
            </li>
          </ul>
          <p v-else class="trace-empty">创建任务后会在这里显示实时追踪事件。</p>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchGenerationOptions } from "@/api/generation";
import { createGenerationTask, generateCreativePrompt, uploadText } from "@/api/tasks";
import TaskProgressCard from "@/components/generate/TaskProgressCard.vue";
import { useTaskProgress } from "@/components/generate/useTaskProgress";
import HintBell from "@/components/HintBell.vue";
import PageHeader from "@/components/PageHeader.vue";
import { shouldStopBeforeVideoGeneration } from "@/workbench/developer-settings";
import type {
  CreateGenerationTaskRequest,
  GenerationOptionsResponse,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
  UploadResponse,
} from "@/types";

const router = useRouter();

const options = ref<GenerationOptionsResponse | null>(null);
const loadingOptions = ref(false);
const submitting = ref(false);
const generatingPrompt = ref(false);
const uploadingText = ref(false);
const promptSource = ref("手动输入");
const statusText = ref("等待填写参数");
const uploadedText = ref<UploadResponse | null>(null);
const textFileInput = ref<HTMLInputElement | null>(null);
const durationLimitMode = ref<"auto" | "manual">("auto");
const manualMaxDurationSeconds = ref("");
const nowMs = ref(Date.now());
const localTaskStartedAtMs = ref<number | null>(null);
const localTaskEndedAtMs = ref<number | null>(null);
let nowTicker: number | null = null;

const {
  state: progressState,
  taskId: progressTaskId,
  taskDetail: progressTaskDetail,
  traceEvents,
  start: startProgress,
  attachTask,
  fail: failProgress,
} = useTaskProgress();

const form = ref<CreateGenerationTaskRequest>({
  title: "文本生成任务",
  creativePrompt: "",
  aspectRatio: "9:16",
  textAnalysisModel: null,
  videoModel: null,
  videoSize: null,
  videoDurationSeconds: null,
  transcriptText: "",
});

function normalizeModelName(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s._-]/g, "");
}

function isPreferredTextModel(value: string | null | undefined): boolean {
  return normalizeModelName(value).includes("qwen36");
}

function isPreferredVideoModel(value: string | null | undefined): boolean {
  const normalized = normalizeModelName(value);
  return normalized.includes("seeddance") || normalized.includes("seedance");
}

function parseDurationSeconds(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  const raw = String(value).trim();
  if (!raw) {
    return null;
  }
  const numeric = Number(raw);
  if (!Number.isFinite(numeric) || !Number.isInteger(numeric)) {
    return null;
  }
  const seconds = Math.trunc(numeric);
  if (seconds < 1 || seconds > 120) {
    return null;
  }
  return seconds;
}

function formatDurationSelection(): string {
  if (durationLimitMode.value === "auto") {
    return "自动";
  }
  const manualMax = parseDurationSeconds(manualMaxDurationSeconds.value);
  if (manualMax !== null) {
    return `手动上限 ${manualMax}s`;
  }
  return "手动（未填写）";
}

function resolvePromptDurationSeconds(): number {
  const manualMax = parseDurationSeconds(manualMaxDurationSeconds.value);
  if (durationLimitMode.value === "manual" && manualMax !== null) {
    return manualMax;
  }
  const defaultDuration = options.value?.defaultVideoDurationSeconds;
  if (typeof defaultDuration === "number" && Number.isFinite(defaultDuration) && defaultDuration > 0) {
    return Math.trunc(defaultDuration);
  }
  const firstOption = durationOptions.value.find((item) => Number.isFinite(item.value) && item.value > 0);
  if (firstOption) {
    return Math.trunc(firstOption.value);
  }
  return 5;
}

function pickModelDefault(
  modelOptions: Array<{ value: string; label?: string }>,
  preferredMatcher: (value: string | null | undefined) => boolean,
  backendDefault?: string | null,
): string | null {
  const preferred = modelOptions.find((item) => preferredMatcher(item.value) || preferredMatcher(item.label));
  if (preferred) {
    return preferred.value;
  }
  const normalizedBackendDefault = normalizeModelName(backendDefault);
  if (normalizedBackendDefault) {
    const matchedDefault = modelOptions.find((item) => normalizeModelName(item.value) === normalizedBackendDefault);
    if (matchedDefault) {
      return matchedDefault.value;
    }
  }
  return modelOptions[0]?.value ?? null;
}

function resolveVideoSize(size: GenerationVideoSizeOption): { width: number; height: number } | null {
  if (typeof size.width === "number" && typeof size.height === "number" && size.width > 0 && size.height > 0) {
    return {
      width: size.width,
      height: size.height,
    };
  }
  const matched = String(size.value ?? "")
    .trim()
    .match(/^(\d+)\s*[xX*]\s*(\d+)$/);
  if (!matched) {
    return null;
  }
  const width = Number(matched[1]);
  const height = Number(matched[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return null;
  }
  return {
    width: Math.trunc(width),
    height: Math.trunc(height),
  };
}

function resolveAspectRatio(size: GenerationVideoSizeOption): "9:16" | "16:9" | null {
  const parsed = resolveVideoSize(size);
  if (!parsed) {
    return null;
  }
  return parsed.width >= parsed.height ? "16:9" : "9:16";
}

function compareVideoSizeByArea(a: GenerationVideoSizeOption, b: GenerationVideoSizeOption): number {
  const aSize = resolveVideoSize(a);
  const bSize = resolveVideoSize(b);
  if (aSize && bSize) {
    const aArea = aSize.width * aSize.height;
    const bArea = bSize.width * bSize.height;
    if (aArea !== bArea) {
      return aArea - bArea;
    }
    if (aSize.width !== bSize.width) {
      return aSize.width - bSize.width;
    }
    if (aSize.height !== bSize.height) {
      return aSize.height - bSize.height;
    }
  } else if (aSize) {
    return -1;
  } else if (bSize) {
    return 1;
  }
  return String(a.label || a.value).localeCompare(String(b.label || b.value), "zh-CN");
}

const textModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.textAnalysisModels ?? []);
const videoModelOptions = computed<GenerationVideoModelInfo[]>(() => options.value?.videoModels ?? []);
const videoSizeOptions = computed<GenerationVideoSizeOption[]>(() => {
  const source = options.value?.videoSizes ?? [];
  const targetAspectRatio = form.value.aspectRatio;
  const selectedVideoModel = normalizeModelName(form.value.videoModel);
  const filtered = source
    .filter((item) => {
      const ratio = resolveAspectRatio(item);
      return !ratio || ratio === targetAspectRatio;
    })
    .filter((item) => {
      if (!selectedVideoModel) {
        return true;
      }
      const supportedModels = Array.isArray(item.supportedModels) ? item.supportedModels : [];
      if (!supportedModels.length) {
        return true;
      }
      return supportedModels.some((model) => normalizeModelName(model) === selectedVideoModel);
    });
  return [...filtered].sort(compareVideoSizeByArea);
});
const durationOptions = computed<GenerationVideoDurationOption[]>(() => {
  const source = options.value?.videoDurations ?? [];
  const selectedVideoModel = normalizeModelName(form.value.videoModel);
  const filtered = source.filter((item) => {
    if (!selectedVideoModel) {
      return true;
    }
    const supportedModels = Array.isArray(item.supportedModels) ? item.supportedModels : [];
    if (!supportedModels.length) {
      return true;
    }
    return supportedModels.some((model) => normalizeModelName(model) === selectedVideoModel);
  });
  return [...filtered].sort((a, b) => a.value - b.value);
});
const minimumSupportedDurationSeconds = computed(() => {
  const first = durationOptions.value.find((item) => Number.isFinite(item.value) && item.value > 0);
  return first ? Math.trunc(first.value) : null;
});
const normalizedManualMaxDurationSeconds = computed(() => parseDurationSeconds(manualMaxDurationSeconds.value));
const isDurationLimitValid = computed(() => {
  if (durationLimitMode.value === "auto") {
    return true;
  }
  return normalizedManualMaxDurationSeconds.value !== null;
});
const promptSourceLabel = computed(() => {
  return form.value.creativePrompt?.trim() ? promptSource.value : "系统默认";
});

function parseTimestampMs(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function formatElapsedLabel(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainingSeconds = safeSeconds % 60;
  if (hours > 0) {
    return `${hours}时 ${minutes}分 ${remainingSeconds}秒`;
  }
  if (minutes > 0) {
    return `${minutes}分 ${remainingSeconds}秒`;
  }
  return `${remainingSeconds}秒`;
}

const progressElapsedLabel = computed(() => {
  const now = nowMs.value;
  const task = progressTaskDetail.value;
  const startedAtMs =
    parseTimestampMs(task?.startedAt ?? null) ?? parseTimestampMs(task?.createdAt ?? null) ?? localTaskStartedAtMs.value;
  if (startedAtMs === null) {
    return "";
  }
  const finishedAtMs = parseTimestampMs(task?.finishedAt ?? null) ?? localTaskEndedAtMs.value;
  const endAtMs = finishedAtMs ?? now;
  const elapsedSeconds = Math.max(0, Math.floor((endAtMs - startedAtMs) / 1000));
  return `已耗时：${formatElapsedLabel(elapsedSeconds)}`;
});

const isFormReady = computed(() => {
  return Boolean(form.value.title.trim() && isDurationLimitValid.value);
});

const submitLabel = computed(() => {
  if (submitting.value) {
    return "创建中...";
  }
  return isFormReady.value ? "生成视频" : "请先补全任务参数";
});

const uploadedTextLabel = computed(() => {
  if (!uploadedText.value) {
    return "未上传 TXT 文件";
  }
  const sizeKb = (uploadedText.value.sizeBytes / 1024).toFixed(1);
  return `已上传：${uploadedText.value.fileName}（${sizeKb} KB）`;
});

const progressTraceCount = computed(() => traceEvents.value.length);

const recentTraceEvents = computed(() => {
  return [...traceEvents.value].slice(-6).reverse();
});

const previewOutputUrl = computed(() => {
  const firstOutput = progressTaskDetail.value?.outputs?.[0];
  if (!firstOutput) {
    return "";
  }
  return firstOutput.previewUrl || firstOutput.downloadUrl || "";
});

const previewPosterUrl = computed(() => "");

const previewResultTitle = computed(() => {
  if (!progressTaskDetail.value) {
    return "生成结果";
  }
  return progressTaskDetail.value.status === "COMPLETED" ? "生成成片预览" : "生成结果";
});

const previewResultMeta = computed(() => {
  const task = progressTaskDetail.value;
  if (!task) {
    return [];
  }
  const progress = `${Math.max(0, Math.min(100, Math.round(task.progress ?? 0)))}%`;
  const durationLabel =
    typeof task.minDurationSeconds === "number" && typeof task.maxDurationSeconds === "number"
      ? `${task.minDurationSeconds}-${task.maxDurationSeconds}s`
      : "";
  return [
    task.status,
    `进度 ${progress}`,
    task.aspectRatio ? `画幅 ${task.aspectRatio}` : "",
    durationLabel,
    task.outputs?.length ? `输出 ${task.outputs.length} 条` : "",
  ].filter(Boolean);
});

const summaryRows = computed(() => {
  const task = progressTaskDetail.value;
  const progressValue = task ? Math.round(task.progress ?? 0) : progressState.value.progress;
  const modelSummary = loadingOptions.value
    ? "加载中"
    : `${form.value.textAnalysisModel || "未选择"} / ${form.value.videoModel || "未选择"}`;
  return [
    { label: "任务 ID", value: progressTaskId.value || "未创建" },
    { label: "当前状态", value: task?.status || (submitting.value ? "CREATING" : progressState.value.stage) },
    { label: "当前进度", value: `${Math.max(0, Math.min(100, progressValue))}%` },
    { label: "模型配置", value: modelSummary },
    { label: "分辨率", value: form.value.videoSize || "未选择" },
    { label: "视频时长", value: formatDurationSelection() },
    { label: "已生成结果", value: task?.outputs?.length ? `${task.outputs.length} 条` : "暂无" },
  ];
});

watch(
  () => progressState.value.status,
  (status) => {
    if (status === "running") {
      if (localTaskStartedAtMs.value === null) {
        localTaskStartedAtMs.value = Date.now();
      }
      localTaskEndedAtMs.value = null;
      return;
    }
    if (status === "completed" || status === "failed" || status === "paused") {
      if (localTaskEndedAtMs.value === null) {
        localTaskEndedAtMs.value = Date.now();
      }
      return;
    }
    if (status === "idle") {
      localTaskStartedAtMs.value = null;
      localTaskEndedAtMs.value = null;
    }
  },
  { immediate: true },
);

function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error ?? new Error("读取 TXT 失败"));
    reader.readAsText(file, "utf-8");
  });
}

async function loadOptions() {
  loadingOptions.value = true;
  try {
    const result = await fetchGenerationOptions();
    options.value = result;
    form.value.textAnalysisModel = pickModelDefault(
      result.textAnalysisModels ?? [],
      isPreferredTextModel,
      result.defaultTextAnalysisModel ?? null,
    );
    form.value.videoModel = pickModelDefault(
      result.videoModels ?? [],
      isPreferredVideoModel,
      result.defaultVideoModel ?? null,
    );
    form.value.videoDurationSeconds = "auto";
    if (!manualMaxDurationSeconds.value.trim()) {
      const fallbackDuration =
        parseDurationSeconds(result.defaultVideoDurationSeconds) ?? parseDurationSeconds(result.videoDurations[0]?.value);
      if (fallbackDuration !== null) {
        manualMaxDurationSeconds.value = String(fallbackDuration);
      }
    }
    statusText.value = "参数已加载，可创建任务";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "加载模型配置失败";
  } finally {
    loadingOptions.value = false;
  }
}

watch(
  videoSizeOptions,
  (items) => {
    if (!items.length) {
      form.value.videoSize = null;
      return;
    }
    if (form.value.videoSize && items.some((item) => item.value === form.value.videoSize)) {
      return;
    }
    form.value.videoSize = items[0].value;
  },
  { immediate: true },
);

async function handleTextFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  uploadingText.value = true;
  statusText.value = "正在上传 TXT...";
  try {
    const [uploaded, content] = await Promise.all([uploadText(file), readTextFile(file)]);
    uploadedText.value = uploaded;
    if (content.trim()) {
      form.value.transcriptText = content;
      if (!form.value.title.trim() || form.value.title === "文本生成任务") {
        form.value.title = file.name.replace(/\.txt$/i, "") || "文本生成任务";
      }
    }
    statusText.value = "TXT 已上传并填充文本";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "TXT 上传失败";
  } finally {
    uploadingText.value = false;
    input.value = "";
  }
}

async function handleGeneratePrompt() {
  if (!form.value.title.trim()) {
    statusText.value = "请先填写任务标题";
    return;
  }
  if (!isDurationLimitValid.value) {
    statusText.value = "请先填写合法的最大总时长（1-120 秒）";
    return;
  }
  generatingPrompt.value = true;
  statusText.value = "正在生成提示词...";
  try {
    const seconds = resolvePromptDurationSeconds();
    const result = await generateCreativePrompt({
      title: form.value.title,
      aspectRatio: form.value.aspectRatio,
      minDurationSeconds: seconds,
      maxDurationSeconds: seconds,
      introTemplate: "none",
      outroTemplate: "none",
      transcriptText: form.value.transcriptText || undefined,
      sourceFileNames: uploadedText.value?.fileName ? [uploadedText.value.fileName] : [],
      editingMode: "drama",
    });
    if (result.prompt?.trim()) {
      form.value.creativePrompt = result.prompt.trim();
      promptSource.value = `AI（${result.source || "model"}）`;
      statusText.value = "提示词生成成功";
    }
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "提示词生成失败";
  } finally {
    generatingPrompt.value = false;
  }
}

async function submitTask() {
  if (!isFormReady.value) {
    statusText.value = "请先补全任务参数";
    return;
  }
  const manualMax = normalizedManualMaxDurationSeconds.value;
  if (durationLimitMode.value === "manual" && manualMax === null) {
    statusText.value = "请先填写合法的最大总时长（1-120 秒）";
    return;
  }

  let minDurationSeconds: number | null = null;
  let maxDurationSeconds: number | null = null;
  if (durationLimitMode.value === "manual" && manualMax !== null) {
    const fallbackMin =
      minimumSupportedDurationSeconds.value ??
      parseDurationSeconds(options.value?.defaultVideoDurationSeconds) ??
      1;
    minDurationSeconds = Math.max(1, Math.min(manualMax, fallbackMin));
    maxDurationSeconds = manualMax;
  }

  submitting.value = true;
  localTaskStartedAtMs.value = Date.now();
  localTaskEndedAtMs.value = null;
  startProgress({ stage: "提交生成请求", message: "正在创建视频生成任务..." });
  statusText.value = "正在创建生成任务...";
  try {
    const creativePrompt = form.value.creativePrompt?.trim();
    const payload: CreateGenerationTaskRequest = {
      title: form.value.title.trim(),
      creativePrompt: creativePrompt || undefined,
      aspectRatio: form.value.aspectRatio,
      textAnalysisModel: form.value.textAnalysisModel || null,
      videoModel: form.value.videoModel || null,
      videoSize: form.value.videoSize || null,
      videoDurationSeconds: "auto",
      minDurationSeconds,
      maxDurationSeconds,
      transcriptText: form.value.transcriptText?.trim() || null,
      stopBeforeVideoGeneration: shouldStopBeforeVideoGeneration(),
    };
    const task = await createGenerationTask(payload);
    attachTask(task.id);
    statusText.value = "任务创建成功，右侧将持续更新任务进度";
  } catch (error) {
    const message = error instanceof Error ? error.message : "任务创建失败";
    statusText.value = message;
    failProgress(message);
  } finally {
    submitting.value = false;
  }
}

async function goToTasks() {
  await router.push({ name: "tasks" });
}

async function goToCurrentTask() {
  if (!progressTaskId.value) {
    return;
  }
  await router.push({ name: "tasks", query: { selected: progressTaskId.value } });
}

function formatTraceTime(value: string) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString("zh-CN", { hour12: false });
}

onMounted(() => {
  nowTicker = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 1000);
  void loadOptions();
});

onUnmounted(() => {
  if (nowTicker !== null) {
    window.clearInterval(nowTicker);
    nowTicker = null;
  }
});
</script>

<style scoped>
.new-task-view {
  display: grid;
  gap: 1rem;
}

.new-task-layout {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.new-task-main {
  min-width: 0;
}

.new-task-side {
  display: grid;
  gap: 1rem;
}

.submit-row {
  display: grid;
  gap: 0.75rem;
}

.submit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.submit-status {
  margin: 0;
  font-size: 0.9rem;
  color: #475569;
}

.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.8rem;
}

.panel-eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #5f7895;
}

.panel-head h3 {
  margin: 0.2rem 0 0;
  font-family: "Sora", "PingFang SC", sans-serif;
  font-size: 1.08rem;
  font-weight: 720;
  color: #0f2744;
}

.summary-grid {
  display: grid;
  gap: 0.6rem;
}

.summary-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  border-radius: 0.8rem;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(255, 255, 255, 0.78);
  padding: 0.58rem 0.72rem;
}

.summary-item span {
  font-size: 0.76rem;
  color: #64748b;
}

.summary-item strong {
  max-width: 72%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8rem;
  color: #1f334b;
}

.trace-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.6rem;
  max-height: 320px;
  overflow: auto;
}

.trace-item {
  border-radius: 0.8rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.78);
  padding: 0.6rem 0.7rem;
}

.trace-main {
  margin: 0;
  display: grid;
  gap: 0.25rem;
  font-size: 0.82rem;
  color: #334155;
}

.trace-stage {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.24);
  background: rgba(219, 234, 254, 0.72);
  color: #1d4ed8;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 0.14rem 0.42rem;
}

.trace-meta {
  margin: 0.35rem 0 0;
  font-size: 0.72rem;
  color: #64748b;
}

.trace-empty {
  margin: 0;
  font-size: 0.86rem;
  color: #64748b;
}

@media (min-width: 1200px) {
  .new-task-layout {
    grid-template-columns: minmax(0, 1.45fr) minmax(340px, 0.95fr);
  }

  .new-task-side {
    position: sticky;
    top: 1rem;
    align-self: start;
  }
}

@media (max-width: 640px) {
  .summary-item strong {
    max-width: 60%;
  }
}
</style>

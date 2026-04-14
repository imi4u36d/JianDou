<template>
  <section class="new-task-view">
    <div class="new-task-layout">
      <div class="new-task-main surface-panel surface-panel-warm p-6">
        <form class="grid gap-6" @submit.prevent="submitTask">
          <div class="new-task-workspace">
            <section class="composer-column composer-column-left">
              <section class="composer-section">
                <div class="composer-section__head">
                  <div>
                    <p class="composer-section__eyebrow">Parameters</p>
                    <h3>模型、Seed 与输出设置</h3>
                    <p>左侧只负责决定生成链路本身，包括模型组合、分辨率、数量和时长限制。</p>
                  </div>
                  <span class="surface-chip">{{ selectedModelCount }}/4 模型已选</span>
                </div>

                <div class="surface-tile parameter-cluster p-4">
                  <div class="parameter-cluster__head">
                    <p class="parameter-cluster__eyebrow">Task Frame</p>
                    <strong>任务框架</strong>
                  </div>
                  <div class="grid gap-4 md:grid-cols-[2fr,1fr]">
                    <label class="grid gap-2 text-sm text-slate-700">
                      任务标题
                      <input v-model="form.title" class="field-input" required placeholder="例如：都市小说第 3 章视频预告" />
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      画幅比例
                      <select v-model="form.aspectRatio" class="field-select">
                        <option v-for="item in aspectRatioOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                  </div>
                </div>

                <div class="surface-tile parameter-cluster field-matrix p-4">
                  <div class="parameter-cluster__head">
                    <p class="parameter-cluster__eyebrow">Model Pipeline</p>
                    <strong>模型链路</strong>
                  </div>
                  <div class="grid gap-4 sm:grid-cols-2">
                    <label class="grid gap-2 text-sm text-slate-700">
                      文本模型
                      <select v-model="form.textAnalysisModel" class="field-select">
                        <option :value="null">请选择文本模型</option>
                        <option v-for="item in textModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      视觉模型
                      <select v-model="form.visionModel" class="field-select">
                        <option :value="null">请选择视觉模型</option>
                        <option v-for="item in visionModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      关键帧模型
                      <select v-model="form.imageModel" class="field-select">
                        <option :value="null">请选择关键帧模型</option>
                        <option v-for="item in imageModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      视频模型
                      <select v-model="form.videoModel" class="field-select">
                        <option :value="null">请选择视频模型</option>
                        <option v-for="item in videoModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                  </div>
                </div>

                <div class="surface-tile parameter-cluster p-4">
                  <div class="parameter-cluster__head">
                    <p class="parameter-cluster__eyebrow">Output Control</p>
                    <strong>输出控制</strong>
                  </div>
                  <div class="grid gap-4 sm:grid-cols-2">
                    <label class="grid gap-2 text-sm text-slate-700">
                      <span class="field-label-inline">
                        <span>Seed</span>
                        <HintBell class="seed-hint-bell" title="Seed 使用说明" :text="seedCapabilityHint" align="left" />
                      </span>
                      <input
                        v-model="seedInput"
                        class="field-input"
                        type="number"
                        min="0"
                        step="1"
                        placeholder="留空则不指定"
                      />
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      清晰度 / 画幅
                      <select v-model="form.videoSize" class="field-select">
                        <option v-for="item in videoSizeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </label>
                    <label class="grid gap-2 text-sm text-slate-700">
                      输出视频数量
                      <select v-model="form.outputCount" class="field-select">
                        <option value="auto">自动（按脚本分镜）</option>
                        <option v-for="item in outputCountOptions" :key="item" :value="item">{{ item }} 条</option>
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
                        :min="minimumAllowedDurationSeconds ?? 1"
                        max="120"
                        step="1"
                        :placeholder="manualDurationPlaceholder"
                      />
                      <span class="text-xs text-slate-500">{{ manualDurationHint }}</span>
                    </label>
                  </div>
                </div>

                <div class="surface-tile p-4">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-slate-900">高分 Seed 复用</p>
                      <p class="mt-1 text-xs text-slate-500">按任务效果评分倒序读取已验证过的 seed，点击即可回填当前表单。</p>
                    </div>
                    <button type="button" class="btn-ghost btn-sm" :disabled="loadingReusableSeeds" @click="loadReusableSeeds">
                      {{ loadingReusableSeeds ? "刷新中..." : "刷新列表" }}
                    </button>
                  </div>
                  <p v-if="reusableSeedError" class="mt-3 text-sm text-rose-600">{{ reusableSeedError }}</p>
                  <div v-else-if="reusableSeedTasks.length" class="mt-4 grid gap-3">
                    <button
                      v-for="task in reusableSeedTasks"
                      :key="task.id"
                      type="button"
                      class="seed-source-card rounded-2xl px-4 py-3 text-left transition"
                      @click="applySeedFromTask(task)"
                    >
                      <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span class="surface-chip">Seed {{ formatReusableSeed(task.taskSeed) }}</span>
                        <span class="surface-chip">评分 {{ formatReusableRating(task.effectRating) }}</span>
                        <span v-if="task.ratedAt">{{ formatReusableDate(task.ratedAt) }}</span>
                      </div>
                      <p class="mt-2 text-sm font-semibold text-slate-900">{{ task.title }}</p>
                      <p class="mt-1 text-xs text-slate-500">
                        {{ task.aspectRatio || "未知画幅" }} · {{ task.status }} · {{ task.id }}
                      </p>
                      <p v-if="task.effectRatingNote" class="mt-2 line-clamp-2 text-sm text-slate-600">{{ task.effectRatingNote }}</p>
                      <p
                        v-if="selectedSeedSourceTaskId === task.id"
                        class="mt-2 text-xs font-medium text-emerald-700"
                      >
                        已回填到当前任务
                      </p>
                    </button>
                  </div>
                  <p v-else class="mt-3 text-sm text-slate-500">当前还没有可复用的高分 seed。</p>
                  <p class="mt-3 text-xs text-slate-500">提示：seed 复用只会回填种子，不会自动改动你当前选择的模型组合。</p>
                </div>
              </section>
            </section>

            <section class="composer-column composer-column-right">
              <section class="composer-section">
                <div class="composer-section__head">
                  <div>
                    <p class="composer-section__eyebrow">Creative Input</p>
                    <h3>提示词、正文输入与操作按钮</h3>
                    <p>右侧负责实际创作内容，填写提示词、导入正文，并从这里直接发起生成。</p>
                  </div>
                  <span class="surface-chip">{{ transcriptCharacterCount > 0 ? `${transcriptCharacterCount} 字文本` : "等待正文输入" }}</span>
                </div>

                <div class="creative-grid">
                  <div class="surface-tile p-4 creative-card">
                    <div class="creative-card__header flex flex-wrap items-center justify-between gap-3">
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
                      rows="12"
                      class="field-textarea mt-3 creative-card__textarea"
                      placeholder="描述人物关系、冲突推进、镜头语气、情绪节奏；留空则使用系统默认提示词。"
                    ></textarea>
                    <p class="mt-2 text-xs text-slate-500 creative-card__meta">提示词来源：{{ promptSourceLabel }}</p>
                  </div>

                  <div class="surface-tile p-4 creative-card">
                    <div class="creative-card__header flex flex-wrap items-center justify-between gap-3">
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
                      rows="12"
                      class="field-textarea mt-3 font-mono text-sm creative-card__textarea"
                      placeholder="可直接粘贴小说正文或上传 TXT 后自动填充。"
                    ></textarea>
                  </div>
                </div>

                <div class="submit-row">
                  <div class="submit-row__copy">
                    <p class="submit-row__eyebrow">Ready Check</p>
                    <strong>{{ submitLabel }}</strong>
                    <p class="submit-status">{{ statusText }}</p>
                  </div>
                  <div class="submit-actions">
                    <button class="btn-primary" type="submit" :disabled="submitting || !isFormReady">{{ submitLabel }}</button>
                    <button class="btn-secondary" type="button" :disabled="submitting" @click="goToTasks">查看任务列表</button>
                    <button class="btn-ghost" type="button" :disabled="!progressTaskId" @click="goToCurrentTask">查看当前任务</button>
                  </div>
                </div>
              </section>
            </section>
          </div>
        </form>
      </div>

      <section class="new-task-progress-area">
        <div class="new-task-progress-card">
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
        </div>

        <section class="surface-panel p-5 new-task-trace-card">
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
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchGenerationOptions } from "@/api/generation";
import { createGenerationTask, fetchTasks, generateCreativePrompt, uploadText } from "@/api/tasks";
import TaskProgressCard from "@/components/generate/TaskProgressCard.vue";
import { useTaskProgress } from "@/components/generate/useTaskProgress";
import HintBell from "@/components/HintBell.vue";
import { shouldStopBeforeVideoGeneration } from "@/workbench/developer-settings";
import type {
  CreateGenerationTaskRequest,
  GenerationAspectRatioOption,
  GenerationOptionsResponse,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
  TaskListItem,
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
const seedInput = ref("");
const reusableSeedTasks = ref<TaskListItem[]>([]);
const loadingReusableSeeds = ref(false);
const reusableSeedError = ref("");
const selectedSeedSourceTaskId = ref("");
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
  visionModel: null,
  imageModel: null,
  videoModel: null,
  videoSize: null,
  outputCount: "auto",
  seed: null,
  videoDurationSeconds: null,
  transcriptText: "",
});

function normalizeModelName(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s._-]/g, "");
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

function parseSeed(value: unknown): number | null {
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
  const seed = Math.trunc(numeric);
  if (seed < 0) {
    return null;
  }
  return seed;
}

function formatReusableSeed(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? String(Math.trunc(value)) : "未设置";
}

function formatReusableRating(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${Math.trunc(value)}/5` : "未评分";
}

function formatReusableDate(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString("zh-CN", { hour12: false });
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
const aspectRatioOptions = computed<GenerationAspectRatioOption[]>(() => options.value?.aspectRatios ?? []);
const visionModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.visionModels ?? []);
const imageModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.imageModels ?? []);
const videoModelOptions = computed<GenerationVideoModelInfo[]>(() => options.value?.videoModels ?? []);
const outputCountOptions = computed<number[]>(() => Array.from({ length: 20 }, (_, index) => index + 1));
const selectedVisionModelOption = computed<GenerationTextAnalysisModelInfo | null>(() => {
  const selectedVisionModel = normalizeModelName(form.value.visionModel);
  if (!selectedVisionModel) {
    return null;
  }
  return (
    visionModelOptions.value.find((item) => normalizeModelName(item.value) === selectedVisionModel) ?? null
  );
});
const selectedVideoModelOption = computed<GenerationVideoModelInfo | null>(() => {
  const selectedVideoModel = normalizeModelName(form.value.videoModel);
  if (!selectedVideoModel) {
    return null;
  }
  return (
    videoModelOptions.value.find((item) => normalizeModelName(item.value) === selectedVideoModel) ?? null
  );
});
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
  const modelDurations = Array.isArray(selectedVideoModelOption.value?.supportedDurations)
    ? selectedVideoModelOption.value?.supportedDurations ?? []
    : [];
  if (modelDurations.length) {
    return [...new Set(modelDurations)]
      .filter((item) => Number.isFinite(item) && item > 0)
      .sort((a, b) => a - b)
      .map((item) => ({
        value: Math.trunc(item),
        label: `${Math.trunc(item)} 秒`,
      }));
  }
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
const minimumAllowedDurationSeconds = computed(() => minimumSupportedDurationSeconds.value ?? 1);
const normalizedManualMaxDurationSeconds = computed(() => parseDurationSeconds(manualMaxDurationSeconds.value));
const manualDurationHint = computed(() => {
  const minimum = minimumAllowedDurationSeconds.value;
  return `当前视频模型要求时长至少 ${minimum} 秒，最大 120 秒。`;
});
const manualDurationPlaceholder = computed(() => {
  const minimum = minimumAllowedDurationSeconds.value;
  return `请输入 ${minimum}-120`;
});
const manualDurationValidationMessage = computed(() => {
  const minimum = minimumAllowedDurationSeconds.value;
  if (!manualMaxDurationSeconds.value.trim()) {
    return `请先填写合法的最大总时长（${minimum}-120 秒）`;
  }
  if (normalizedManualMaxDurationSeconds.value === null) {
    return `请先填写合法的最大总时长（${minimum}-120 秒）`;
  }
  if (normalizedManualMaxDurationSeconds.value < minimum) {
    return `当前视频模型要求最大总时长至少为 ${minimum} 秒`;
  }
  return "";
});
const isDurationLimitValid = computed(() => {
  if (durationLimitMode.value === "auto") {
    return true;
  }
  return Boolean(normalizedManualMaxDurationSeconds.value !== null && !manualDurationValidationMessage.value);
});
const promptSourceLabel = computed(() => {
  return form.value.creativePrompt?.trim() ? promptSource.value : "系统默认";
});

const selectedModelCount = computed(() => {
  return [
    form.value.textAnalysisModel,
    form.value.visionModel,
    form.value.imageModel,
    form.value.videoModel,
  ].filter(Boolean).length;
});

const transcriptCharacterCount = computed(() => form.value.transcriptText.trim().length);

const seedCapabilityHint = computed(() => {
  const visionSupportsSeed = Boolean(selectedVisionModelOption.value?.supportsSeed);
  const videoSupportsSeed = Boolean(selectedVideoModelOption.value?.supportsSeed);
  if (visionSupportsSeed && videoSupportsSeed) {
    return "当前视觉模型和视频模型都会使用该 seed。";
  }
  if (videoSupportsSeed) {
    return "当前仅视频模型会使用该 seed。";
  }
  if (visionSupportsSeed) {
    return "当前仅视觉模型会使用该 seed。";
  }
  return "当前所选模型未声明支持 seed，保存后仅做任务记录。";
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
  return Boolean(
    form.value.title.trim() &&
      form.value.textAnalysisModel &&
      form.value.visionModel &&
      form.value.imageModel &&
      form.value.videoModel &&
      isDurationLimitValid.value,
  );
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
    form.value.aspectRatio = (result.defaultAspectRatio as "9:16" | "16:9" | null) || form.value.aspectRatio;
    form.value.textAnalysisModel = null;
    form.value.visionModel = null;
    form.value.imageModel = null;
    form.value.videoModel = null;
    form.value.outputCount = "auto";
    form.value.videoDurationSeconds = "auto";
    if (!manualMaxDurationSeconds.value.trim()) {
      const fallbackDuration =
        parseDurationSeconds(result.defaultVideoDurationSeconds) ??
        parseDurationSeconds(result.videoDurations[0]?.value);
      if (fallbackDuration !== null) {
        manualMaxDurationSeconds.value = String(fallbackDuration);
      }
    }
    statusText.value = "参数已加载，请先选择模型再创建任务";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "加载模型配置失败";
  } finally {
    loadingOptions.value = false;
  }
}

async function loadReusableSeeds() {
  loadingReusableSeeds.value = true;
  reusableSeedError.value = "";
  try {
    const tasks = await fetchTasks({ sort: "effect_rating_desc" });
    reusableSeedTasks.value = tasks
      .filter((task) => typeof task.taskSeed === "number" && Number.isFinite(task.taskSeed))
      .filter((task) => typeof task.effectRating === "number" && Number.isFinite(task.effectRating) && task.effectRating > 0)
      .slice(0, 8);
  } catch (error) {
    reusableSeedError.value = error instanceof Error ? error.message : "读取高分 seed 失败";
  } finally {
    loadingReusableSeeds.value = false;
  }
}

function applySeedFromTask(task: TaskListItem) {
  const seed = task.taskSeed;
  if (typeof seed !== "number" || !Number.isFinite(seed)) {
    return;
  }
  seedInput.value = String(Math.trunc(seed));
  selectedSeedSourceTaskId.value = task.id;
  statusText.value = `已复用任务 ${task.id} 的高分 seed：${Math.trunc(seed)}`;
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
    const configuredDefault = options.value?.defaultVideoSize;
    const matchedDefault = configuredDefault ? items.find((item) => item.value === configuredDefault) : null;
    form.value.videoSize = matchedDefault?.value ?? items[0].value;
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
    statusText.value = manualDurationValidationMessage.value;
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
    statusText.value = "请先补全任务参数并选择全部模型";
    return;
  }
  const manualMax = normalizedManualMaxDurationSeconds.value;
  if (durationLimitMode.value === "manual" && manualMax === null) {
    statusText.value = manualDurationValidationMessage.value;
    return;
  }
  if (durationLimitMode.value === "manual" && manualDurationValidationMessage.value) {
    statusText.value = manualDurationValidationMessage.value;
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
      visionModel: form.value.visionModel || null,
      imageModel: form.value.imageModel || null,
      videoModel: form.value.videoModel || null,
      videoSize: form.value.videoSize || null,
      outputCount: form.value.outputCount ?? "auto",
      seed: parseSeed(seedInput.value),
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
  void loadReusableSeeds();
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

.new-task-view :deep(.surface-panel),
.new-task-view :deep(.surface-tile) {
  background: var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.new-task-view :deep(.surface-chip) {
  background: var(--bg-surface);
  color: var(--text-body);
  box-shadow: var(--shadow-pressed);
}

.new-task-layout {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.composer-section__eyebrow,
.submit-row__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.composer-section {
  display: grid;
  gap: 1rem;
}

.new-task-workspace {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.composer-column {
  min-width: 0;
}

.composer-section__head {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  justify-content: space-between;
  gap: 0.85rem;
}

.composer-section__head h3 {
  margin: 0.35rem 0 0;
  font-size: 1.15rem;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--text-strong);
}

.composer-section__head p:last-child {
  margin: 0.35rem 0 0;
  max-width: 56ch;
  line-height: 1.7;
  color: var(--text-body);
}

.field-matrix {
  position: relative;
}

.parameter-cluster {
  display: grid;
  gap: 0.95rem;
}

.parameter-cluster__head {
  display: grid;
  gap: 0.2rem;
}

.parameter-cluster__eyebrow {
  margin: 0;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.parameter-cluster__head strong {
  color: var(--text-strong);
  font-size: 0.98rem;
  letter-spacing: -0.02em;
}

.field-label-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
}

.seed-hint-bell {
  display: inline-flex;
}

.seed-hint-bell :deep(.hint-bell) {
  width: 1rem;
  height: 1rem;
  min-width: 1rem;
  color: var(--text-muted);
  background: transparent;
  box-shadow: none;
}

.seed-hint-bell :deep(.hint-bell:hover) {
  transform: none;
  box-shadow: none;
  color: var(--text-body);
}

.seed-hint-bell :deep(.hint-bell svg) {
  width: 0.78rem;
  height: 0.78rem;
}

.seed-hint-bell :deep(.hint-bell-dot) {
  display: none;
}

.creative-grid {
  display: grid;
  gap: 1rem;
}

.creative-card {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.creative-card__header {
  min-height: 2.5rem;
}

.creative-card__textarea {
  flex: 1;
}

.creative-card__meta {
  margin-top: 0.75rem;
}

.new-task-main {
  min-width: 0;
  position: relative;
  overflow: hidden;
}

.new-task-main::before {
  content: "";
  position: absolute;
  inset: -20% auto auto -12%;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 183, 174, 0.18), transparent 70%);
  pointer-events: none;
}

.new-task-progress-area {
  display: grid;
  gap: 1rem;
}

.new-task-progress-card,
.new-task-trace-card {
  min-width: 0;
}

.submit-row {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-radius: 1.4rem;
  border: 1px solid rgba(197, 108, 115, 0.16);
  padding: 1rem 1.05rem;
  background:
    linear-gradient(180deg, rgba(255, 240, 236, 0.88), rgba(255, 255, 255, 0.48)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.submit-row__copy {
  min-width: 220px;
}

.submit-row__copy strong {
  display: block;
  margin-top: 0.3rem;
  font-size: 1.05rem;
  line-height: 1.2;
  color: var(--text-strong);
}

.submit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.submit-status {
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
  color: var(--text-body);
}

.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.8rem;
}

.panel-eyebrow {
  color: var(--text-muted);
}

.panel-head h3 {
  margin: 0.2rem 0 0;
  font-size: 1.08rem;
  font-weight: 720;
  color: var(--text-strong);
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
  border-radius: 0.95rem;
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.3)),
    var(--bg-surface);
  padding: 0.6rem 0.7rem;
  box-shadow: var(--shadow-pressed);
}

.trace-main {
  margin: 0;
  display: grid;
  gap: 0.25rem;
  font-size: 0.82rem;
  color: var(--text-strong);
}

.trace-stage {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  background: var(--bg-surface);
  color: var(--accent-strong);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 0.14rem 0.42rem;
  box-shadow: var(--shadow-pressed);
}

.trace-meta {
  margin: 0.35rem 0 0;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.trace-empty {
  margin: 0;
  font-size: 0.86rem;
  color: var(--text-body);
  border-radius: 0.95rem;
  border: 1px dashed var(--surface-border-strong);
  padding: 0.85rem 0.95rem;
  background: rgba(255, 255, 255, 0.44);
}

.seed-source-card {
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.seed-source-card:hover {
  transform: translateY(-1px);
}

.seed-source-card:active {
  box-shadow: var(--shadow-pressed);
}

@media (min-width: 1200px) {
  .new-task-workspace {
    grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  }

  .creative-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }

  .creative-grid > * {
    height: 100%;
  }

  .new-task-progress-area {
    grid-template-columns: minmax(0, 1.12fr) minmax(320px, 0.88fr);
    align-items: start;
  }
}

@media (max-width: 640px) {
  .submit-row {
    padding: 1rem;
  }
}
</style>

<template>
  <section class="new-task-view">
    <form class="task-studio" @submit.prevent="submitTask">
      <aside class="surface-panel studio-panel studio-panel-rail">
        <div class="studio-panel__head">
          <div>
            <p class="studio-eyebrow">配置轨道</p>
            <h2>模型链路</h2>
          </div>
          <span class="surface-chip">已选 {{ selectedModelCount }}/4</span>
        </div>

        <label class="studio-field">
          <span>任务标题</span>
          <input v-model="form.title" class="field-input" required placeholder="例如：悬疑短剧第 12 集预告" />
        </label>

        <div class="model-rail">
          <div class="model-rail__line" aria-hidden="true"></div>

          <label class="model-rail__item">
            <span class="model-rail__dot"></span>
            <span class="model-rail__label">文本模型</span>
            <select v-model="form.textAnalysisModel" class="field-select">
              <option :value="null">请选择文本模型</option>
              <option v-for="item in textModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>

          <label class="model-rail__item">
            <span class="model-rail__dot"></span>
            <span class="model-rail__label">视觉模型</span>
            <select v-model="form.visionModel" class="field-select">
              <option :value="null">请选择视觉模型</option>
              <option v-for="item in visionModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>

          <label class="model-rail__item">
            <span class="model-rail__dot"></span>
            <span class="model-rail__label">关键帧模型</span>
            <select v-model="form.imageModel" class="field-select">
              <option :value="null">请选择关键帧模型</option>
              <option v-for="item in imageModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>

          <label class="model-rail__item">
            <span class="model-rail__dot"></span>
            <span class="model-rail__label">视频模型</span>
            <select v-model="form.videoModel" class="field-select">
              <option :value="null">请选择视频模型</option>
              <option v-for="item in videoModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
        </div>

        <section class="surface-tile control-card">
          <div class="control-card__head">
            <div>
              <p class="studio-eyebrow">参数控制</p>
              <h3>输出设置</h3>
            </div>
            <HintBell title="种子使用说明" :text="seedCapabilityHint" align="left" />
          </div>

          <div class="ratio-toggle">
            <button
              v-for="item in aspectRatioOptions"
              :key="item.value"
              type="button"
              class="ratio-toggle__item"
              :class="{ 'ratio-toggle__item-active': form.aspectRatio === item.value }"
              @click="form.aspectRatio = item.value"
            >
              {{ item.value }}
            </button>
          </div>

          <div class="control-grid">
            <label class="studio-field">
              <span>清晰度</span>
              <select v-model="form.videoSize" class="field-select">
                <option v-for="item in videoSizeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>

            <label class="studio-field">
              <span>输出数量</span>
              <select v-model="form.outputCount" class="field-select">
                <option value="auto">自动</option>
                <option v-for="item in outputCountOptions" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>

            <label class="studio-field">
              <span>时长模式</span>
              <select v-model="durationLimitMode" class="field-select">
                <option value="auto">自动</option>
                <option value="manual">手动</option>
              </select>
            </label>

            <label v-if="durationLimitMode === 'manual'" class="studio-field">
              <span>最大时长</span>
              <input
                v-model="manualMaxDurationSeconds"
                class="field-input"
                type="number"
                min="5"
                max="12"
                step="1"
                :placeholder="manualDurationPlaceholder"
              />
            </label>
          </div>

          <p class="control-card__hint">
            {{ durationLimitMode === "manual" ? manualDurationHint : "自动模式会跟随当前视频模型能力。" }}
          </p>
          <p v-if="durationLimitMode === 'manual' && manualDurationValidationMessage" class="control-card__error">
            {{ manualDurationValidationMessage }}
          </p>
        </section>

        <section class="surface-tile seed-library">
          <div class="seed-library__head">
            <div>
              <p class="studio-eyebrow">种子库</p>
              <h3>高分复用</h3>
            </div>
            <button type="button" class="btn-ghost btn-sm" :disabled="loadingReusableSeeds" @click="loadReusableSeeds">
              {{ loadingReusableSeeds ? "加载中..." : "刷新" }}
            </button>
          </div>

          <p v-if="reusableSeedError" class="control-card__error">{{ reusableSeedError }}</p>
          <div v-else-if="reusableSeedTasks.length" class="seed-library__list">
            <button
              v-for="task in reusableSeedTasks"
              :key="task.id"
              type="button"
              class="seed-library__item"
              :class="{ 'seed-library__item-active': selectedSeedSourceTaskId === task.id }"
              @click="applySeedFromTask(task)"
            >
              <div class="seed-library__chips">
                <span class="surface-chip">种子 {{ formatReusableSeed(task.taskSeed) }}</span>
                <span class="surface-chip">评分 {{ formatReusableRating(task.effectRating) }}</span>
              </div>
              <strong>{{ task.title }}</strong>
              <small>{{ task.aspectRatio || "未知画幅" }} · {{ formatReusableDate(task.ratedAt) || task.status }}</small>
            </button>
          </div>
          <p v-else class="seed-library__empty">当前还没有可复用的高分种子。</p>
        </section>
      </aside>

      <section class="surface-panel studio-panel studio-panel-core">
        <div class="studio-panel__head">
          <div>
            <p class="studio-eyebrow">创作核心</p>
            <h2>提示词与正文内容</h2>
          </div>
          <span class="surface-chip">{{ transcriptCharacterCount > 0 ? `${transcriptCharacterCount} 字` : "等待正文输入" }}</span>
        </div>

        <div class="core-topbar">
          <button type="button" class="btn-primary core-topbar__action" :disabled="generatingPrompt || loadingOptions" @click="handleGeneratePrompt">
            {{ generatingPrompt ? "生成中..." : "智能生成提示词" }}
          </button>
          <button type="button" class="btn-secondary btn-sm" :disabled="uploadingText" @click="textFileInput?.click()">
            {{ uploadingText ? "上传中..." : "上传文本" }}
          </button>
          <input
            ref="textFileInput"
            type="file"
            accept=".txt,text/plain"
            class="hidden"
            @change="handleTextFileChange"
          />
        </div>

        <p class="core-upload-label">{{ uploadedTextLabel }}</p>

        <label class="studio-field">
          <span>小说正文</span>
          <textarea
            v-model="form.transcriptText"
            rows="12"
            class="field-textarea core-textarea"
            placeholder="可直接粘贴小说正文，或上传文本文件自动填充。"
          ></textarea>
        </label>

        <label class="studio-field">
          <span>全局创意提示词</span>
          <textarea
            v-model="form.creativePrompt"
            rows="5"
            class="field-textarea"
            placeholder="填写全局创意提示词..."
          ></textarea>
        </label>

        <div class="core-bottom-grid">
          <label class="studio-field">
            <span>种子</span>
            <input
              v-model="seedInput"
              class="field-input"
              type="number"
              min="0"
              step="1"
              placeholder="可选"
            />
          </label>

          <div class="surface-tile core-status">
            <p class="studio-eyebrow">提交检查</p>
            <strong>{{ submitLabel }}</strong>
            <p>{{ statusText }}</p>
            <p class="core-status__meta">提示词来源：{{ promptSourceLabel }}</p>
          </div>
        </div>

        <div class="core-actions">
          <button class="btn-primary" type="submit" :disabled="submitting || !isFormReady || loadingOptions">{{ submitLabel }}</button>
          <button class="btn-secondary" type="button" :disabled="submitting" @click="goToTasks">查看任务</button>
          <button class="btn-ghost" type="button" :disabled="!progressTaskId" @click="goToCurrentTask">打开当前任务</button>
        </div>
      </section>

      <aside class="surface-panel studio-panel studio-panel-trace">
        <div class="studio-panel__head">
          <div>
            <p class="studio-eyebrow">实时追踪</p>
            <h2>执行监控</h2>
          </div>
          <span class="surface-chip">{{ progressState.status }}</span>
        </div>

        <div class="trace-ring-shell">
          <div class="trace-ring" :style="{ '--progress': `${progressState.progress}%` }">
            <div class="trace-ring__inner">
              <p>{{ progressState.stage }}</p>
              <strong>{{ progressState.progress }}%</strong>
            </div>
          </div>
          <p class="trace-ring__meta">{{ progressElapsedLabel || "任务开始后会显示耗时。" }}</p>
        </div>

        <div v-if="previewOutputUrl" class="trace-preview">
          <p class="trace-preview__title">{{ previewResultTitle }}</p>
          <video :src="previewOutputUrl" controls playsinline preload="metadata"></video>
          <div class="trace-preview__meta">
            <span v-for="item in previewResultMeta" :key="item">{{ item }}</span>
          </div>
        </div>

        <section class="trace-feed">
          <div class="trace-feed__head">
            <h3>最近追踪</h3>
            <span class="surface-chip">{{ progressTraceCount }}</span>
          </div>
          <ul v-if="recentTraceEvents.length" class="trace-feed__list">
            <li v-for="(item, index) in recentTraceEvents" :key="`${item.timestamp}-${item.event}-${index}`" class="trace-feed__item">
              <p>[{{ formatTraceTime(item.timestamp) }}] {{ item.message }}</p>
              <small>{{ item.stage }} · {{ item.level }}</small>
            </li>
          </ul>
          <div v-else class="trace-feed__empty">创建任务后，这里会显示最近追踪记录。</div>
        </section>
      </aside>
    </form>
  </section>
</template>

<script setup lang="ts">
/**
 * New任务页面组件。
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchGenerationOptions } from "@/api/generation";
import { createGenerationTask, fetchTasks, generateCreativePrompt, uploadText } from "@/api/tasks";
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
const MANUAL_DURATION_MIN_SECONDS = 5;
const MANUAL_DURATION_MAX_SECONDS = 12;
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

/**
 * 规范化模型Name。
 * @param value 待处理的值
 * @return 处理结果
 */
function normalizeModelName(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s._-]/g, "");
}

/**
 * 解析时长Seconds。
 * @param value 待处理的值
 * @return 处理结果
 */
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

/**
 * 解析种子。
 * @param value 待处理的值
 * @return 处理结果
 */
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

/**
 * 格式化可复用种子。
 * @param value 待处理的值
 * @return 处理结果
 */
function formatReusableSeed(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? String(Math.trunc(value)) : "未设置";
}

/**
 * 格式化可复用评分。
 * @param value 待处理的值
 * @return 处理结果
 */
function formatReusableRating(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${Math.trunc(value)}/5` : "未评分";
}

/**
 * 格式化可复用日期。
 * @param value 待处理的值
 * @return 处理结果
 */
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

/**
 * 处理解析提示词时长Seconds。
 * @return 处理结果
 */
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

/**
 * 处理解析视频Size。
 * @param size size值
 */
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

/**
 * 处理解析AspectRatio。
 * @param size size值
 * @return 处理结果
 */
function resolveAspectRatio(size: GenerationVideoSizeOption): "9:16" | "16:9" | null {
  const parsed = resolveVideoSize(size);
  if (!parsed) {
    return null;
  }
  return parsed.width >= parsed.height ? "16:9" : "9:16";
}

/**
 * 处理比较视频SizeBy面积。
 * @param a a值
 * @param b b值
 * @return 处理结果
 */
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
const aspectRatioOptions = computed<Array<GenerationAspectRatioOption & { value: CreateGenerationTaskRequest["aspectRatio"] }>>(() => {
  return (options.value?.aspectRatios ?? []).filter(
    (item): item is GenerationAspectRatioOption & { value: CreateGenerationTaskRequest["aspectRatio"] } => {
      return item.value === "9:16" || item.value === "16:9";
    },
  );
});
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
      // 先按画幅比过滤，避免把当前任务无法直接使用的尺寸暴露给用户。
      const ratio = resolveAspectRatio(item);
      return !ratio || ratio === targetAspectRatio;
    })
    .filter((item) => {
      if (!selectedVideoModel) {
        return true;
      }
      // 再按模型能力收窄选项，确保表单提交前就满足后端目录配置约束。
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
    // 模型显式声明支持时长时，优先使用模型能力本身，避免被全局默认值误导。
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
const normalizedManualMaxDurationSeconds = computed(() => parseDurationSeconds(manualMaxDurationSeconds.value));
const manualDurationHint = computed(() => {
  return `手动模式下时长限制为 ${MANUAL_DURATION_MIN_SECONDS}-${MANUAL_DURATION_MAX_SECONDS} 秒。`;
});
const manualDurationPlaceholder = computed(() => {
  return `请输入 ${MANUAL_DURATION_MIN_SECONDS}-${MANUAL_DURATION_MAX_SECONDS}`;
});
const manualDurationValidationMessage = computed(() => {
  if (!manualMaxDurationSeconds.value.trim()) {
    return `请先填写合法的最大总时长（${MANUAL_DURATION_MIN_SECONDS}-${MANUAL_DURATION_MAX_SECONDS} 秒）`;
  }
  if (normalizedManualMaxDurationSeconds.value === null) {
    return `请先填写合法的最大总时长（${MANUAL_DURATION_MIN_SECONDS}-${MANUAL_DURATION_MAX_SECONDS} 秒）`;
  }
  if (normalizedManualMaxDurationSeconds.value < MANUAL_DURATION_MIN_SECONDS || normalizedManualMaxDurationSeconds.value > MANUAL_DURATION_MAX_SECONDS) {
    return `手动模式的最大总时长需在 ${MANUAL_DURATION_MIN_SECONDS}-${MANUAL_DURATION_MAX_SECONDS} 秒之间`;
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

const transcriptCharacterCount = computed(() => (form.value.transcriptText ?? "").trim().length);

const seedCapabilityHint = computed(() => {
  const visionSupportsSeed = Boolean(selectedVisionModelOption.value?.supportsSeed);
  const videoSupportsSeed = Boolean(selectedVideoModelOption.value?.supportsSeed);
  if (visionSupportsSeed && videoSupportsSeed) {
    return "当前视觉模型和视频模型都会使用该种子。";
  }
  if (videoSupportsSeed) {
    return "当前仅视频模型会使用该种子。";
  }
  if (visionSupportsSeed) {
    return "当前仅视觉模型会使用该种子。";
  }
  return "当前所选模型未声明支持种子，保存后仅做任务记录。";
});

/**
 * 解析时间戳毫秒。
 * @param value 待处理的值
 * @return 处理结果
 */
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

/**
 * 格式化Elapsed标签。
 * @param seconds seconds值
 * @return 处理结果
 */
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
    return "未上传文本文件";
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

/**
 * 处理read文本文件。
 * @param file 待上传的文件
 * @return 处理结果
 */
function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error ?? new Error("读取文本文件失败"));
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
        parseDurationSeconds(result.videoDurations[0]?.value) ??
        MANUAL_DURATION_MIN_SECONDS;
      manualMaxDurationSeconds.value = String(
        Math.max(MANUAL_DURATION_MIN_SECONDS, Math.min(MANUAL_DURATION_MAX_SECONDS, fallbackDuration)),
      );
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
    reusableSeedError.value = error instanceof Error ? error.message : "读取高分种子失败";
  } finally {
    loadingReusableSeeds.value = false;
  }
}

/**
 * 应用种子From任务。
 * @param task 要处理的任务对象
 */
function applySeedFromTask(task: TaskListItem) {
  const seed = task.taskSeed;
  if (typeof seed !== "number" || !Number.isFinite(seed)) {
    return;
  }
  seedInput.value = String(Math.trunc(seed));
  selectedSeedSourceTaskId.value = task.id;
  statusText.value = `已复用任务 ${task.id} 的高分种子：${Math.trunc(seed)}`;
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
  statusText.value = "正在上传文本文件...";
  try {
    const [uploaded, content] = await Promise.all([uploadText(file), readTextFile(file)]);
    uploadedText.value = uploaded;
    if (content.trim()) {
      form.value.transcriptText = content;
      if (!form.value.title.trim() || form.value.title === "文本生成任务") {
        form.value.title = file.name.replace(/\.txt$/i, "") || "文本生成任务";
      }
    }
    statusText.value = "文本文件已上传并填充正文";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "文本文件上传失败";
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
      promptSource.value = `智能生成（${result.source || "模型"}）`;
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
    minDurationSeconds = MANUAL_DURATION_MIN_SECONDS;
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

/**
 * 格式化追踪时间。
 * @param value 待处理的值
 */
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
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.task-studio {
  display: grid;
  gap: 22px;
  align-items: start;
  height: 100%;
  min-height: 0;
  grid-template-columns: minmax(280px, 0.88fr) minmax(420px, 1fr) minmax(300px, 0.82fr);
}

.studio-panel {
  display: grid;
  gap: 20px;
  min-width: 0;
  min-height: 0;
  max-height: 100%;
  padding: 18px;
  overflow: auto;
}

.studio-panel__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.studio-panel__head h2,
.control-card__head h3,
.seed-library__head h3,
.trace-feed__head h3 {
  margin: 0.28rem 0 0;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.95);
}

.studio-eyebrow {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.studio-field {
  display: grid;
  gap: 0.55rem;
}

.studio-field > span {
  color: rgba(255, 255, 255, 0.74);
  font-size: 0.82rem;
  font-weight: 600;
}

.model-rail {
  position: relative;
  display: grid;
  gap: 18px;
  padding-left: 22px;
}

.model-rail__line {
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 5px;
  width: 2px;
  background: linear-gradient(180deg, rgba(176, 92, 255, 0.9), rgba(78, 219, 255, 0.88), rgba(176, 92, 255, 0.9));
  box-shadow:
    0 0 16px rgba(176, 92, 255, 0.24),
    0 0 22px rgba(78, 219, 255, 0.2);
}

.model-rail__item {
  position: relative;
  display: grid;
  gap: 0.5rem;
}

.model-rail__dot {
  position: absolute;
  left: -22px;
  top: 13px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(180deg, #b05cff, #4edbff);
  box-shadow:
    0 0 0 3px rgba(8, 11, 18, 0.96),
    0 0 18px rgba(120, 147, 255, 0.32);
}

.model-rail__label {
  color: rgba(255, 255, 255, 0.86);
  font-size: 0.82rem;
  font-weight: 600;
}

.control-card,
.seed-library,
.core-status {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.control-card__head,
.seed-library__head,
.trace-feed__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ratio-toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.ratio-toggle__item {
  min-height: 44px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.74);
  font-weight: 700;
}

.ratio-toggle__item-active {
  border-color: rgba(145, 180, 255, 0.4);
  background: linear-gradient(180deg, rgba(176, 92, 255, 0.18), rgba(78, 219, 255, 0.08));
  color: #8fc6ff;
  box-shadow: var(--shadow-glow);
}

.control-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.control-card__hint {
  margin: -2px 0 0;
  color: var(--text-muted);
  font-size: 0.76rem;
}

.control-card__error {
  margin: 0;
  color: #ff9eb3;
  font-size: 0.78rem;
}

.seed-library__list {
  display: grid;
  gap: 10px;
  overflow: auto;
}

.seed-library__item {
  display: grid;
  gap: 8px;
  text-align: left;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.seed-library__item:hover {
  transform: translateY(-1px);
  border-color: rgba(145, 180, 255, 0.24);
}

.seed-library__item-active {
  border-color: rgba(145, 180, 255, 0.4);
  box-shadow: var(--shadow-glow);
}

.seed-library__item strong {
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.88rem;
}

.seed-library__item small,
.seed-library__empty,
.core-upload-label {
  color: var(--text-muted);
  font-size: 0.76rem;
  line-height: 1.55;
}

.seed-library__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.core-topbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.core-topbar__action {
  flex: 1 1 220px;
}

.core-textarea {
  min-height: 300px;
}

.core-bottom-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: minmax(0, 0.82fr) minmax(0, 1.18fr);
  align-items: start;
}

.core-status strong {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.98rem;
}

.core-status p {
  margin: 0;
  color: var(--text-body);
  line-height: 1.65;
}

.core-status__meta {
  color: var(--text-muted);
  font-size: 0.78rem;
}

.core-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.studio-panel-trace {
  align-self: stretch;
  grid-template-rows: auto auto auto 1fr;
}

.trace-ring-shell {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 8px 0 2px;
}

.trace-ring {
  --progress: 0%;
  position: relative;
  width: min(240px, 100%);
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, rgba(10, 13, 20, 0.96) 56%, transparent 57%),
    conic-gradient(from 220deg, rgba(255, 255, 255, 0.1) 0 25%, #b05cff 45%, #8f93ff 70%, #4edbff 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.04),
    0 20px 40px rgba(0, 0, 0, 0.24);
}

.trace-ring::before {
  content: "";
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  background:
    conic-gradient(from 220deg, rgba(255, 255, 255, 0.08) 0 var(--progress), rgba(255, 255, 255, 0.06) var(--progress) 100%);
  mask: radial-gradient(farthest-side, transparent calc(100% - 16px), #000 calc(100% - 15px));
}

.trace-ring__inner {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 8px;
  justify-items: center;
  width: 68%;
  text-align: center;
}

.trace-ring__inner p {
  margin: 0;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.45;
}

.trace-ring__inner strong {
  font-size: 2.3rem;
  line-height: 1;
  letter-spacing: -0.06em;
  color: rgba(255, 255, 255, 0.98);
}

.trace-ring__meta {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.trace-preview {
  display: grid;
  gap: 10px;
  align-content: start;
}

.trace-preview__title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
}

.trace-preview video {
  width: 100%;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.8);
}

.trace-preview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trace-preview__meta span {
  display: inline-flex;
  padding: 0.25rem 0.58rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  font-size: 0.7rem;
}

.trace-feed {
  display: grid;
  gap: 12px;
  min-height: 0;
}

.trace-feed__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
}

.trace-feed__item,
.trace-feed__empty {
  padding: 14px;
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.trace-feed__item p,
.trace-feed__item small {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.trace-feed__item p {
  color: rgba(255, 255, 255, 0.84);
  font-size: 0.76rem;
  line-height: 1.65;
}

.trace-feed__item small {
  display: block;
  margin-top: 0.38rem;
  color: rgba(255, 255, 255, 0.38);
  font-size: 0.68rem;
}

.trace-feed__empty {
  color: var(--text-muted);
  font-size: 0.82rem;
}

@media (max-width: 1380px) {
  .task-studio {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: auto;
  }

  .studio-panel-trace {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .task-studio {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .core-bottom-grid,
  .control-grid {
    grid-template-columns: 1fr;
  }

  .core-actions {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .studio-panel {
    padding: 14px;
  }

  .trace-ring {
    width: min(200px, 100%);
  }
}
</style>

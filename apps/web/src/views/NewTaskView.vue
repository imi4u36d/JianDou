<template>
  <section class="new-task-view">
    <form class="task-studio" @submit.prevent="submitTask">
      <section class="generate-hero">
        <h1>使用 <span>Agent 模式</span> 立即开始创作！</h1>

        <section class="composer-card">
          <button
            type="button"
            class="composer-upload"
            :disabled="uploadingText"
            @click="textFileInput?.click()"
          >
            <span>+</span>
          </button>
          <input
            ref="textFileInput"
            type="file"
            accept=".txt,text/plain"
            class="hidden"
            @change="handleTextFileChange"
          />

          <label class="composer-title">
            <span>任务标题</span>
            <input
              v-model="form.title"
              required
              placeholder="例如：悬疑短剧第 12 集预告"
            />
          </label>

          <label class="composer-main">
            <span>小说正文</span>
            <textarea
              v-model="form.transcriptText"
              rows="6"
              placeholder="上传小说、输入文字，煎豆会自动拆解脚本、关键帧与视频生成链路"
            ></textarea>
          </label>

          <label class="composer-prompt">
            <span>全局创意提示词</span>
            <textarea
              v-model="form.creativePrompt"
              rows="2"
              placeholder="可选：补充风格、节奏、镜头方向"
            ></textarea>
          </label>

          <div class="composer-toolbar">
            <button type="button" class="tool-pill tool-pill-accent">Agent 模式</button>
            <button type="button" class="tool-pill">自动</button>
            <button type="button" class="tool-pill">灵感搜索</button>
            <button type="button" class="tool-pill">创意设计</button>
            <span class="composer-count">{{ transcriptCharacterCount > 0 ? `${transcriptCharacterCount} 字` : "等待正文输入" }}</span>
          </div>

          <button class="composer-submit" type="submit" :disabled="submitting || !isFormReady || loadingOptions" :title="submitLabel">
            <svg v-if="!submitting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 19V5" />
              <path d="m5 12 7-7 7 7" />
            </svg>
            <span v-else>...</span>
          </button>
        </section>
      </section>

      <section class="studio-section studio-section-models">
        <div class="studio-section__head">
          <div>
            <p class="studio-eyebrow">模型链路</p>
            <h2>高级参数</h2>
          </div>
          <span class="surface-chip surface-chip-compact">已选 {{ selectedModelCount }}/3</span>
        </div>

        <div class="studio-grid">
          <div class="model-rail">
            <label class="model-rail__item">
              <span class="model-rail__label">文本模型</span>
              <AppSelect v-model="form.textAnalysisModel" :options="textModelSelectOptions" compact />
            </label>

            <label class="model-rail__item">
              <span class="model-rail__label">关键帧模型</span>
              <AppSelect v-model="form.imageModel" :options="imageModelSelectOptions" compact />
            </label>

            <label class="model-rail__item">
              <span class="model-rail__label">视频模型</span>
              <AppSelect v-model="form.videoModel" :options="videoModelSelectOptions" compact />
            </label>
          </div>

          <section class="control-card">
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
                <AppSelect v-model="form.videoSize" :options="videoSizeSelectOptions" compact />
              </label>

              <label class="studio-field">
                <span>输出数量</span>
                <AppSelect v-model="form.outputCount" :options="outputCountSelectOptions" compact />
              </label>

              <label class="studio-field">
                <span>时长模式</span>
                <AppSelect v-model="durationLimitMode" :options="durationLimitModeOptions" compact />
              </label>

              <label v-if="durationLimitMode === 'manual'" class="studio-field">
                <span>最大时长</span>
                <input
                  v-model="manualMaxDurationSeconds"
                  class="field-input field-input-compact"
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

            <div class="seed-control">
              <div class="seed-control__head">
                <span>种子</span>
                <span class="surface-chip surface-chip-compact">{{ seedMode === "auto" ? "自动生成" : "手动输入" }}</span>
              </div>

              <div class="ratio-toggle seed-mode-toggle">
                <button
                  type="button"
                  class="ratio-toggle__item"
                  :class="{ 'ratio-toggle__item-active': seedMode === 'auto' }"
                  @click="seedMode = 'auto'"
                >
                  自动
                </button>
                <button
                  type="button"
                  class="ratio-toggle__item"
                  :class="{ 'ratio-toggle__item-active': seedMode === 'manual' }"
                  @click="seedMode = 'manual'"
                >
                  手动
                </button>
              </div>

              <div v-if="seedMode === 'auto'" class="seed-auto">
                <label class="studio-field">
                  <span>自动种子</span>
                  <div class="seed-auto__row">
                    <input :value="autoSeed" class="field-input field-input-compact seed-auto__value" type="text" readonly />
                    <button type="button" class="btn-ghost btn-sm btn-compact seed-auto__refresh" @click="refreshAutoSeed">换一个</button>
                  </div>
                </label>
                <p class="control-card__hint">自动模式会为本次任务使用随机种子。</p>
              </div>

              <label v-else class="studio-field">
                <span>手动种子</span>
                <input
                  v-model="seedInput"
                  class="field-input field-input-compact"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="输入非负整数"
                  @input="selectedSeedSourceTaskId = ''"
                />
              </label>

              <p v-if="seedMode === 'manual' && seedValidationMessage" class="control-card__error">
                {{ seedValidationMessage }}
              </p>
            </div>
          </section>

          <section class="seed-library">
            <div class="seed-library__head">
              <div>
                <p class="studio-eyebrow">种子库</p>
                <h3>高分复用</h3>
              </div>
              <button
                type="button"
                class="btn-ghost btn-sm btn-compact"
                :disabled="loadingReusableSeeds"
                @click="loadReusableSeeds"
              >
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
                  <span class="surface-chip surface-chip-compact">种子 {{ formatReusableSeed(task.taskSeed) }}</span>
                </div>
                <strong>{{ task.title }}</strong>
                <small>{{ task.aspectRatio || "未知画幅" }} · {{ formatReusableDate(task.ratedAt) || task.status }}</small>
              </button>
            </div>
            <p v-else class="seed-library__empty">当前还没有可复用的历史种子。</p>
          </section>
        </div>

        <div class="core-footer">
          <div class="core-actions">
            <button class="btn-primary btn-compact core-actions__primary" type="submit" :disabled="submitting || !isFormReady || loadingOptions">{{ submitLabel }}</button>
            <button class="btn-secondary btn-compact" type="button" :disabled="submitting" @click="goToTasks">查看任务</button>
            <button class="btn-ghost btn-compact" type="button" :disabled="!progressTaskId" @click="goToCurrentTask">打开当前任务</button>
          </div>
        </div>
      </section>

      <section class="studio-section studio-section-trace">
        <div class="studio-section__head">
          <div>
            <p class="studio-eyebrow">实时追踪</p>
            <h2>执行监控</h2>
          </div>
          <span class="surface-chip surface-chip-compact">{{ progressState.status }}</span>
        </div>

        <div class="trace-stats">
          <div class="trace-stat">
            <span>当前阶段</span>
            <strong>{{ progressState.stage }}</strong>
          </div>
          <div class="trace-stat">
            <span>追踪数量</span>
            <strong>{{ progressTraceCount }} 条</strong>
          </div>
          <div class="trace-stat">
            <span>任务编号</span>
            <strong>{{ progressTaskId || "未挂载" }}</strong>
          </div>
          <div class="trace-stat">
            <span>耗时</span>
            <strong>{{ progressElapsedLabel || "等待开始" }}</strong>
          </div>
        </div>

        <div class="trace-ring-shell">
          <div class="trace-ring" :style="{ '--progress': `${progressState.progress}%` }">
            <div class="trace-ring__inner">
              <p>{{ progressState.stage }}</p>
              <strong>{{ progressState.progress }}%</strong>
            </div>
          </div>
          <p v-if="progressElapsedLabel" class="trace-ring__meta">{{ progressElapsedLabel }}</p>
        </div>

        <div v-if="previewOutputUrl" class="trace-preview">
          <p class="trace-preview__title">{{ previewResultTitle }}</p>
          <video :src="previewOutputUrl" controls playsinline preload="metadata"></video>
          <div class="trace-preview__meta">
            <span v-for="item in previewResultMeta" :key="item">{{ item }}</span>
          </div>
          <div v-if="previewDownloadUrl" class="trace-preview__actions">
            <a class="btn-secondary btn-sm btn-compact" :href="previewDownloadUrl" download target="_blank" rel="noopener noreferrer">
              下载最新拼接结果
            </a>
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
          <div v-else class="trace-feed__empty"></div>
        </section>
      </section>
    </form>
  </section>
</template>

<script setup lang="ts">
/**
 * New任务页面组件。
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createGenerationTask, fetchGenerationOptions, fetchTasks, uploadText } from "@/features/generation";
import { requireAuth } from "@/auth/modal";
import AppSelect from "@/components/common/AppSelect.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { useTaskProgress } from "@/components/generate/useTaskProgress";
import HintBell from "@/components/HintBell.vue";
import { formatApiErrorMessage } from "@/utils/api-error";
import { formatVideoSizeLabel } from "@/utils/presentation";
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
const route = useRoute();

const options = ref<GenerationOptionsResponse | null>(null);
const loadingOptions = ref(false);
const submitting = ref(false);
const uploadingText = ref(false);
const statusText = ref("等待填写参数");
const uploadedText = ref<UploadResponse | null>(null);
const textFileInput = ref<HTMLInputElement | null>(null);
const durationLimitMode = ref<"auto" | "manual">("auto");
const manualMaxDurationSeconds = ref("");
const MANUAL_DURATION_MIN_SECONDS = 5;
const MANUAL_DURATION_MAX_SECONDS = 12;
const seedMode = ref<"auto" | "manual">("auto");
const seedInput = ref("");
const autoSeed = ref<number>(createRandomSeed());
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
  aspectRatio: "16:9",
  textAnalysisModel: null,
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

function queryString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function queryAspectRatio(): "9:16" | "16:9" | null {
  const ratio = queryString(route.query.ratio);
  return ratio === "9:16" || ratio === "16:9" ? ratio : null;
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
 * 创建随机种子。
 * @return 处理结果
 */
function createRandomSeed(): number {
  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    return Math.max(1, values[0] % 2147483647);
  }
  return Math.max(1, Math.floor(Math.random() * 2147483647));
}

/**
 * 刷新自动种子。
 */
function refreshAutoSeed() {
  autoSeed.value = createRandomSeed();
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
const textModelSelectOptions = computed<AppSelectOption[]>(() =>
  textModelOptions.value.map((item) => ({
    label: item.label,
    value: item.value,
    description: item.description || "",
  })),
);
const aspectRatioOptions = computed<Array<GenerationAspectRatioOption & { value: CreateGenerationTaskRequest["aspectRatio"] }>>(() => {
  return (options.value?.aspectRatios ?? []).filter(
    (item): item is GenerationAspectRatioOption & { value: CreateGenerationTaskRequest["aspectRatio"] } => {
      return item.value === "9:16" || item.value === "16:9";
    },
  );
});
const imageModelOptions = computed<GenerationTextAnalysisModelInfo[]>(() => options.value?.imageModels ?? []);
const imageModelSelectOptions = computed<AppSelectOption[]>(() =>
  imageModelOptions.value.map((item) => ({
    label: item.label,
    value: item.value,
    description: item.description || "",
  })),
);
const videoModelOptions = computed<GenerationVideoModelInfo[]>(() => options.value?.videoModels ?? []);
const videoModelSelectOptions = computed<AppSelectOption[]>(() =>
  videoModelOptions.value.map((item) => ({
    label: item.label,
    value: item.value,
    description: item.description || "",
  })),
);
const outputCountOptions = computed<number[]>(() => Array.from({ length: 20 }, (_, index) => index + 1));
const outputCountSelectOptions = computed<AppSelectOption[]>(() => [
  { label: "自动", value: "auto" },
  ...outputCountOptions.value.map((item) => ({ label: String(item), value: item })),
]);
const durationLimitModeOptions: AppSelectOption[] = [
  { label: "自动", value: "auto" },
  { label: "手动", value: "manual" },
];
const selectedVideoModelOption = computed<GenerationVideoModelInfo | null>(() => {
  const selectedVideoModel = normalizeModelName(form.value.videoModel);
  if (!selectedVideoModel) {
    return null;
  }
  return (
    videoModelOptions.value.find((item) => normalizeModelName(item.value) === selectedVideoModel) ?? null
  );
});
const selectedImageModelOption = computed<GenerationTextAnalysisModelInfo | null>(() => {
  const selectedImageModel = normalizeModelName(form.value.imageModel);
  if (!selectedImageModel) {
    return null;
  }
  return (
    imageModelOptions.value.find((item) => normalizeModelName(item.value) === selectedImageModel) ?? null
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
const videoSizeSelectOptions = computed<AppSelectOption[]>(() =>
  videoSizeOptions.value.map((item) => ({
    label: formatVideoSizeLabel(item.label || item.value),
    value: item.value,
  })),
);
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
const selectedModelCount = computed(() => {
  return [
    form.value.textAnalysisModel,
    form.value.imageModel,
    form.value.videoModel,
  ].filter(Boolean).length;
});

const transcriptCharacterCount = computed(() => (form.value.transcriptText ?? "").trim().length);

const seedCapabilityHint = computed(() => {
  const imageSupportsSeed = Boolean(selectedImageModelOption.value?.supportsSeed);
  const videoSupportsSeed = Boolean(selectedVideoModelOption.value?.supportsSeed);
  if (imageSupportsSeed && videoSupportsSeed) {
    return "当前图片模型和视频模型都会使用该种子。";
  }
  if (imageSupportsSeed) {
    return "当前图片模型会使用该种子，视频模型未声明支持种子。";
  }
  if (videoSupportsSeed) {
    return "当前视频模型会使用该种子，图片模型未声明支持种子。";
  }
  return "当前所选模型未声明支持种子，保存后仅做任务记录。";
});
const parsedManualSeed = computed(() => parseSeed(seedInput.value));
const seedValidationMessage = computed(() => {
  if (seedMode.value !== "manual") {
    return "";
  }
  if (!seedInput.value.trim()) {
    return "请先填写合法的种子值";
  }
  if (parsedManualSeed.value === null) {
    return "种子需为非负整数";
  }
  return "";
});
const isSeedReady = computed(() => {
  return seedMode.value === "auto" || !seedValidationMessage.value;
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
      form.value.imageModel &&
      form.value.videoModel &&
      isDurationLimitValid.value &&
      isSeedReady.value,
  );
});

const submitLabel = computed(() => {
  if (submitting.value) {
    return "创建中...";
  }
  return isFormReady.value ? "生成视频" : "请先补全任务参数";
});

const progressTraceCount = computed(() => traceEvents.value.length);

const recentTraceEvents = computed(() => {
  return [...traceEvents.value].slice(-6).reverse();
});

const previewOutputUrl = computed(() => {
  const task = progressTaskDetail.value;
  if (!task) {
    return "";
  }
  return task.monitoring?.latestJoinOutputUrl
    || task.monitoring?.latestVideoOutputUrl
    || task.outputs?.[0]?.previewUrl
    || task.outputs?.[0]?.downloadUrl
    || "";
});

const previewPosterUrl = computed(() => "");

const previewDownloadUrl = computed(() => {
  const task = progressTaskDetail.value;
  if (!task) {
    return "";
  }
  return task.monitoring?.latestJoinOutputUrl
    || task.outputs?.[0]?.downloadUrl
    || task.outputs?.[0]?.previewUrl
    || "";
});

const previewResultTitle = computed(() => {
  const task = progressTaskDetail.value;
  if (!task) {
    return "生成结果";
  }
  if (task.monitoring?.latestJoinOutputUrl) {
    return task.status === "COMPLETED" ? "最新拼接成片预览" : "最新拼接结果";
  }
  return task.status === "COMPLETED" ? "生成成片预览" : "首段生成结果";
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
    task.monitoring?.latestJoinName ? `拼接 ${task.monitoring.latestJoinName}` : "",
    task.aspectRatio ? `画幅 ${task.aspectRatio}` : "",
    durationLabel,
    task.outputs?.length ? `输出 ${task.outputs.length} 条` : "",
  ].filter(Boolean);
});

watch(
  seedMode,
  (mode, previousMode) => {
    if (mode !== "auto") {
      return;
    }
    selectedSeedSourceTaskId.value = "";
    if (previousMode !== "auto") {
      refreshAutoSeed();
    }
  },
);

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
    form.value.aspectRatio = queryAspectRatio() || (result.defaultAspectRatio as "9:16" | "16:9" | null) || form.value.aspectRatio;
    form.value.textAnalysisModel = result.defaultTextAnalysisModel || result.textAnalysisModels?.[0]?.value || null;
    form.value.imageModel = result.imageModels?.[0]?.value ?? null;
    form.value.videoModel = result.videoModels?.[0]?.value ?? null;
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
    statusText.value = "参数已加载，已自动选择默认模型";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "加载模型配置失败";
  } finally {
    loadingOptions.value = false;
  }
}

async function loadReusableSeeds() {
  const authenticated = await requireAuth({
    title: "登录后读取种子库",
    message: "高分种子来自你的历史任务，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    reusableSeedError.value = "登录后可读取高分种子。";
    return;
  }
  loadingReusableSeeds.value = true;
  reusableSeedError.value = "";
  try {
    const tasks = await fetchTasks({ sort: "updated_desc" });
    reusableSeedTasks.value = tasks
      .filter((task) => typeof task.taskSeed === "number" && Number.isFinite(task.taskSeed))
      .slice(0, 8);
  } catch (error) {
    reusableSeedError.value = error instanceof Error ? error.message : "读取历史种子失败";
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
  seedMode.value = "manual";
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
  const authenticated = await requireAuth({
    title: "登录后上传文本",
    message: "上传文本会保存到你的生成任务中，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    input.value = "";
    statusText.value = "登录后可继续上传文本。";
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
  if (seedMode.value === "manual" && seedValidationMessage.value) {
    statusText.value = seedValidationMessage.value;
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后创建任务",
    message: "视频生成任务会保存到你的账号下，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    statusText.value = "登录后即可继续创建任务。";
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
      imageModel: form.value.imageModel || null,
      videoModel: form.value.videoModel || null,
      videoSize: form.value.videoSize || null,
      outputCount: form.value.outputCount ?? "auto",
      seed: seedMode.value === "manual" ? parsedManualSeed.value : autoSeed.value,
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
    const message = formatApiErrorMessage(error, "任务创建失败");
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
  min-height: 100%;
  color: var(--text-strong);
}

.task-studio {
  display: grid;
  gap: 36px;
  padding: 72px 48px 56px;
}

.generate-hero {
  display: grid;
  justify-items: center;
  gap: 42px;
}

.generate-hero h1 {
  margin: 0;
  font-size: clamp(1.4rem, 2vw, 1.9rem);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.generate-hero h1 span {
  color: var(--accent-cyan);
}

.composer-card {
  position: relative;
  display: grid;
  gap: 16px;
  width: min(100%, 1204px);
  min-height: 258px;
  padding: 22px 58px 16px 92px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 24px;
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.composer-upload {
  position: absolute;
  left: 24px;
  top: 24px;
  display: grid;
  place-items: center;
  width: 48px;
  height: 64px;
  border: 0;
  border-radius: 2px;
  background: #f0f1f2;
  color: var(--text-muted);
  font-size: 1.5rem;
  transform: rotate(-7deg);
  cursor: pointer;
}

.composer-upload:disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.composer-title,
.composer-main,
.composer-prompt {
  display: grid;
  gap: 6px;
}

.composer-title span,
.composer-main span,
.composer-prompt span {
  color: var(--text-muted);
  font-size: 0.74rem;
  font-weight: 700;
}

.composer-title input,
.composer-main textarea,
.composer-prompt textarea {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-strong);
}

.composer-title input {
  font-size: 1.02rem;
  font-weight: 700;
}

.composer-main textarea {
  min-height: 96px;
  resize: vertical;
  font-size: 0.95rem;
  line-height: 1.7;
}

.composer-prompt textarea {
  min-height: 44px;
  resize: vertical;
  color: var(--text-body);
  line-height: 1.55;
}

.composer-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-top: 6px;
}

.tool-pill {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 9px;
  background: #fff;
  color: var(--text-strong);
  font-size: 0.78rem;
  font-weight: 650;
  cursor: default;
}

.tool-pill-accent {
  color: var(--accent-cyan);
}

.composer-count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.composer-submit {
  position: absolute;
  right: 18px;
  bottom: 16px;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: var(--accent-cyan);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(124, 58, 237, 0.24);
}

.composer-submit:disabled {
  background: #dce0e4;
  cursor: not-allowed;
  box-shadow: none;
}

.composer-submit svg {
  width: 18px;
  height: 18px;
}

.studio-section {
  display: grid;
  gap: 16px;
  width: min(100%, 1204px);
  margin: 0 auto;
}

.studio-section__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.studio-section__head h2,
.control-card__head h3,
.seed-library__head h3,
.trace-feed__head h3 {
  margin: 0.28rem 0 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.studio-eyebrow {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.studio-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr) minmax(260px, 0.85fr);
  gap: 12px;
}

.studio-field {
  display: grid;
  gap: 0.45rem;
}

.studio-field > span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.model-rail {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 20px;
  background: #fff;
}

.model-rail__item {
  display: grid;
  gap: 0.42rem;
}

.model-rail__label {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.control-card,
.seed-library,
.core-status {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 20px;
  background: #fff;
}

.control-card__head,
.seed-library__head,
.trace-feed__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.ratio-toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.ratio-toggle__item {
  min-height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #fff;
  color: var(--text-body);
  font-weight: 700;
}

.ratio-toggle__item-active {
  border-color: rgba(124, 58, 237, 0.22);
  background: rgba(124, 58, 237, 0.08);
  color: var(--accent-cyan);
}

.control-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.control-card__hint {
  margin: -2px 0 0;
  color: var(--text-muted);
  font-size: 0.76rem;
}

.control-card__error {
  margin: 0;
  color: var(--accent-danger);
  font-size: 0.78rem;
}

.seed-control {
  display: grid;
  gap: 10px;
  padding-top: 4px;
}

.seed-control__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.seed-control__head > span:first-child {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.seed-auto {
  display: grid;
  gap: 10px;
}

.seed-auto__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.seed-auto__value {
  flex: 1 1 auto;
}

.seed-auto__refresh {
  flex: 0 0 auto;
}

.seed-library__list {
  display: grid;
  gap: 8px;
  overflow: auto;
}

.seed-library__item {
  display: grid;
  gap: 6px;
  text-align: left;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #f8fafb;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.seed-library__item:hover {
  transform: translateY(-1px);
  border-color: rgba(124, 58, 237, 0.22);
}

.seed-library__item-active {
  border-color: rgba(124, 58, 237, 0.3);
  background: rgba(124, 58, 237, 0.08);
}

.seed-library__item strong {
  color: var(--text-strong);
  font-size: 0.88rem;
}

.seed-library__item small,
.seed-library__empty {
  color: var(--text-muted);
  font-size: 0.76rem;
  line-height: 1.55;
}

.seed-library__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.core-footer {
  display: grid;
  padding-top: 4px;
}

.core-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.core-actions__primary {
  flex: 0 1 320px;
  width: min(100%, 320px);
  max-width: 320px;
}

.core-actions > .btn-secondary,
.core-actions > .btn-ghost {
  flex: 0 0 auto;
}

.studio-section-trace {
  padding-bottom: 16px;
}

.trace-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.trace-stat {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
}

.trace-stat span {
  color: var(--text-muted);
  font-size: 0.68rem;
  letter-spacing: 0.04em;
}

.trace-stat strong {
  color: var(--text-strong);
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.trace-ring-shell {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 2px 0 0;
}

.trace-ring {
  --progress: 0%;
  position: relative;
  width: 160px;
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, #fff 56%, transparent 57%),
    conic-gradient(from 220deg, rgba(15, 20, 25, 0.08) 0 25%, #7c3aed 45%, #6366f1 100%);
  box-shadow: var(--shadow-soft);
}

.trace-ring::before {
  content: "";
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  background:
    conic-gradient(from 220deg, rgba(124, 58, 237, 0.16) 0 var(--progress), rgba(15, 20, 25, 0.05) var(--progress) 100%);
  mask: radial-gradient(farthest-side, transparent calc(100% - 16px), #000 calc(100% - 15px));
}

.trace-ring__inner {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 6px;
  justify-items: center;
  width: 68%;
  text-align: center;
}

.trace-ring__inner p {
  margin: 0;
  color: var(--text-body);
  line-height: 1.45;
}

.trace-ring__inner strong {
  font-size: 2rem;
  line-height: 1;
  letter-spacing: -0.06em;
  color: var(--text-strong);
}

.trace-ring__meta {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.trace-preview {
  display: grid;
  gap: 8px;
  align-content: start;
}

.trace-preview__title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--text-strong);
}

.trace-preview video {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 16px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #eef2f4;
}

.trace-preview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.trace-preview__meta span {
  display: inline-flex;
  padding: 0.25rem 0.58rem;
  border-radius: 999px;
  background: #f3f6f8;
  color: var(--text-muted);
  font-size: 0.7rem;
}

.trace-preview__actions {
  display: flex;
  justify-content: flex-start;
}

.trace-feed {
  display: grid;
  gap: 10px;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
}

.trace-feed__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
  overflow: auto;
}

.trace-feed__item,
.trace-feed__empty {
  padding: 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 20, 25, 0.06);
}

.trace-feed__item p,
.trace-feed__item small {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.trace-feed__item p {
  color: var(--text-strong);
  font-size: 0.76rem;
  line-height: 1.65;
}

.trace-feed__item small {
  display: block;
  margin-top: 0.38rem;
  color: var(--text-muted);
  font-size: 0.68rem;
}

.trace-feed__empty {
  color: var(--text-muted);
  font-size: 0.82rem;
}

@media (max-width: 1180px) {
  .task-studio {
    padding: 44px 22px 42px;
  }

  .studio-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .trace-stats,
  .control-grid {
    grid-template-columns: 1fr;
  }

  .core-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .core-actions__primary {
    width: 100%;
    max-width: none;
  }

  .seed-auto__row {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 640px) {
  .task-studio {
    padding: 28px 14px 34px;
  }

  .composer-card {
    padding: 18px 18px 16px;
  }

  .composer-upload {
    position: static;
    transform: rotate(-7deg);
  }

  .composer-count {
    width: 100%;
    margin-left: 0;
  }

  .core-actions {
    align-items: stretch;
  }

  .core-actions > * {
    width: 100%;
  }
}
</style>

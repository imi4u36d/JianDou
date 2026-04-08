<template>
  <section class="generate-view">
    <header class="hero surface-panel p-6">
      <div>
        <p class="hero-eyebrow">AI One-Click</p>
        <h1>TXT 小说生成视频</h1>
        <p class="hero-description">提示词流程已收敛到小说工作流，本页仅保留 TXT 小说生成能力。</p>
      </div>
    </header>

    <div class="layout-grid">
      <form class="surface-panel novel-form p-6" @submit.prevent="handleNovelSubmit">
        <div class="form-head">
          <div>
            <p class="eyebrow">Novel Mode</p>
            <h2>TXT 小说生成视频</h2>
          </div>
        </div>

        <div v-if="developerModeNotice" class="surface-tile prompt-dev-note p-4">
          {{ developerModeNotice }}
        </div>

        <div class="field-grid">
          <label class="field">
            <span class="field-label">项目标题</span>
            <input v-model="novelForm.title" class="field-input" type="text" placeholder="默认取文件名或小说生成视频" />
          </label>
          <label class="field">
            <span class="field-label">画幅</span>
            <select v-model="novelForm.aspectRatio" class="field-select">
              <option value="9:16">9:16</option>
              <option value="16:9">16:9</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">总时长</span>
            <input
              v-model="novelForm.totalDurationSeconds"
              class="field-input"
              type="number"
              min="6"
              max="90"
              step="1"
              placeholder="留空则按分镜脚本总时长"
            />
            <p class="field-hint">不填写时，默认采用大模型生成的分镜脚本总时长。</p>
          </label>
          <label class="field">
            <span class="field-label">视频模型</span>
            <select v-model="novelForm.providerModel" class="field-select" :disabled="optionsLoading">
              <option v-for="item in availableNovelVideoModels" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
            <p v-if="selectedNovelVideoModel?.description" class="field-hint">
              {{ selectedNovelVideoModel.description }}
            </p>
          </label>
          <label class="field">
            <span class="field-label">分辨率</span>
            <select v-model="novelForm.videoSize" class="field-select" :disabled="optionsLoading">
              <option v-for="item in availableNovelVideoSizes" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
            <p class="field-hint">按当前视频模型过滤可用分辨率。</p>
          </label>
          <label class="field">
            <span class="field-label">文本分析模型</span>
            <select v-model="novelForm.textAnalysisModel" class="field-select" :disabled="optionsLoading">
              <option v-for="item in availableTextAnalysisModels" :key="item.value" :value="item.value">
                {{ item.label }}{{ item.description ? ` · ${item.description}` : "" }}
              </option>
            </select>
            <TextModelProbeInline
              ref="novelTextModelProbeRef"
              :model-value="novelForm.textAnalysisModel"
              :disabled="optionsLoading || submitting"
            />
          </label>
        </div>

        <div class="model-inline">
          <span>{{ selectedNovelVideoModel?.label || novelForm.providerModel || "未选视频模型" }}</span>
          <span v-if="selectedNovelVideoModel?.provider">{{ selectedNovelVideoModel.provider }}</span>
          <span>{{ novelForm.videoSize || "未选分辨率" }}</span>
          <span>{{ novelForm.aspectRatio }}</span>
        </div>

        <label class="upload-box">
          <input type="file" accept=".txt,text/plain" class="hidden-input" @change="handleNovelFileChange" />
          <span class="upload-box-title">{{ novelForm.fileName || "上传 TXT 文件" }}</span>
          <span class="upload-box-meta">{{ novelStats }}</span>
        </label>

        <label class="field">
          <span class="field-label">小说正文</span>
          <textarea
            v-model="novelForm.text"
            rows="12"
            class="field-textarea"
            placeholder="上传 TXT 后会自动填入，也可以直接粘贴小说正文。"
          ></textarea>
        </label>

        <div v-if="submitError" class="surface-tile rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-700">
          {{ submitError }}
        </div>

        <button type="submit" class="btn-primary submit-btn justify-center" :disabled="!canSubmitNovel">
          {{ submitting ? "生成中..." : "生成小说视频" }}
        </button>
      </form>

      <TaskProgressCard
        :state="progressCardState"
        :task-id="progressTaskId"
        :trace-count="progressTraceCount"
        :result-title="previewResultTitle"
        :result-meta="previewResultMeta"
        :output-url="previewOutputUrl"
        :poster-url="previewPosterUrl"
      />
    </div>

    <section v-if="stoppedBeforeVideoGeneration" class="surface-panel prompt-review p-6">
      <header class="prompt-review__head">
        <div>
          <p class="eyebrow">Developer Review</p>
          <h2>视频模型脚本检查</h2>
        </div>
        <span class="prompt-review__badge">已在视频模型前停止</span>
      </header>
      <p class="prompt-review__summary">
        {{ aiDramaDetail?.summary || "本次运行已暂停在视频生成前，可先检查每个镜头将发送给视频模型的 prompt。" }}
      </p>
      <div class="prompt-review__meta">
        <span v-for="item in preparedShotMeta" :key="item">{{ item }}</span>
      </div>
      <div class="prompt-review__list">
        <article v-for="shot in preparedShots" :key="shot.shotNo" class="prompt-review__item">
          <div class="prompt-review__item-head">
            <strong>{{ shot.shotNo }}</strong>
            <span>{{ shot.shotType || "镜头" }}</span>
            <span v-if="shot.durationSeconds !== null">{{ shot.durationSeconds }}s</span>
          </div>
          <p class="prompt-review__prompt">{{ shot.prompt }}</p>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { fetchGenerationOptions, fetchVideoModelUsage } from "@/api/generation";
import { fetchAgentRun, fetchAgentRuns, getPersistedRuns, runAIDramaAgent, runVisualAgent } from "@/api/agents";
import { getRuntimeConfig } from "@/api/runtime-config";
import { progressStateFromAgentRun, mediaResultFromAgentRun, isAgentRunActive } from "@/utils/agent-run";
import { resolveRuntimeUrl } from "@/utils/url";
import type {
  AgentRunDetail,
  GenerateMediaResponse,
  GenerationOptionsResponse,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
  VideoModelUsageItem,
} from "@/types";
import GenerateFormCard from "@/components/generate/GenerateFormCard.vue";
import TaskProgressCard from "@/components/generate/TaskProgressCard.vue";
import TextModelProbeInline from "@/components/TextModelProbeInline.vue";
import { useTaskProgress } from "@/components/generate/useTaskProgress";
import type { GenerateFormModel, TaskProgressState } from "@/components/generate/types";
import { loadDeveloperSettings, subscribeDeveloperSettings, type DeveloperSettings } from "@/workbench/developer-settings";

type GenerateMode = "prompt" | "novel";

const ACTIVE_RUN_STORAGE_KEY = "ai-cut:generate-view:active-run";
const MAX_PERSISTED_NOVEL_TEXT_LENGTH = 12000;

interface PreparedShotPreview {
  shotNo: string;
  shotType: string;
  durationSeconds: number | null;
  prompt: string;
}

interface PromptFormSnapshot {
  prompt: string;
  textAnalysisModel: string;
  providerModel: string;
  videoSize: string;
  minDurationSeconds: string;
  maxDurationSeconds: string;
}

interface NovelFormSnapshot {
  title: string;
  fileName: string;
  text: string;
  textAnalysisModel: string;
  aspectRatio: "9:16" | "16:9";
  totalDurationSeconds: string;
  providerModel: string;
  videoSize: string;
}

interface TaskProgressSnapshot {
  status: TaskProgressState["status"];
  progress: number;
  stage: string;
  message: string;
  updatedAt: string;
}

interface GenerateViewActiveRunState {
  mode: GenerateMode;
  runId: string;
  promptForm: PromptFormSnapshot;
  novelForm: NovelFormSnapshot;
  novelProgress: TaskProgressSnapshot | null;
}

const fallbackOptions: GenerationOptionsResponse = {
  versions: [],
  stylePresets: [],
  imageSizes: [],
  textAnalysisModels: [
    { value: "gpt-5.4", label: "GPT-5.4", isDefault: true, provider: "chatgpt", family: "gpt" },
    { value: "qwen3.6-plus", label: "Qwen 3.6 Plus", provider: "qwen", family: "qwen" },
  ],
  defaultTextAnalysisModel: "gpt-5.4",
  videoModels: [],
  defaultVideoModel: "",
  videoSizes: [
    { value: "1080x1920", label: "1080 × 1920", width: 1080, height: 1920 },
    { value: "1920x1080", label: "1920 × 1080", width: 1920, height: 1080 },
  ],
  videoDurations: [
    { value: 5, label: "5 秒" },
    { value: 10, label: "10 秒" },
  ],
  defaultVideoSize: "1080x1920",
};

const generateMode = ref<GenerateMode>("novel");
const options = ref<GenerationOptionsResponse>(fallbackOptions);
const optionsLoading = ref(true);
const optionsError = ref("");
const submitError = ref("");
const submitting = ref(false);
const result = ref<GenerateMediaResponse | null>(null);
const aiDramaDetail = ref<AgentRunDetail | null>(null);
const promptRun = ref<AgentRunDetail | null>(null);
const promptProgressState = ref<TaskProgressState>(
  progressStateFromAgentRun(null, "提交参数后将开始生成视频。")
);
const usageVisible = ref(false);
const usageLoading = ref(false);
const usageError = ref("");
const usageRows = ref<VideoModelUsageItem[]>([]);
const developerSettings = ref<DeveloperSettings>(loadDeveloperSettings());
const promptFormRef = ref<{ ensureTextModelReady: () => Promise<boolean> } | null>(null);
const novelTextModelProbeRef = ref<{ ensureReady: (force?: boolean) => Promise<boolean> } | null>(null);

const form = reactive<GenerateFormModel>({
  prompt: "",
  textAnalysisModel: fallbackOptions.defaultTextAnalysisModel || fallbackOptions.textAnalysisModels?.[0]?.value || "gpt-5.4",
  providerModel: "",
  videoSize: "1080x1920",
  minDurationSeconds: "",
  maxDurationSeconds: "",
});

const novelForm = reactive({
  title: "",
  text: "",
  fileName: "",
  textFile: null as File | null,
  uploadedTextSnapshot: "",
  textAnalysisModel: fallbackOptions.defaultTextAnalysisModel || fallbackOptions.textAnalysisModels?.[0]?.value || "gpt-5.4",
  aspectRatio: "9:16" as "9:16" | "16:9",
  totalDurationSeconds: "",
  providerModel: fallbackOptions.defaultVideoModel || fallbackOptions.videoModels[0]?.value || "",
  videoSize: fallbackOptions.defaultVideoSize || fallbackOptions.videoSizes[0]?.value || "1080x1920",
});

const {
  state: progressState,
  reset: resetProgress,
  start: startProgress,
  complete,
  fail,
} = useTaskProgress();

let promptRunPollTimer: number | null = null;
let novelRunPollTimer: number | null = null;

const availableAllVideoModels = computed<GenerationVideoModelInfo[]>(() => {
  const source = options.value.videoModels.length ? options.value.videoModels : fallbackOptions.videoModels;
  return source;
});

const availablePromptVideoModels = computed<GenerationVideoModelInfo[]>(() => {
  const source = availableAllVideoModels.value;
  const filtered = source.filter((item) => item.generationMode !== "i2v");
  return filtered.length ? filtered : source;
});

const availableNovelVideoModels = computed<GenerationVideoModelInfo[]>(() => {
  return availableAllVideoModels.value;
});

const availableTextAnalysisModels = computed<GenerationTextAnalysisModelInfo[]>(() => {
  return options.value.textAnalysisModels?.length ? options.value.textAnalysisModels : (fallbackOptions.textAnalysisModels || []);
});

const selectedVideoModel = computed<GenerationVideoModelInfo | null>(() => {
  return availablePromptVideoModels.value.find((item) => item.value === form.providerModel) ?? null;
});

const selectedNovelVideoModel = computed<GenerationVideoModelInfo | null>(() => {
  return availableNovelVideoModels.value.find((item) => item.value === novelForm.providerModel) ?? null;
});

function filterVideoSizesByModel(providerModel: string, modelOptions: GenerationVideoModelInfo[]): GenerationVideoSizeOption[] {
  const source = options.value.videoSizes.length ? options.value.videoSizes : fallbackOptions.videoSizes;
  const bySize = source.filter((size) => {
    if (!size.supportedModels?.length) {
      return true;
    }
    return size.supportedModels.includes(providerModel);
  });
  const model = modelOptions.find((item) => item.value === providerModel);
  const byModel = model?.supportedSizes?.length
    ? bySize.filter((item) => model.supportedSizes?.includes(item.value))
    : bySize;
  return byModel.length ? byModel : source;
}

function filterVideoDurationsByModel(providerModel: string): GenerationVideoDurationOption[] {
  const source = options.value.videoDurations.length ? options.value.videoDurations : fallbackOptions.videoDurations;
  const byDuration = source.filter((duration) => {
    if (!duration.supportedModels?.length) {
      return true;
    }
    return duration.supportedModels.includes(providerModel);
  });
  const model = availablePromptVideoModels.value.find((item) => item.value === providerModel);
  const byModel = model?.supportedDurations?.length
    ? byDuration.filter((item) => model.supportedDurations?.includes(item.value))
    : byDuration;
  return byModel.length ? byModel : source;
}

const availableVideoSizes = computed<GenerationVideoSizeOption[]>(() =>
  filterVideoSizesByModel(form.providerModel, availablePromptVideoModels.value)
);

const availableNovelVideoSizes = computed<GenerationVideoSizeOption[]>(() =>
  filterVideoSizesByModel(novelForm.providerModel, availableNovelVideoModels.value)
);

const availableVideoDurations = computed<GenerationVideoDurationOption[]>(() => filterVideoDurationsByModel(form.providerModel));

const canSubmitPrompt = computed(() => {
  return (
    Boolean(form.prompt.trim()) &&
    Boolean(form.providerModel) &&
    !optionsLoading.value &&
    !submitting.value &&
    !isAgentRunActive(promptRun.value)
  );
});

const canSubmitNovel = computed(() => {
  return Boolean(novelForm.text.trim()) && Boolean(novelForm.providerModel) && !submitting.value && !isAgentRunActive(aiDramaDetail.value);
});

const novelStats = computed(() => {
  const length = novelForm.text.trim().length;
  if (novelForm.fileName && length) {
    return `${novelForm.fileName} · ${length.toLocaleString("zh-CN")} 字`;
  }
  if (novelForm.fileName) {
    return novelForm.fileName;
  }
  if (length) {
    return `${length.toLocaleString("zh-CN")} 字`;
  }
  return "支持上传后自动读取，也可直接粘贴正文";
});

const progressTaskId = computed(() => aiDramaDetail.value?.id || "");

const progressTraceCount = computed(() => aiDramaDetail.value?.events.length || 0);

const progressCardState = computed(() =>
  aiDramaDetail.value
    ? progressStateFromAgentRun(aiDramaDetail.value, "提交小说内容后将开始生成视频。")
    : progressState.value
);

const previewOutputUrl = computed(() => {
  const videoUrl = extractAiDramaVideoUrl(aiDramaDetail.value);
  return videoUrl ? resolveRuntimeUrl(videoUrl, getRuntimeConfig().storageBaseUrl) : "";
});

const previewPosterUrl = computed(() => "");

const previewResultTitle = computed(() => {
  if (stoppedBeforeVideoGeneration.value) {
    return "视频模型脚本预览";
  }
  return aiDramaDetail.value ? "小说生成成片" : "生成结果";
});

const previewResultMeta = computed(() => {
  const output = aiDramaDetail.value?.output || {};
  return [
    asString(output.providerModel),
    asString(output.videoSize),
    asString(output.aspectRatio),
    asNumber(output.shotCount) ? `${asNumber(output.shotCount)} 镜头` : "",
    asNumber(output.durationSeconds) ? `${asNumber(output.durationSeconds)}s` : "",
    asNumber(output.totalDurationSeconds) ? `${asNumber(output.totalDurationSeconds)}s` : "",
    asString(output.visualStyle),
  ].filter(Boolean);
});

const stoppedBeforeVideoGeneration = computed(() => {
  return Boolean(aiDramaDetail.value?.output.stoppedBeforeVideoGeneration);
});

const preparedShots = computed<PreparedShotPreview[]>(() => {
  const raw = aiDramaDetail.value?.output.preparedShots;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .map((item) => normalizePreparedShot(item))
    .filter((item): item is PreparedShotPreview => item !== null);
});

const preparedShotMeta = computed(() => {
  const shotCount = preparedShots.value.length;
  if (!shotCount) {
    return [];
  }
  const durations = preparedShots.value
    .map((item) => item.durationSeconds)
    .filter((item): item is number => typeof item === "number" && Number.isFinite(item));
  const totalDuration = durations.reduce((sum, item) => sum + item, 0);
  return [
    `${shotCount} 个镜头`,
    totalDuration > 0 ? `预计 ${totalDuration.toFixed(1)}s` : "",
    "未调用视频模型",
  ].filter(Boolean);
});

const developerModeNotice = computed(() => {
  if (!developerSettings.value.enabled) {
    return "";
  }
  if (developerSettings.value.stopBeforeVideoGeneration) {
    return "开发者模式已开启：本次小说生成会在调用视频模型前停止，并返回逐镜头脚本供检查。";
  }
  return "开发者模式已开启：当前不会提前停止任务。";
});

watch(
  () => novelForm.providerModel,
  () => {
    const firstSize = availableNovelVideoSizes.value[0];
    if (!availableNovelVideoSizes.value.some((item) => item.value === novelForm.videoSize)) {
      novelForm.videoSize = firstSize?.value || "";
    }
  }
);

function pickDefaultPromptVideoModel(nextOptions: GenerationOptionsResponse) {
  const available = (nextOptions.videoModels.length ? nextOptions.videoModels : fallbackOptions.videoModels).filter(
    (item) => item.generationMode !== "i2v"
  );
  return (
    available.find((item) => item.value === nextOptions.defaultVideoModel)?.value ||
    available.find((item) => item.isDefault)?.value ||
    available[0]?.value ||
    ""
  );
}

function pickDefaultNovelVideoModel(nextOptions: GenerationOptionsResponse) {
  const available = nextOptions.videoModels.length ? nextOptions.videoModels : fallbackOptions.videoModels;
  return (
    available.find((item) => item.value === nextOptions.defaultVideoModel)?.value ||
    available.find((item) => item.isDefault)?.value ||
    available[0]?.value ||
    ""
  );
}

function pickDefaultTextAnalysisModel(nextOptions: GenerationOptionsResponse) {
  return (
    nextOptions.defaultTextAnalysisModel ||
    nextOptions.textAnalysisModels?.find((item) => item.isDefault)?.value ||
    nextOptions.textAnalysisModels?.[0]?.value ||
    fallbackOptions.defaultTextAnalysisModel ||
    fallbackOptions.textAnalysisModels?.[0]?.value ||
    "gpt-5.4"
  );
}

function pickVideoSizeForModel(nextOptions: GenerationOptionsResponse, providerModel: string, currentValue = "") {
  const modelOptions = (nextOptions.videoModels.length ? nextOptions.videoModels : fallbackOptions.videoModels).length
    ? nextOptions.videoModels.length
      ? nextOptions.videoModels
      : fallbackOptions.videoModels
    : fallbackOptions.videoModels;
  const sizeOptions = filterVideoSizesByModel(providerModel, modelOptions);
  return (
    sizeOptions.find((item) => item.value === currentValue)?.value ||
    sizeOptions.find((item) => item.value === nextOptions.defaultVideoSize)?.value ||
    sizeOptions[0]?.value ||
    fallbackOptions.videoSizes[0].value
  );
}

function applyOptionDefaults(nextOptions: GenerationOptionsResponse) {
  const defaultTextAnalysisModel = pickDefaultTextAnalysisModel(nextOptions);
  const defaultNovelVideoModel = pickDefaultNovelVideoModel(nextOptions);
  novelForm.textAnalysisModel =
    availableTextAnalysisModels.value.find((item) => item.value === novelForm.textAnalysisModel)?.value ||
    defaultTextAnalysisModel;
  novelForm.providerModel =
    availableNovelVideoModels.value.find((item) => item.value === novelForm.providerModel)?.value ||
    defaultNovelVideoModel;
  novelForm.videoSize = pickVideoSizeForModel(nextOptions, novelForm.providerModel, novelForm.videoSize);
}

async function loadOptions() {
  optionsLoading.value = true;
  optionsError.value = "";
  try {
    const fetched = await fetchGenerationOptions();
    options.value = fetched;
    applyOptionDefaults(fetched);
  } catch (error) {
    options.value = fallbackOptions;
    applyOptionDefaults(fallbackOptions);
    optionsError.value = error instanceof Error ? error.message : "加载参数失败。";
  } finally {
    optionsLoading.value = false;
  }
}

function truncatePersistedNovelText(value: unknown) {
  const normalized = typeof value === "string" ? value : "";
  if (normalized.length <= MAX_PERSISTED_NOVEL_TEXT_LENGTH) {
    return normalized;
  }
  return normalized.slice(0, MAX_PERSISTED_NOVEL_TEXT_LENGTH);
}

function snapshotTaskProgress(state: TaskProgressState): TaskProgressSnapshot {
  return {
    status: state.status,
    progress: Math.max(0, Math.min(100, Math.round(state.progress))),
    stage: state.stage || "",
    message: state.message || "",
    updatedAt: state.updatedAt || "",
  };
}

function normalizeTaskProgressSnapshot(value: unknown): TaskProgressSnapshot | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const statusRaw = asString(record.status).toLowerCase();
  const status: TaskProgressState["status"] =
    statusRaw === "running" || statusRaw === "completed" || statusRaw === "failed" || statusRaw === "idle"
      ? statusRaw
      : "idle";
  const progress = asNumber(record.progress);
  return {
    status,
    progress: Math.max(0, Math.min(100, Math.round(progress ?? 0))),
    stage: asString(record.stage),
    message: asString(record.message),
    updatedAt: asString(record.updatedAt),
  };
}

function snapshotPromptForm(): PromptFormSnapshot {
  return {
    prompt: form.prompt,
    textAnalysisModel: form.textAnalysisModel,
    providerModel: form.providerModel,
    videoSize: form.videoSize,
    minDurationSeconds: form.minDurationSeconds,
    maxDurationSeconds: form.maxDurationSeconds,
  };
}

function snapshotNovelForm(): NovelFormSnapshot {
  return {
    title: novelForm.title,
    fileName: novelForm.fileName,
    text: truncatePersistedNovelText(novelForm.text),
    textAnalysisModel: novelForm.textAnalysisModel,
    aspectRatio: novelForm.aspectRatio,
    totalDurationSeconds: novelForm.totalDurationSeconds,
    providerModel: novelForm.providerModel,
    videoSize: novelForm.videoSize,
  };
}

function persistActiveRunState(mode: GenerateMode, runId = "") {
  const payload: GenerateViewActiveRunState = {
    mode,
    runId,
    promptForm: snapshotPromptForm(),
    novelForm: snapshotNovelForm(),
    novelProgress: mode === "novel" ? snapshotTaskProgress(progressCardState.value) : null,
  };
  try {
    window.localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore persistence failures.
  }
}

function readActiveRunState(): GenerateViewActiveRunState | null {
  try {
    const raw = window.localStorage.getItem(ACTIVE_RUN_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<GenerateViewActiveRunState>;
    if (parsed.mode !== "prompt" && parsed.mode !== "novel") {
      return null;
    }
    return {
      mode: parsed.mode,
      runId: typeof parsed.runId === "string" ? parsed.runId.trim() : "",
      promptForm: {
        prompt: parsed.promptForm?.prompt ?? "",
        textAnalysisModel: parsed.promptForm?.textAnalysisModel ?? "",
        providerModel: parsed.promptForm?.providerModel ?? "",
        videoSize: parsed.promptForm?.videoSize ?? "",
        minDurationSeconds: parsed.promptForm?.minDurationSeconds ?? "",
        maxDurationSeconds: parsed.promptForm?.maxDurationSeconds ?? "",
      },
      novelForm: {
        title: parsed.novelForm?.title ?? "",
        fileName: parsed.novelForm?.fileName ?? "",
        text: truncatePersistedNovelText(parsed.novelForm?.text ?? ""),
        textAnalysisModel: parsed.novelForm?.textAnalysisModel ?? "",
        aspectRatio: parsed.novelForm?.aspectRatio === "16:9" ? "16:9" : "9:16",
        totalDurationSeconds: parsed.novelForm?.totalDurationSeconds ?? "",
        providerModel: parsed.novelForm?.providerModel ?? "",
        videoSize: parsed.novelForm?.videoSize ?? "",
      },
      novelProgress: normalizeTaskProgressSnapshot(parsed.novelProgress),
    };
  } catch {
    return null;
  }
}

function clearPersistedActiveRunState() {
  try {
    window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  } catch {
    // Ignore persistence failures.
  }
}

function applyPromptSnapshot(snapshot: PromptFormSnapshot) {
  form.prompt = snapshot.prompt || form.prompt;
  form.textAnalysisModel = snapshot.textAnalysisModel || form.textAnalysisModel;
  form.providerModel = snapshot.providerModel || form.providerModel;
  form.videoSize = snapshot.videoSize || form.videoSize;
  form.minDurationSeconds = snapshot.minDurationSeconds ?? form.minDurationSeconds;
  form.maxDurationSeconds = snapshot.maxDurationSeconds ?? form.maxDurationSeconds;
}

function applyNovelSnapshot(snapshot: NovelFormSnapshot) {
  novelForm.title = snapshot.title || novelForm.title;
  novelForm.fileName = snapshot.fileName || novelForm.fileName;
  if (snapshot.text && !novelForm.text.trim()) {
    novelForm.text = snapshot.text;
  }
  novelForm.textAnalysisModel = snapshot.textAnalysisModel || novelForm.textAnalysisModel;
  novelForm.aspectRatio = snapshot.aspectRatio || novelForm.aspectRatio;
  novelForm.totalDurationSeconds = snapshot.totalDurationSeconds || novelForm.totalDurationSeconds;
  novelForm.providerModel = snapshot.providerModel || novelForm.providerModel;
  novelForm.videoSize = snapshot.videoSize || novelForm.videoSize;
}

function applyNovelProgressSnapshot(snapshot: TaskProgressSnapshot | null) {
  if (!snapshot) {
    return;
  }
  progressState.value = {
    ...progressState.value,
    ...snapshot,
  };
}

function restorePersistedDrafts() {
  const state = readActiveRunState();
  if (!state) {
    return null;
  }
  generateMode.value = state.mode;
  if (state.mode === "prompt") {
    applyPromptSnapshot(state.promptForm);
  } else {
    applyNovelSnapshot(state.novelForm);
    applyNovelProgressSnapshot(state.novelProgress);
  }
  return state;
}

function getPersistedRun(runId: string) {
  return getPersistedRuns().find((item) => item.id === runId) ?? null;
}

function stopPromptRunPolling() {
  if (promptRunPollTimer !== null) {
    window.clearInterval(promptRunPollTimer);
    promptRunPollTimer = null;
  }
}

function stopNovelRunPolling() {
  if (novelRunPollTimer !== null) {
    window.clearInterval(novelRunPollTimer);
    novelRunPollTimer = null;
  }
}

function syncPromptRun(run: AgentRunDetail) {
  promptRun.value = run;
  promptProgressState.value = progressStateFromAgentRun(run, "提交参数后将开始生成视频。");
  if (run.status === "failed") {
    submitError.value = run.summary || "视频生成失败，请稍后重试。";
    clearPersistedActiveRunState();
    stopPromptRunPolling();
    return;
  }
  if (run.status === "completed") {
    const nextResult = mediaResultFromAgentRun(run);
    result.value = nextResult;
    if (!nextResult) {
      submitError.value = "任务已完成，但未返回视频文件。";
    }
    clearPersistedActiveRunState();
    stopPromptRunPolling();
    return;
  }
  persistActiveRunState("prompt", run.id);
}

async function refreshPromptRun(runId: string) {
  try {
    const run = await fetchAgentRun(runId);
    syncPromptRun(run);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "同步视频任务状态失败";
  }
}

function startPromptRunPolling(runId: string) {
  stopPromptRunPolling();
  void refreshPromptRun(runId);
  promptRunPollTimer = window.setInterval(() => {
    void refreshPromptRun(runId);
  }, 2000);
}

function syncNovelRun(run: AgentRunDetail) {
  aiDramaDetail.value = run;
  if (run.status === "failed") {
    submitError.value = run.summary || "小说视频生成失败，请稍后重试。";
    clearPersistedActiveRunState();
    stopNovelRunPolling();
    return;
  }
  if (run.status === "completed") {
    clearPersistedActiveRunState();
    stopNovelRunPolling();
    return;
  }
  persistActiveRunState("novel", run.id);
}

async function refreshNovelRun(runId: string) {
  try {
    const run = await fetchAgentRun(runId);
    syncNovelRun(run);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "同步小说任务状态失败";
  }
}

function startNovelRunPolling(runId: string) {
  stopNovelRunPolling();
  void refreshNovelRun(runId);
  novelRunPollTimer = window.setInterval(() => {
    void refreshNovelRun(runId);
  }, 2000);
}

function hydratePromptFormFromRun(run: AgentRunDetail) {
  form.prompt = asString(run.input.prompt) || form.prompt;
  form.textAnalysisModel = asString(run.input.textAnalysisModel) || form.textAnalysisModel;
  form.providerModel = asString(run.input.providerModel) || form.providerModel;
  form.videoSize = asString(run.input.videoSize) || form.videoSize;
  const minDurationSeconds = asNumber(run.input.minDurationSeconds);
  const maxDurationSeconds = asNumber(run.input.maxDurationSeconds) ?? asNumber(run.input.durationSeconds);
  form.minDurationSeconds = minDurationSeconds !== null ? `${minDurationSeconds}` : form.minDurationSeconds;
  form.maxDurationSeconds = maxDurationSeconds !== null ? `${maxDurationSeconds}` : form.maxDurationSeconds;
}

function hydrateNovelFormFromRun(run: AgentRunDetail) {
  novelForm.title = asString(run.input.title) || novelForm.title;
  novelForm.fileName = asString(run.input.textFileName) || novelForm.fileName;
  novelForm.textAnalysisModel = asString(run.input.textAnalysisModel) || novelForm.textAnalysisModel;
  novelForm.aspectRatio = asString(run.input.aspectRatio) === "16:9" ? "16:9" : novelForm.aspectRatio;
  novelForm.providerModel = asString(run.input.providerModel) || novelForm.providerModel;
  novelForm.videoSize = asString(run.input.videoSize) || novelForm.videoSize;
  const inputText = asString(run.input.text);
  if (inputText && !novelForm.text.trim()) {
    novelForm.text = inputText;
  }
  const totalDurationSeconds = asNumber(run.input.totalDurationSeconds);
  if (totalDurationSeconds !== null) {
    novelForm.totalDurationSeconds = `${totalDurationSeconds}`;
  }
}

function restoreRunById(mode: GenerateMode, runId: string) {
  if (!runId) {
    return false;
  }
  const cached = getPersistedRun(runId);
  if (cached) {
    if (mode === "prompt") {
      hydratePromptFormFromRun(cached);
      syncPromptRun(cached);
      if (isAgentRunActive(cached)) {
        startPromptRunPolling(runId);
      } else {
        void refreshPromptRun(runId);
      }
    } else {
      hydrateNovelFormFromRun(cached);
      syncNovelRun(cached);
      if (isAgentRunActive(cached)) {
        startNovelRunPolling(runId);
      } else {
        void refreshNovelRun(runId);
      }
    }
    return true;
  }
  if (mode === "prompt") {
    startPromptRunPolling(runId);
  } else {
    startNovelRunPolling(runId);
  }
  return true;
}

async function restoreLatestActiveRun(preferredMode?: GenerateMode, allowCrossMode = true) {
  try {
    const [promptRuns, novelRuns] = await Promise.all([
      fetchAgentRuns("visual-lab"),
      fetchAgentRuns("ai-drama"),
    ]);
    const activeCandidates = [
      ...promptRuns
        .filter((item) => item.status === "queued" || item.status === "running")
        .map((item) => ({ mode: "prompt" as const, createdAt: item.createdAt, runId: item.id })),
      ...novelRuns
        .filter((item) => item.status === "queued" || item.status === "running")
        .map((item) => ({ mode: "novel" as const, createdAt: item.createdAt, runId: item.id })),
    ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
    const candidate = preferredMode
      ? activeCandidates.find((item) => item.mode === preferredMode) || (allowCrossMode ? activeCandidates[0] : null)
      : activeCandidates[0];
    if (!candidate) {
      return;
    }
    generateMode.value = candidate.mode;
    persistActiveRunState(candidate.mode, candidate.runId);
    restoreRunById(candidate.mode, candidate.runId);
  } catch {
    // Ignore auto-restore failures.
  }
}

function extractAiDramaVideoUrl(detail: AgentRunDetail | null) {
  if (!detail) {
    return "";
  }
  const outputUrl = asString(detail.output.finalVideoUrl);
  if (outputUrl) {
    return outputUrl;
  }
  const artifactUrl = detail.artifacts.find((item) => item.kind === "stitched-video")?.url || "";
  return artifactUrl;
}

function modelLabel(modelValue: string) {
  const usageLabel = usageRows.value.find((item) => item.model === modelValue)?.label;
  return usageLabel || availableAllVideoModels.value.find((item) => item.value === modelValue)?.label || modelValue;
}

function formatAmount(value: number | null | undefined, unit?: string | null, label?: string | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "未设置";
  }
  const normalized = value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  const suffix = [label, unit].filter(Boolean).join(" ");
  return suffix ? `${normalized} ${suffix}` : normalized;
}

function parseOptionalDuration(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }
  return parsed;
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function normalizePreparedShot(value: unknown): PreparedShotPreview | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const prompt = asString(record.prompt);
  const shotNo = asString(record.shotNo) || asString(record.shot_no);
  if (!prompt || !shotNo) {
    return null;
  }
  return {
    shotNo,
    shotType: asString(record.shotType) || asString(record.shot_type),
    durationSeconds: asNumber(record.durationSeconds) ?? asNumber(record.duration_seconds),
    prompt,
  };
}

function defaultNovelTitle() {
  return novelForm.title.trim() || novelForm.fileName.replace(/\.[^.]+$/, "").trim() || "小说生成视频";
}

async function loadUsage() {
  usageLoading.value = true;
  usageError.value = "";
  try {
    const response = await fetchVideoModelUsage();
    usageRows.value = response.items;
  } catch (error) {
    usageRows.value = [];
    usageError.value = error instanceof Error ? error.message : "读取模型用量失败";
  } finally {
    usageLoading.value = false;
  }
}

async function openUsagePanel() {
  usageVisible.value = true;
  if (!usageRows.value.length && !usageLoading.value) {
    await loadUsage();
  }
}

async function handlePromptSubmit() {
  submitError.value = "";
  aiDramaDetail.value = null;
  promptRun.value = null;
  result.value = null;
  clearPersistedActiveRunState();
  stopPromptRunPolling();
  stopNovelRunPolling();
  promptProgressState.value = {
    status: "running",
    progress: 8,
    stage: "提交生成请求",
    message: "正在创建异步视频任务...",
    updatedAt: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
  };
  if (!form.prompt.trim()) {
    submitError.value = "请输入视频提示词。";
    return;
  }
  const minDurationSeconds = parseOptionalDuration(form.minDurationSeconds);
  const maxDurationSeconds = parseOptionalDuration(form.maxDurationSeconds);
  if (minDurationSeconds !== undefined && minDurationSeconds <= 0) {
    submitError.value = "最小时长必须大于 0。";
    return;
  }
  if (maxDurationSeconds !== undefined && maxDurationSeconds <= 0) {
    submitError.value = "最大时长必须大于 0。";
    return;
  }
  if (minDurationSeconds !== undefined && maxDurationSeconds !== undefined && minDurationSeconds > maxDurationSeconds) {
    submitError.value = "最小时长不能大于最大时长。";
    return;
  }
  const modelReady = await promptFormRef.value?.ensureTextModelReady();
  if (modelReady === false) {
    submitError.value = "所选文本模型测试未通过，请先检查配置或切换模型。";
    return;
  }
  submitting.value = true;
  persistActiveRunState("prompt");
  try {
    const run = await runVisualAgent("visual-lab", {
      prompt: form.prompt.trim(),
      mediaKind: "video",
      textAnalysisModel: form.textAnalysisModel,
      stylePreset: "",
      providerModel: form.providerModel,
      imageSize: "",
      videoSize: form.videoSize,
      videoDurationSeconds: maxDurationSeconds ?? minDurationSeconds ?? 5,
      minDurationSeconds,
      maxDurationSeconds,
    });
    syncPromptRun(run);
    if (isAgentRunActive(run)) {
      startPromptRunPolling(run.id);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "视频生成失败，请稍后重试。";
    submitError.value = message;
    promptProgressState.value = {
      status: "failed",
      progress: Math.max(promptProgressState.value.progress, 1),
      stage: "任务失败",
      message,
      updatedAt: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    };
  } finally {
    submitting.value = false;
  }
}

async function handleNovelFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (!file) {
    return;
  }
  try {
    novelForm.fileName = file.name;
    novelForm.textFile = file;
    novelForm.text = await file.text();
    novelForm.uploadedTextSnapshot = novelForm.text;
    if (!novelForm.title.trim()) {
      novelForm.title = file.name.replace(/\.[^.]+$/, "");
    }
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "TXT 文件读取失败";
  } finally {
    if (input) {
      input.value = "";
    }
  }
}

async function handleNovelSubmit() {
  submitError.value = "";
  result.value = null;
  aiDramaDetail.value = null;
  stopPromptRunPolling();
  stopNovelRunPolling();
  const text = novelForm.text.trim();
  const useUploadedFile =
    novelForm.textFile instanceof File &&
    novelForm.uploadedTextSnapshot.trim() &&
    text === novelForm.uploadedTextSnapshot.trim();
  if (!text && !useUploadedFile) {
    submitError.value = "请上传 TXT 文件或粘贴小说正文。";
    return;
  }
  const totalDurationSeconds = parseOptionalDuration(novelForm.totalDurationSeconds);
  if (totalDurationSeconds !== undefined && (totalDurationSeconds < 6 || totalDurationSeconds > 90)) {
    submitError.value = "总时长需在 6 到 90 秒之间。";
    return;
  }
  const modelReady = await novelTextModelProbeRef.value?.ensureReady();
  if (modelReady === false) {
    submitError.value = "所选文本模型测试未通过，请先检查配置或切换模型。";
    return;
  }
  submitting.value = true;
  const currentDeveloperSettings = loadDeveloperSettings();
  const stopBeforeVideoGeneration = Boolean(
    currentDeveloperSettings.enabled && currentDeveloperSettings.stopBeforeVideoGeneration
  );
  resetProgress();
  startProgress({
    progress: 12,
    stage: "提交小说内容",
    message: stopBeforeVideoGeneration
      ? "开发者模式已开启，将在调用视频模型前停止并返回脚本..."
      : "正在启动 AI 剧总控生成成片...",
  });
  persistActiveRunState("novel");
  try {
    const detail = await runAIDramaAgent({
      title: defaultNovelTitle(),
      text: useUploadedFile ? "" : text,
      textFile: useUploadedFile ? novelForm.textFile : null,
      textAnalysisModel: novelForm.textAnalysisModel,
      aspectRatio: novelForm.aspectRatio,
      providerModel: novelForm.providerModel,
      videoSize: novelForm.videoSize,
      continuitySeed: 2025,
      totalDurationSeconds: totalDurationSeconds ?? null,
      includeKeyframes: true,
      includeDubPlan: true,
      includeLipsyncPlan: true,
      stopBeforeVideoGeneration,
    });
    syncNovelRun(detail);
    if (isAgentRunActive(detail)) {
      startNovelRunPolling(detail.id);
    } else if (detail.status === "completed") {
      complete(detail.summary || (stopBeforeVideoGeneration ? "已在视频模型前停止。" : "小说视频已生成完成。"));
    } else if (detail.status === "failed") {
      fail(detail.summary || "小说视频生成失败，请稍后重试。");
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "小说视频生成失败，请稍后重试。";
    submitError.value = message;
    clearPersistedActiveRunState();
    fail(message);
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  const restoredState = restorePersistedDrafts();
  void loadOptions();
  if (restoredState?.runId) {
    if (restoreRunById(restoredState.mode, restoredState.runId)) {
      return;
    }
    void restoreLatestActiveRun(restoredState.mode);
    return;
  }
  void restoreLatestActiveRun(restoredState?.mode);
});

const unsubscribeDeveloperSettings = subscribeDeveloperSettings((value) => {
  developerSettings.value = value;
});

onUnmounted(() => {
  stopPromptRunPolling();
  stopNovelRunPolling();
  unsubscribeDeveloperSettings();
});
</script>

<style scoped>
.generate-view {
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: clamp(1rem, 2vw, 1.6rem);
  display: grid;
  gap: 1rem;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background:
    radial-gradient(circle at 10% 24%, rgba(97, 173, 255, 0.22), transparent 28%),
    radial-gradient(circle at 88% 10%, rgba(58, 226, 194, 0.16), transparent 28%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.86), rgba(244, 249, 255, 0.74));
}

.hero-eyebrow,
.eyebrow,
.usage-eyebrow {
  margin: 0 0 0.18rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #67809b;
}

.hero h1,
.form-head h2 {
  margin: 0;
  font-family: "Sora", "PingFang SC", sans-serif;
  letter-spacing: -0.04em;
  color: #102842;
}

.hero h1 {
  font-size: clamp(1.45rem, 2.8vw, 1.95rem);
}

.hero-description {
  margin: 0.35rem 0 0;
  color: #4e657f;
  line-height: 1.65;
}

.mode-switch {
  display: inline-flex;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.mode-btn {
  border: 1px solid rgba(112, 137, 171, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  color: #48627f;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 0.72rem 1rem;
  transition: border-color 180ms ease, background 180ms ease, color 180ms ease, transform 180ms ease;
}

.mode-btn:hover {
  transform: translateY(-1px);
}

.mode-btn-active {
  border-color: rgba(46, 125, 255, 0.22);
  background: rgba(234, 243, 255, 0.94);
  color: #1954a6;
}

.layout-grid {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.novel-form {
  display: grid;
  gap: 1rem;
}

.prompt-review {
  display: grid;
  gap: 1rem;
}

.prompt-dev-note {
  color: #244364;
  border: 1px solid rgba(56, 189, 248, 0.14);
  background:
    linear-gradient(180deg, rgba(240, 249, 255, 0.92), rgba(232, 244, 255, 0.82)),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), transparent 30%);
}

.prompt-review__head,
.prompt-review__item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.prompt-review__head h2 {
  margin: 0;
  color: #102842;
  font-family: "Sora", "PingFang SC", sans-serif;
  font-size: 1.22rem;
}

.prompt-review__badge {
  border-radius: 999px;
  border: 1px solid rgba(29, 78, 216, 0.14);
  background: rgba(219, 234, 254, 0.86);
  color: #1d4ed8;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.45rem 0.8rem;
}

.prompt-review__summary {
  margin: 0;
  color: #47607a;
  line-height: 1.7;
}

.prompt-review__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.prompt-review__meta span,
.prompt-review__item-head span {
  border-radius: 999px;
  border: 1px solid rgba(125, 151, 187, 0.18);
  background: rgba(255, 255, 255, 0.74);
  color: #4f6782;
  font-size: 0.75rem;
  padding: 0.28rem 0.62rem;
}

.prompt-review__list {
  display: grid;
  gap: 0.85rem;
}

.prompt-review__item {
  display: grid;
  gap: 0.65rem;
  border: 1px solid rgba(125, 151, 187, 0.16);
  border-radius: 1.15rem;
  background: rgba(255, 255, 255, 0.74);
  padding: 1rem;
}

.prompt-review__item-head strong {
  color: #0f2744;
  font-size: 0.92rem;
}

.prompt-review__prompt {
  margin: 0;
  color: #24384f;
  line-height: 1.75;
  white-space: pre-wrap;
}

.form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.field {
  display: grid;
  gap: 0.5rem;
}

.field-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.field-label {
  color: #35526f;
  font-size: 0.82rem;
  font-weight: 700;
}

.field-hint {
  margin: 0;
  color: #6b819b;
  font-size: 0.74rem;
  line-height: 1.5;
}

.field-input,
.field-select,
.field-textarea {
  width: 100%;
  border: 1px solid rgba(124, 149, 182, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: #12233d;
  padding: 0.88rem 0.95rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.field-textarea {
  min-height: 18rem;
  resize: vertical;
  line-height: 1.72;
}

.field-input:focus,
.field-select:focus,
.field-textarea:focus {
  outline: none;
  border-color: rgba(46, 125, 255, 0.34);
  box-shadow:
    0 0 0 4px rgba(46, 125, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.model-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.model-inline span {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(111, 143, 185, 0.16);
  padding: 0.42rem 0.72rem;
  color: #4d6581;
  font-size: 0.75rem;
  font-weight: 700;
}

.upload-box {
  display: grid;
  gap: 0.22rem;
  border: 1px dashed rgba(112, 137, 171, 0.28);
  border-radius: 16px;
  background: rgba(250, 252, 255, 0.86);
  padding: 1rem;
  cursor: pointer;
}

.hidden-input {
  display: none;
}

.upload-box-title {
  color: #18395e;
  font-size: 0.92rem;
  font-weight: 700;
}

.upload-box-meta {
  color: #69809b;
  font-size: 0.78rem;
}

.submit-btn {
  min-height: 3.1rem;
}

.usage-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(8, 16, 30, 0.42);
  display: grid;
  place-items: center;
  padding: 1rem;
}

.usage-card {
  width: min(700px, 100%);
  max-height: min(76vh, 620px);
  overflow: auto;
  padding: 1rem;
  border-radius: 18px;
}

.usage-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.usage-head h3 {
  margin: 0.25rem 0 0;
  color: #0e2b49;
}

.usage-close {
  border: 1px solid rgba(58, 89, 124, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #254c77;
  font-size: 0.82rem;
  min-height: 2rem;
  padding: 0 0.8rem;
}

.usage-state {
  margin: 0.85rem 0 0;
  color: #4f6885;
}

.usage-state-error {
  color: #ae3e46;
}

.usage-table-wrap {
  margin-top: 0.85rem;
  border: 1px solid rgba(96, 123, 154, 0.22);
  border-radius: 14px;
  overflow: hidden;
}

.usage-table {
  width: 100%;
  border-collapse: collapse;
}

.usage-table th,
.usage-table td {
  text-align: left;
  font-size: 0.86rem;
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid rgba(113, 138, 167, 0.18);
}

.usage-table th {
  font-weight: 700;
  color: #2e4f76;
  background: rgba(243, 249, 255, 0.8);
}

.usage-model {
  margin: 0;
  font-weight: 600;
  color: #1a3e67;
}

.usage-model-id {
  margin: 0.1rem 0 0;
  font-size: 0.75rem;
  color: #6a829f;
}

.usage-model-note {
  margin: 0.2rem 0 0;
  font-size: 0.72rem;
  color: #8a5b12;
}

@media (min-width: 1080px) {
  .layout-grid {
    grid-template-columns: minmax(0, 1.02fr) minmax(0, 0.98fr);
  }
}

@media (max-width: 900px) {
  .hero,
  .form-head {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 820px) {
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

<template>
  <section class="text-script-view space-y-6">
    <PageHeader
      eyebrow="Narrative Studio"
      title="文字转脚本"
      description="输入故事片段或剧情梗概，系统会用固定的短剧导演系统提示词生成角色档案与分镜脚本。"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="surface-chip">固定系统提示词</span>
        <span class="surface-chip">文本模型 {{ activeTextAnalysisModelLabel }}</span>
        <span class="surface-chip">{{ result?.visualStyle || defaultVisualStyle }}</span>
      </div>
    </PageHeader>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)]">
      <form class="surface-panel surface-panel-warm grid gap-5 p-6" @submit.prevent="handleSubmit">
        <div class="surface-tile p-4 text-sm text-slate-600">
          输出会强制包含角色档案和 Markdown 分镜表格；不指定风格时由 AI 自动判断最合适的视觉方向。
        </div>
        <div v-if="optionsError" class="surface-tile border border-amber-200 bg-amber-50/85 p-4 text-sm text-amber-800">
          {{ optionsError }}
        </div>

        <label class="grid gap-2 text-sm text-slate-700">
          故事正文
          <textarea
            v-model="sourceText"
            rows="13"
            class="field-textarea"
            placeholder="例如：少女在暴雨夜闯进旧车站，发现失踪多年的哥哥留下的录音机，录音里正在播放她十分钟后的求救声。"
          ></textarea>
        </label>

        <label class="grid gap-2 text-sm text-slate-700">
          文本分析模型
          <select v-model="textAnalysisModel" class="field-select" :disabled="optionsLoading">
            <option v-for="model in textAnalysisModels" :key="model.value" :value="model.value">
              {{ model.label }}{{ model.description ? ` · ${model.description}` : "" }}
            </option>
          </select>
          <TextModelProbeInline
            ref="textModelProbeRef"
            :model-value="textAnalysisModel"
            :disabled="optionsLoading || submitting"
          />
          <p class="text-xs text-slate-500">用于解析人物、对话、语境和剧情结构。默认 {{ defaultTextAnalysisModelLabel }}。</p>
        </label>

        <label class="grid gap-2 text-sm text-slate-700">
          视觉风格
          <input
            v-model="visualStyle"
            type="text"
            class="field-input"
            :placeholder="defaultVisualStyle"
          />
          <p class="text-xs text-slate-500">可填“写实电影感”“手绘风”“悬疑冷调”等，不填则由 AI 自动决策并保持全片一致。</p>
        </label>

        <div v-if="submitError" class="surface-tile border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
          {{ submitError }}
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button type="submit" class="btn-primary" :disabled="!canSubmit">
            {{ submitButtonLabel }}
          </button>
          <button v-if="result" type="button" class="btn-secondary" @click="handleCopy">
            {{ copyButtonLabel }}
          </button>
          <p class="text-sm text-slate-600">{{ statusLabel }}</p>
        </div>
      </form>

      <aside class="grid gap-4">
        <section class="surface-panel p-5">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">脚本输出</p>
              <h3 class="mt-2 text-lg font-semibold text-slate-900">Markdown 结果</h3>
            </div>
            <span v-if="result" class="surface-chip text-xs">{{ result.visualStyle }}</span>
          </div>

          <div v-if="submitting || activeRunPending" class="surface-tile mt-4 grid gap-2 p-8 text-center text-sm text-slate-600">
            <p class="text-base font-semibold text-slate-800">{{ activeRunStage }}</p>
            <p>{{ activeRunMessage }}</p>
            <p v-if="activeRun" class="text-xs text-slate-500">运行 ID：{{ activeRun.id }} · {{ activeRun.progress }}%</p>
          </div>

          <div v-else-if="result" class="mt-4 grid gap-4">
            <dl class="metadata-grid">
              <div v-for="item in summaryItems" :key="item.label" class="metadata-item">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value }}</dd>
              </div>
            </dl>

            <div class="surface-tile p-4">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">脚本内容</p>
                <div class="flex flex-wrap items-center gap-2">
                  <button type="button" class="btn-secondary btn-sm" @click="handleDownload">
                    下载 Markdown
                  </button>
                  <button type="button" class="btn-secondary btn-sm" @click="handleCopy">
                    {{ copyButtonLabel }}
                  </button>
                </div>
              </div>
              <article class="markdown-output mt-3" v-html="renderedMarkdown"></article>
            </div>

            <div v-if="modelInfoItems.length" class="surface-tile p-4">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">模型信息</p>
              <dl class="metadata-grid mt-3">
                <div v-for="item in modelInfoItems" :key="item.label" class="metadata-item">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </div>
              </dl>
            </div>

          </div>

          <div v-else class="surface-tile mt-4 border-dashed p-8 text-center text-sm text-slate-500">
            生成完成后会在这里展示 Markdown 剧本。
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { fetchAgentRun, runScriptAgent } from "@/api/agents";
import { fetchGenerationOptions } from "@/api/generation";
import PageHeader from "@/components/PageHeader.vue";
import TextModelProbeInline from "@/components/TextModelProbeInline.vue";
import { getRuntimeConfig } from "@/api/runtime-config";
import type { AgentRunDetail, GenerateScriptRequest, GenerateScriptResponse, GenerationTextAnalysisModelInfo } from "@/types";
import { isAgentRunActive, scriptResultFromAgentRun } from "@/utils/agent-run";
import { downloadTextFile, renderMarkdownToHtml } from "@/utils/markdown";
import { resolveRuntimeUrl } from "@/utils/url";

const defaultVisualStyle = "AI 自动决策";
const ACTIVE_RUN_STORAGE_KEY = "ai-cut:text-script:active-run-id";
const FALLBACK_TEXT_ANALYSIS_MODELS: GenerationTextAnalysisModelInfo[] = [
  {
    value: "gpt-5.4",
    label: "GPT-5.4",
    description: "OpenAI ChatGPT key 模式",
    provider: "openai",
    family: "gpt",
    isDefault: true,
  },
  {
    value: "qwen3.6-plus",
    label: "Qwen 3.6 Plus",
    description: "阿里云百炼兼容模式",
    provider: "qwen",
    family: "qwen",
  },
];
const DEFAULT_TEXT_ANALYSIS_MODEL =
  FALLBACK_TEXT_ANALYSIS_MODELS.find((item) => item.isDefault)?.value || FALLBACK_TEXT_ANALYSIS_MODELS[0]?.value || "gpt-5.4";

const sourceText = ref("");
const visualStyle = ref("");
const textAnalysisModels = ref<GenerationTextAnalysisModelInfo[]>([...FALLBACK_TEXT_ANALYSIS_MODELS]);
const textAnalysisModel = ref(DEFAULT_TEXT_ANALYSIS_MODEL);
const optionsLoading = ref(false);
const optionsError = ref("");
const submitting = ref(false);
const submitError = ref("");
const copyState = ref<"idle" | "done" | "error">("idle");
const result = ref<GenerateScriptResponse | null>(null);
const activeRun = ref<AgentRunDetail | null>(null);
const textModelProbeRef = ref<{ ensureReady: (force?: boolean) => Promise<boolean> } | null>(null);

let activeRunPollTimer: number | null = null;

function parseString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeTextModelValue(value: string | null | undefined): string {
  return parseString(value).toLowerCase();
}

function resolveTextAnalysisModelLabel(value: string): string {
  const normalizedValue = normalizeTextModelValue(value);
  if (!normalizedValue) {
    return "";
  }
  const found = textAnalysisModels.value.find((item) => normalizeTextModelValue(item.value) === normalizedValue);
  return found?.label || value;
}

function extractRequestedModelName(response: GenerateScriptResponse | null): string {
  if (!response?.modelInfo) {
    return "";
  }
  const info = response.modelInfo as Record<string, unknown>;
  return parseString(
    info.requestedModel ??
      info.selectedModel ??
      info.textAnalysisModel ??
      response.metadata?.textAnalysisModel ??
      response.metadata?.requestedTextAnalysisModel
  );
}

function extractResolvedModelName(response: GenerateScriptResponse | null): string {
  if (!response?.modelInfo) {
    const source = parseString(response?.source);
    return source.startsWith("remote:") ? parseString(source.slice("remote:".length)) : "";
  }
  const info = response.modelInfo as Record<string, unknown>;
  const source = parseString(response.source);
  const sourceModel = source.startsWith("remote:") ? parseString(source.slice("remote:".length)) : "";
  return parseString(info.resolvedModel ?? info.modelName ?? info.providerModel ?? sourceModel);
}

function pickDefaultTextAnalysisModel(models: GenerationTextAnalysisModelInfo[], preferredValue?: string | null): string {
  const normalizedPreferred = normalizeTextModelValue(preferredValue);
  if (normalizedPreferred) {
    const preferred = models.find((item) => normalizeTextModelValue(item.value) === normalizedPreferred);
    if (preferred) {
      return preferred.value;
    }
  }
  const defaultModel = models.find((item) => item.isDefault);
  if (defaultModel) {
    return defaultModel.value;
  }
  return models[0]?.value || DEFAULT_TEXT_ANALYSIS_MODEL;
}

async function loadTextAnalysisModels() {
  optionsLoading.value = true;
  optionsError.value = "";
  try {
    const options = await fetchGenerationOptions();
    const apiModels = (options.textAnalysisModels || []).filter((item) => Boolean(parseString(item.value)));
    const nextModels = apiModels.length ? apiModels : [...FALLBACK_TEXT_ANALYSIS_MODELS];
    textAnalysisModels.value = nextModels;
    textAnalysisModel.value = pickDefaultTextAnalysisModel(
      nextModels,
      options.defaultTextAnalysisModel || textAnalysisModel.value
    );
    if (!apiModels.length) {
      optionsError.value = "生成配置未返回文本分析模型，已自动使用默认模型列表。";
    }
  } catch (error) {
    optionsError.value = error instanceof Error ? `模型配置加载失败：${error.message}` : "模型配置加载失败，已使用默认模型列表。";
    textAnalysisModels.value = [...FALLBACK_TEXT_ANALYSIS_MODELS];
    textAnalysisModel.value = pickDefaultTextAnalysisModel(textAnalysisModels.value, textAnalysisModel.value);
  } finally {
    optionsLoading.value = false;
  }
}

const selectedTextAnalysisModel = computed(() =>
  textAnalysisModels.value.find((item) => normalizeTextModelValue(item.value) === normalizeTextModelValue(textAnalysisModel.value)) || null
);
const selectedTextAnalysisModelLabel = computed(
  () => selectedTextAnalysisModel.value?.label || resolveTextAnalysisModelLabel(textAnalysisModel.value) || textAnalysisModel.value
);
const defaultTextAnalysisModelLabel = computed(() => {
  const modelValue = pickDefaultTextAnalysisModel(textAnalysisModels.value);
  return resolveTextAnalysisModelLabel(modelValue) || modelValue;
});
const activeTextAnalysisModelLabel = computed(() => {
  const resolved = extractResolvedModelName(result.value);
  return resolveTextAnalysisModelLabel(resolved || textAnalysisModel.value) || (resolved || textAnalysisModel.value || "未选择");
});

const activeRunPending = computed(() => isAgentRunActive(activeRun.value));
const activeRunStage = computed(() => {
  if (!activeRun.value) {
    return "正在提交脚本任务";
  }
  return activeRun.value.status === "queued" ? "任务排队中" : "任务执行中";
});
const activeRunMessage = computed(() => {
  if (!activeRun.value) {
    return "正在创建异步脚本任务...";
  }
  return activeRun.value.summary || "正在生成角色档案和 Markdown 分镜表。";
});

const canSubmit = computed(() => Boolean(sourceText.value.trim()) && !submitting.value && !activeRunPending.value);
const submitButtonLabel = computed(() => {
  if (submitting.value) {
    return "提交中...";
  }
  if (activeRunPending.value) {
    return "生成进行中...";
  }
  return "开始生成脚本";
});
const copyButtonLabel = computed(() => {
  if (copyState.value === "done") {
    return "已复制";
  }
  if (copyState.value === "error") {
    return "复制失败";
  }
  return "复制 Markdown";
});
const statusLabel = computed(() => {
  if (submitting.value) {
    return "正在创建异步脚本任务。";
  }
  if (activeRunPending.value) {
    return activeRunMessage.value;
  }
  if (result.value) {
    return `最近一次生成风格：${result.value.visualStyle} · 文本模型：${activeTextAnalysisModelLabel.value}`;
  }
  return `支持把故事片段直接转成可继续投喂图像或视频生产链路的脚本。当前文本模型：${selectedTextAnalysisModelLabel.value}`;
});

const summaryItems = computed(() => {
  if (!result.value) {
    return [];
  }
  const resolvedModelName = extractResolvedModelName(result.value);
  const requestedModelName = extractRequestedModelName(result.value) || textAnalysisModel.value;
  return [
    { label: "ID", value: result.value.id },
    { label: "文本模型", value: resolveTextAnalysisModelLabel(resolvedModelName || requestedModelName) || requestedModelName || "未指定" },
    { label: "视觉风格", value: result.value.visualStyle },
    { label: "来源模型", value: result.value.source },
    { label: "生成时间", value: new Date(result.value.createdAt).toLocaleString() },
  ];
});

const modelInfoItems = computed(() => {
  const info = result.value?.modelInfo;
  if (!info) {
    return [];
  }
  const infoRecord = info as Record<string, unknown>;
  const requestedModel = parseString(
    infoRecord.requestedModel ?? infoRecord.selectedModel ?? infoRecord.textAnalysisModel
  );
  const resolvedModel = parseString(
    infoRecord.resolvedModel ?? infoRecord.modelName ?? infoRecord.providerModel
  );
  const entries: Array<{ label: string; value: string }> = [];
  if (info.provider) {
    entries.push({ label: "服务商", value: info.provider });
  }
  if (requestedModel) {
    entries.push({ label: "请求模型", value: resolveTextAnalysisModelLabel(requestedModel) || requestedModel });
  }
  if (resolvedModel) {
    const requestedNormalized = normalizeTextModelValue(requestedModel);
    const resolvedNormalized = normalizeTextModelValue(resolvedModel);
    entries.push({
      label: requestedNormalized && requestedNormalized !== resolvedNormalized ? "实际模型" : "底层模型",
      value: resolveTextAnalysisModelLabel(resolvedModel) || resolvedModel,
    });
  }
  if (info.endpointHost) {
    entries.push({ label: "模型网关", value: info.endpointHost });
  }
  if (typeof info.temperature === "number") {
    entries.push({ label: "Temperature", value: `${info.temperature}` });
  }
  if (typeof info.maxTokens === "number") {
    entries.push({ label: "Max Tokens", value: `${info.maxTokens}` });
  }
  if (typeof info.timeoutSeconds === "number") {
    entries.push({ label: "超时", value: `${info.timeoutSeconds} 秒` });
  }
  return entries;
});

const renderedMarkdown = computed(() => renderMarkdownToHtml(result.value?.scriptMarkdown || ""));

function persistActiveRunId(runId: string) {
  try {
    window.localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, runId);
  } catch {
    // Ignore persistence failures.
  }
}

function clearPersistedActiveRunId() {
  try {
    window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  } catch {
    // Ignore persistence failures.
  }
}

function stopActiveRunPolling() {
  if (activeRunPollTimer !== null) {
    window.clearInterval(activeRunPollTimer);
    activeRunPollTimer = null;
  }
}

function syncActiveRun(run: AgentRunDetail) {
  activeRun.value = run;
  if (run.status === "failed") {
    submitError.value = run.summary || "脚本生成失败";
    clearPersistedActiveRunId();
    stopActiveRunPolling();
    return;
  }
  if (run.status === "completed") {
    const nextResult = scriptResultFromAgentRun(run);
    result.value = nextResult;
    if (!nextResult) {
      submitError.value = "任务已完成，但未返回 Markdown 脚本。";
    }
    clearPersistedActiveRunId();
    stopActiveRunPolling();
    return;
  }
  persistActiveRunId(run.id);
}

async function refreshActiveRun(runId: string) {
  try {
    const run = await fetchAgentRun(runId);
    syncActiveRun(run);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "同步脚本任务状态失败";
  }
}

function startActiveRunPolling(runId: string) {
  stopActiveRunPolling();
  void refreshActiveRun(runId);
  activeRunPollTimer = window.setInterval(() => {
    void refreshActiveRun(runId);
  }, 2000);
}

function restoreActiveRun() {
  try {
    const runId = window.localStorage.getItem(ACTIVE_RUN_STORAGE_KEY)?.trim() || "";
    if (!runId) {
      return;
    }
    startActiveRunPolling(runId);
  } catch {
    // Ignore restore failures.
  }
}

async function handleSubmit() {
  if (!canSubmit.value) {
    return;
  }
  submitError.value = "";
  copyState.value = "idle";
  result.value = null;
  activeRun.value = null;
  clearPersistedActiveRunId();
  stopActiveRunPolling();
  try {
    const modelReady = await textModelProbeRef.value?.ensureReady();
    if (modelReady === false) {
      submitError.value = "所选文本模型测试未通过，请先检查配置或切换模型。";
      return;
    }
    submitting.value = true;
    const payload: GenerateScriptRequest = {
      text: sourceText.value.trim(),
      visualStyle: visualStyle.value.trim() || null,
      textAnalysisModel: textAnalysisModel.value || null,
    };
    const run = await runScriptAgent("script-director", {
      text: payload.text,
      visualStyle: payload.visualStyle || "",
      textAnalysisModel: payload.textAnalysisModel || undefined,
    });
    syncActiveRun(run);
    if (isAgentRunActive(run)) {
      startActiveRunPolling(run.id);
    }
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "脚本生成失败";
  } finally {
    submitting.value = false;
  }
}

async function handleCopy() {
  if (!result.value?.scriptMarkdown) {
    return;
  }
  try {
    await navigator.clipboard.writeText(result.value.scriptMarkdown);
    copyState.value = "done";
    window.setTimeout(() => {
      copyState.value = "idle";
    }, 1800);
  } catch {
    copyState.value = "error";
  }
}

function handleDownload() {
  if (!result.value?.scriptMarkdown) {
    return;
  }
  const downloadUrl = result.value.downloadUrl || result.value.markdownFileUrl;
  if (downloadUrl) {
    const link = document.createElement("a");
    link.href = resolveRuntimeUrl(downloadUrl, getRuntimeConfig().storageBaseUrl);
    link.download = `script-${result.value.id}.md`;
    link.rel = "noreferrer noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }
  downloadTextFile(`script-${result.value.id}.md`, result.value.scriptMarkdown, "text/markdown;charset=utf-8");
}

onMounted(() => {
  void loadTextAnalysisModels();
  restoreActiveRun();
});

onUnmounted(() => {
  stopActiveRunPolling();
});
</script>

<style scoped>
.markdown-output {
  max-height: 68vh;
  overflow: auto;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.9);
  padding: 1rem;
  color: #0f172a;
  font-size: 0.84rem;
  line-height: 1.7;
  word-break: break-word;
}

.markdown-output :deep(h1),
.markdown-output :deep(h2),
.markdown-output :deep(h3),
.markdown-output :deep(h4) {
  margin: 1.2rem 0 0.6rem;
  color: #0f172a;
  line-height: 1.25;
}

.markdown-output :deep(h1) { font-size: 1.4rem; }
.markdown-output :deep(h2) { font-size: 1.18rem; }
.markdown-output :deep(h3) { font-size: 1.04rem; }

.markdown-output :deep(p),
.markdown-output :deep(li),
.markdown-output :deep(blockquote) {
  margin: 0.45rem 0;
  color: #1f2937;
}

.markdown-output :deep(a) {
  color: #2563eb;
  text-decoration: none;
}

.markdown-output :deep(a:hover) {
  text-decoration: underline;
}

.markdown-output :deep(ul),
.markdown-output :deep(ol) {
  margin: 0.6rem 0;
  padding-left: 1.35rem;
}

.markdown-output :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.85rem 0;
  overflow: hidden;
  border-radius: 14px;
}

.markdown-output :deep(th),
.markdown-output :deep(td) {
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 0.55rem 0.65rem;
  vertical-align: top;
}

.markdown-output :deep(th) {
  background: rgba(241, 245, 249, 0.95);
  font-weight: 700;
}

.markdown-output :deep(code) {
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.06);
  padding: 0.1rem 0.35rem;
  font-family: "JetBrains Mono", monospace;
}

.markdown-output :deep(pre) {
  overflow: auto;
  border-radius: 14px;
  background: #0f172a;
  padding: 0.85rem 1rem;
  color: #e2e8f0;
}

.metadata-grid {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
}

.metadata-item {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.64);
  padding: 0.7rem 0.8rem;
}

.metadata-item dt {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.metadata-item dd {
  margin-top: 0.35rem;
  font-size: 0.84rem;
  color: #0f172a;
  word-break: break-word;
}

</style>

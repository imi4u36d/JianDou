<template>
  <section class="text-script-view space-y-6">
    <PageHeader
      eyebrow="Narrative Studio"
      title="文字转脚本"
      description="输入故事片段或剧情梗概，系统会用固定的短剧导演系统提示词生成角色档案与分镜脚本。"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="surface-chip">固定系统提示词</span>
        <span class="surface-chip">{{ result?.visualStyle || defaultVisualStyle }}</span>
      </div>
    </PageHeader>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)]">
      <form class="surface-panel surface-panel-warm grid gap-5 p-6" @submit.prevent="handleSubmit">
        <div class="surface-tile p-4 text-sm text-slate-600">
          输出会强制包含角色档案和 Markdown 分镜表格；不指定风格时由 AI 自动判断最合适的视觉方向。
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

          <div v-if="submitting" class="surface-tile mt-4 p-8 text-center text-sm text-slate-600">
            正在生成脚本，请稍候...
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
import { computed, ref } from "vue";
import { generateScriptFromText } from "@/api/script";
import PageHeader from "@/components/PageHeader.vue";
import { getRuntimeConfig } from "@/api/runtime-config";
import type { GenerateScriptRequest, GenerateScriptResponse } from "@/types";
import { downloadTextFile, renderMarkdownToHtml } from "@/utils/markdown";
import { resolveRuntimeUrl } from "@/utils/url";

const defaultVisualStyle = "AI 自动决策";

const sourceText = ref("");
const visualStyle = ref("");
const submitting = ref(false);
const submitError = ref("");
const copyState = ref<"idle" | "done" | "error">("idle");
const result = ref<GenerateScriptResponse | null>(null);

const canSubmit = computed(() => Boolean(sourceText.value.trim()) && !submitting.value);
const submitButtonLabel = computed(() => (submitting.value ? "生成中..." : "开始生成脚本"));
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
    return "系统提示词已固定，下游正在生成角色档案和分镜表。";
  }
  if (result.value) {
    return `最近一次生成风格：${result.value.visualStyle}`;
  }
  return "支持把故事片段直接转成可继续投喂图像或视频生产链路的脚本。";
});

const summaryItems = computed(() => {
  if (!result.value) {
    return [];
  }
  return [
    { label: "ID", value: result.value.id },
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
  const entries: Array<{ label: string; value: string }> = [];
  if (info.provider) {
    entries.push({ label: "服务商", value: info.provider });
  }
  if (info.modelName) {
    entries.push({ label: "底层模型", value: info.modelName });
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

async function handleSubmit() {
  if (!canSubmit.value) {
    return;
  }
  submitError.value = "";
  copyState.value = "idle";
  submitting.value = true;
  try {
    const payload: GenerateScriptRequest = {
      text: sourceText.value.trim(),
      visualStyle: visualStyle.value.trim() || null,
    };
    result.value = await generateScriptFromText(payload);
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

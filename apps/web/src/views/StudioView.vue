<template>
  <section class="studio-page">
    <aside class="agent-rail" :class="railCollapsed ? 'agent-rail-collapsed' : ''">
      <div class="agent-rail-head">
        <div v-if="!railCollapsed">
          <p class="section-eyebrow">Agent Menu</p>
          <h2 class="agent-rail-title">四大 Agent</h2>
        </div>
        <button type="button" class="rail-toggle" @click="railCollapsed = !railCollapsed">
          {{ railCollapsed ? "展开" : "收起" }}
        </button>
      </div>

      <div class="agent-rail-list">
        <button
          v-for="agent in AGENT_DEFINITIONS"
          :key="agent.id"
          type="button"
          class="agent-rail-item"
          :class="agent.id === selectedAgentId ? 'agent-rail-item-active' : ''"
          :style="{ '--agent-accent': agent.accent, '--agent-accent-soft': agent.accentSoft }"
          @click="handleSelectAgent(agent.id)"
        >
          <span class="agent-rail-icon">{{ agent.icon }}</span>
          <div v-if="!railCollapsed" class="agent-rail-copy">
            <div class="agent-rail-copy-head">
              <strong>{{ agent.name }}</strong>
              <span class="agent-rail-status">{{ agentStatusLabel(agent.id) }}</span>
            </div>
            <p>{{ agent.subtitle }}</p>
          </div>
        </button>
      </div>
    </aside>

    <div class="studio-content">
      <header class="hero-card">
        <div>
          <p class="section-eyebrow">Active Agent</p>
          <h1 class="hero-title">{{ selectedAgent.name }}</h1>
          <p class="hero-description">{{ selectedAgent.description }}</p>
        </div>

        <div class="hero-badges">
          <span class="hero-badge" :style="{ '--agent-accent': selectedAgent.accent }">{{ runtimeStatusLabel }}</span>
          <span class="hero-badge hero-badge-soft">{{ selectedAgent.deliveryLabel }}</span>
        </div>
      </header>

      <section class="progress-card">
        <div class="section-head">
          <div>
            <p class="section-eyebrow">Run Flow</p>
            <h2 class="section-title">完整运行流程</h2>
          </div>

          <div class="progress-metrics">
            <div class="metric-card">
              <span>总运行时间</span>
              <strong>{{ progressTotalRuntimeLabel }}</strong>
            </div>
            <div class="metric-card">
              <span>当前节点</span>
              <strong>{{ progressCurrentStageLabel }}</strong>
            </div>
            <div class="metric-card">
              <span>节点已用时间</span>
              <strong>{{ progressCurrentStageElapsedLabel }}</strong>
            </div>
          </div>
        </div>

        <div class="flow-track">
          <div
            v-for="stage in progressStages"
            :key="stage.key"
            class="flow-stage"
            :class="`flow-stage-${stage.state}`"
          >
            <div class="flow-stage-line"></div>
            <div class="flow-stage-dot"></div>
            <div class="flow-stage-card">
              <div class="flow-stage-head">
                <strong>{{ stage.label }}</strong>
                <span>{{ stage.stateLabel }}</span>
              </div>
              <p>{{ stage.description }}</p>
              <small>{{ stage.elapsedLabel }}</small>
              <small v-if="stage.message" class="flow-stage-message">{{ stage.message }}</small>
            </div>
          </div>
        </div>

        <p v-if="progressErrorMessage" class="progress-error">{{ progressErrorMessage }}</p>
      </section>

      <section class="studio-main-grid">
        <section class="console-panel form-panel">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">Composer</p>
              <h2 class="section-title">Agent 输入区</h2>
            </div>
          </div>

          <form class="console-form" @submit.prevent="handleRun">
            <div v-if="selectedAgent.id === 'ai-drama'" class="console-form-stack">
              <label class="console-field">
                <span>标题</span>
                <input v-model="aiDramaDraft.title" class="console-input" type="text" />
              </label>
              <label class="console-field">
                <span>正文</span>
                <textarea v-model="aiDramaDraft.text" class="console-textarea" rows="8"></textarea>
              </label>
              <label class="console-field">
                <span>TXT 文本导入</span>
                <input class="console-file" type="file" accept=".txt,text/plain" @change="handleAIDramaTextFile" />
                <p class="console-hint">支持上传 `.txt`，内容会直接写入正文输入框。</p>
              </label>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>画幅</span>
                  <select v-model="aiDramaDraft.aspectRatio" class="console-select">
                    <option value="9:16">9:16</option>
                    <option value="16:9">16:9</option>
                  </select>
                </label>
                <label class="console-field">
                  <span>总生成时长</span>
                  <input
                    v-model.number="aiDramaDraft.totalDurationSeconds"
                    class="console-input"
                    type="number"
                    min="6"
                    max="90"
                    step="0.5"
                    placeholder="例如 24"
                  />
                  <p class="console-hint">作为导演决策约束，AI 会据此反推镜头数和单镜头时长。</p>
                </label>
              </div>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>统一 Seed</span>
                  <input v-model.number="aiDramaDraft.continuitySeed" class="console-input" type="number" min="0" />
                </label>
                <div class="console-field">
                  <span>导演决策</span>
                  <p class="console-hint">
                    镜头数、单镜头时长、视觉风格、片头片尾和转场算法都由 AI 剧总控自动决策，并由多 Agent 协同完成。
                  </p>
                </div>
                <div class="console-field">
                  <span>附加流水线</span>
                  <div class="console-file-list">
                    <button
                      type="button"
                      class="btn-segment"
                      :class="aiDramaDraft.includeKeyframes ? 'btn-segment-active' : ''"
                      @click="aiDramaDraft.includeKeyframes = !aiDramaDraft.includeKeyframes"
                    >
                      关键帧
                    </button>
                    <button
                      type="button"
                      class="btn-segment"
                      :class="aiDramaDraft.includeDubPlan ? 'btn-segment-active' : ''"
                      @click="aiDramaDraft.includeDubPlan = !aiDramaDraft.includeDubPlan"
                    >
                      配音规划
                    </button>
                    <button
                      type="button"
                      class="btn-segment"
                      :class="aiDramaDraft.includeLipsyncPlan ? 'btn-segment-active' : ''"
                      @click="aiDramaDraft.includeLipsyncPlan = !aiDramaDraft.includeLipsyncPlan"
                    >
                      口型规划
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="selectedAgent.id === 'drama-editor'" class="console-form-stack">
              <label class="console-field">
                <span>任务标题</span>
                <input v-model="dramaDraft.title" class="console-input" type="text" />
              </label>
              <label class="console-field">
                <span>源素材</span>
                <input class="console-file" type="file" accept="video/*" multiple @change="handleDramaFiles" />
                <div class="console-file-list">
                  <span v-for="file in dramaFileNames" :key="file" class="soft-pill">{{ file }}</span>
                </div>
              </label>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>平台</span>
                  <select v-model="dramaDraft.platform" class="console-select">
                    <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platform }}</option>
                  </select>
                </label>
                <label class="console-field">
                  <span>画幅</span>
                  <select v-model="dramaDraft.aspectRatio" class="console-select">
                    <option value="9:16">9:16</option>
                    <option value="16:9">16:9</option>
                  </select>
                </label>
              </div>
              <div class="console-grid-3">
                <label class="console-field">
                  <span>最小时长</span>
                  <input v-model.number="dramaDraft.minDurationSeconds" class="console-input" type="number" min="5" max="300" />
                </label>
                <label class="console-field">
                  <span>最大时长</span>
                  <input v-model.number="dramaDraft.maxDurationSeconds" class="console-input" type="number" min="5" max="300" />
                </label>
                <label class="console-field">
                  <span>输出数</span>
                  <input v-model.number="dramaDraft.outputCount" class="console-input" type="number" min="1" max="10" />
                </label>
              </div>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>片头</span>
                  <select v-model="dramaDraft.introTemplate" class="console-select">
                    <option v-for="item in introOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                  </select>
                </label>
                <label class="console-field">
                  <span>片尾</span>
                  <select v-model="dramaDraft.outroTemplate" class="console-select">
                    <option v-for="item in outroOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                  </select>
                </label>
              </div>
              <label class="console-field">
                <span>创意提示词</span>
                <textarea v-model="dramaDraft.creativePrompt" class="console-textarea" rows="4"></textarea>
              </label>
              <label class="console-field">
                <span>台词 / 字幕片段</span>
                <textarea v-model="dramaDraft.transcriptText" class="console-textarea" rows="3"></textarea>
              </label>
            </div>

            <div v-else-if="selectedAgent.id === 'visual-lab'" class="console-form-stack">
              <label class="console-field">
                <span>视觉提示词</span>
                <textarea v-model="visualDraft.prompt" class="console-textarea" rows="7"></textarea>
              </label>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>媒体类型</span>
                  <div class="segmented-shell">
                    <button
                      type="button"
                      class="btn-segment"
                      :class="visualDraft.mediaKind === 'image' ? 'btn-segment-active' : ''"
                      @click="visualDraft.mediaKind = 'image'"
                    >
                      图片
                    </button>
                    <button
                      type="button"
                      class="btn-segment"
                      :class="visualDraft.mediaKind === 'video' ? 'btn-segment-active' : ''"
                      @click="visualDraft.mediaKind = 'video'"
                    >
                      视频
                    </button>
                  </div>
                </label>
                <label class="console-field">
                  <span>版本</span>
                  <select v-model.number="visualDraft.version" class="console-select">
                    <option v-for="item in versionOptions" :key="item.version" :value="item.version">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
              </div>
              <div class="console-grid-2">
                <label class="console-field">
                  <span>风格预设</span>
                  <select v-model="visualDraft.stylePreset" class="console-select">
                    <option value="">不指定</option>
                    <option v-for="preset in availableStylePresets" :key="preset.key" :value="preset.key">
                      {{ preset.label }}
                    </option>
                  </select>
                </label>
                <label class="console-field" v-if="visualDraft.mediaKind === 'image'">
                  <span>图片尺寸</span>
                  <select v-model="visualDraft.imageSize" class="console-select">
                    <option v-for="item in generationOptions.imageSizes" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
                <label class="console-field" v-else>
                  <span>视频模型</span>
                  <select v-model="visualDraft.providerModel" class="console-select">
                    <option v-for="item in availableVideoModels" :key="item.value" :value="item.value">
                      {{ item.label }}{{ item.description ? ` · ${item.description}` : "" }}
                    </option>
                  </select>
                  <p v-if="selectedVideoModel?.description" class="console-hint">{{ selectedVideoModel.description }}</p>
                </label>
              </div>
              <div class="console-grid-2" v-if="visualDraft.mediaKind === 'video'">
                <label class="console-field">
                  <span>视频分辨率</span>
                  <select v-model="visualDraft.videoSize" class="console-select">
                    <option v-for="item in availableVideoSizes" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
                <label class="console-field">
                  <span>视频时长</span>
                  <select v-model.number="visualDraft.videoDurationSeconds" class="console-select">
                    <option v-for="item in availableVideoDurations" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
              </div>
            </div>

            <div v-else class="console-form-stack">
              <label class="console-field">
                <span>故事正文</span>
                <textarea v-model="scriptDraft.text" class="console-textarea" rows="11"></textarea>
              </label>
              <label class="console-field">
                <span>视觉风格</span>
                <input
                  v-model="scriptDraft.visualStyle"
                  class="console-input"
                  type="text"
                  placeholder="AI 自动决策"
                />
              </label>
            </div>

            <div class="console-actions">
              <button type="submit" class="agent-run-button" :disabled="runDisabled">
                {{ runLabel }}
              </button>
              <button type="button" class="agent-secondary-button" @click="resetDraft">
                Reset
              </button>
            </div>
            <p class="console-hint">{{ submitHint }}</p>
            <p v-if="submitError" class="form-error">{{ submitError }}</p>
          </form>
        </section>

        <section class="console-panel output-panel">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">Result</p>
              <h2 class="section-title">{{ activeRun?.title || "等待运行结果" }}</h2>
            </div>
            <span class="hero-badge hero-badge-soft">{{ activeRun ? activeRun.resultLabel : selectedAgent.deliveryLabel }}</span>
          </div>

          <div v-if="runBusy && !activeRun" class="console-placeholder">
            当前请求已提交，流程卡片会显示节点进度，结果完成后会自动落在这里。
          </div>

          <div v-else-if="activeRun" class="output-stack">
            <div class="output-preview">
              <template v-if="previewKind === 'image'">
                <img :src="resolvedPreviewUrl" alt="generated media" class="output-media" />
              </template>
              <template v-else-if="previewKind === 'video'">
                <video :src="resolvedPreviewUrl" controls playsinline preload="metadata" class="output-media"></video>
              </template>
              <template v-else-if="previewKind === 'markdown'">
                <div class="output-markdown" v-html="renderedMarkdown"></div>
              </template>
              <template v-else>
                <div class="output-empty">
                  <p>任务输出会在这里以卡片形式展示。</p>
                </div>
              </template>
            </div>

            <div class="output-meta-grid">
              <div class="output-meta">
                <span>Agent</span>
                <strong>{{ getAgentDefinition(activeRun.agentId).name }}</strong>
              </div>
              <div class="output-meta">
                <span>Status</span>
                <strong>{{ activeRun.status }}</strong>
              </div>
              <div class="output-meta">
                <span>Source</span>
                <strong>{{ activeRun.sourceLabel }}</strong>
              </div>
              <div class="output-meta">
                <span>Created</span>
                <strong>{{ formatDate(activeRun.createdAt) }}</strong>
              </div>
            </div>

            <div v-if="previewKind === 'markdown'" class="output-actions">
              <button type="button" class="agent-secondary-button" @click="downloadMarkdown">
                下载 Markdown
              </button>
            </div>

            <details class="data-drawer">
              <summary>查看输入 / 输出详情</summary>
              <div class="output-json-grid">
                <div class="output-json-block">
                  <p>Input</p>
                  <pre>{{ prettyJson(activeRun.input) }}</pre>
                </div>
                <div class="output-json-block">
                  <p>Output</p>
                  <pre>{{ prettyJson(activeRun.output) }}</pre>
                </div>
              </div>
            </details>
          </div>

          <div v-else class="console-placeholder">
            选择一个 Agent 并运行，结果会在这里展示。
          </div>
        </section>
      </section>

      <section class="console-panel history-panel">
        <div class="section-head">
          <div>
            <p class="section-eyebrow">History</p>
            <h2 class="section-title">最近运行</h2>
          </div>
          <span class="hero-badge hero-badge-soft">{{ historyEntries.length }}</span>
        </div>

        <div class="history-list">
          <button
            v-for="entry in historyEntries"
            :key="entry.id"
            class="history-item"
            :class="entry.id === selectedRunId ? 'history-item-active' : ''"
            type="button"
            @click="openHistoryEntry(entry)"
          >
            <div class="history-item-head">
              <strong>{{ entry.title }}</strong>
              <span :style="{ '--agent-accent': getAgentDefinition(entry.agentId).accent }">{{ entry.status }}</span>
            </div>
            <p>{{ getAgentDefinition(entry.agentId).name }}</p>
            <small>{{ entry.summary }}</small>
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchGenerationOptions } from "@/api/generation";
import {
  fetchAgentRun,
  fetchAgentRuns,
  getPersistedRuns,
  runAIDramaAgent,
  runDramaAgent,
  runScriptAgent,
  runVisualAgent,
} from "@/api/agents";
import { DEFAULT_AGENT_ID, AGENT_DEFINITIONS, getAgentDefinition, isAgentId } from "@/workbench/agents";
import { upsertAgentRun } from "@/workbench/storage";
import { getRuntimeConfig } from "@/api/runtime-config";
import type {
  AgentId,
  AgentRunArtifact,
  AgentRunDetail,
  AgentRunEvent,
  AgentRunSummary,
  GenerationOptionsResponse,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";
import { resolveRuntimeUrl } from "@/utils/url";
import { usePolling } from "@/composables/usePolling";

type FlowStageState = "pending" | "running" | "completed" | "error";

interface FlowStageDefinition {
  key: string;
  label: string;
  description: string;
  match: (event: AgentRunEvent) => boolean;
}

interface FlowStageView {
  key: string;
  label: string;
  description: string;
  state: FlowStageState;
  stateLabel: string;
  elapsedMs: number | null;
  elapsedLabel: string;
  startedMs: number | null;
  finishedMs: number | null;
  message: string;
}

interface PendingRunState {
  agentId: AgentId;
  title: string;
  startedMs: number;
}

const route = useRoute();
const router = useRouter();

const FALLBACK_GENERATION_OPTIONS: GenerationOptionsResponse = {
  versions: Array.from({ length: 10 }, (_, index) => index + 1),
  defaultVersion: 1,
  stylePresets: [],
  imageSizes: [
    { value: "768x768", label: "768 × 768" },
    { value: "1024x1024", label: "1024 × 1024" },
    { value: "1365x768", label: "1365 × 768" },
  ],
  videoModels: [
    { value: "wan2.6-i2v", label: "wan2.6-i2v", isDefault: true },
    { value: "wan2.6-t2v", label: "wan2.6-t2v" },
    { value: "wan2.5-t2v-preview", label: "wan2.5-t2v-preview" },
    { value: "wan2.2-t2v-plus", label: "wan2.2-t2v-plus" },
    { value: "wanx2.1-t2v-turbo", label: "wanx2.1-t2v-turbo" },
    { value: "wanx2.1-t2v-plus", label: "wanx2.1-t2v-plus" },
  ] as GenerationVideoModelInfo[],
  defaultVideoModel: "wan2.6-i2v",
  videoSizes: [
    { value: "1080x1920", label: "1080 × 1920", width: 1080, height: 1920 },
    { value: "1920x1080", label: "1920 × 1080", width: 1920, height: 1080 },
    { value: "1280x720", label: "1280 × 720", width: 1280, height: 720 },
  ] as GenerationVideoSizeOption[],
  videoDurations: [
    { value: 4, label: "4 秒" },
    { value: 6, label: "6 秒" },
    { value: 8, label: "8 秒" },
  ] as GenerationVideoDurationOption[],
  defaultStylePreset: null,
  defaultImageSize: "1024x1024",
  defaultVideoSize: "1080x1920",
  defaultVideoDurationSeconds: 6,
};

const INTRO_OPTIONS = [
  { value: "hook", label: "开场钩子" },
  { value: "cold_open", label: "冷开场" },
  { value: "flash_hook", label: "闪切钩子" },
  { value: "pressure_build", label: "压迫感推进" },
];

const OUTRO_OPTIONS = [
  { value: "brand", label: "品牌收束" },
  { value: "follow_hook", label: "追更钩子" },
  { value: "question_freeze", label: "反问定格" },
  { value: "call_to_action", label: "行动召唤" },
];

const PLATFORM_OPTIONS = ["抖音", "视频号", "快手", "小红书"];
const introOptions = INTRO_OPTIONS;
const outroOptions = OUTRO_OPTIONS;
const platformOptions = PLATFORM_OPTIONS;

const generationOptions = ref<GenerationOptionsResponse>({
  ...FALLBACK_GENERATION_OPTIONS,
  versions: [...FALLBACK_GENERATION_OPTIONS.versions],
  stylePresets: [...FALLBACK_GENERATION_OPTIONS.stylePresets],
  imageSizes: [...FALLBACK_GENERATION_OPTIONS.imageSizes],
  videoModels: [...FALLBACK_GENERATION_OPTIONS.videoModels],
  videoSizes: [...FALLBACK_GENERATION_OPTIONS.videoSizes],
  videoDurations: [...FALLBACK_GENERATION_OPTIONS.videoDurations],
});
const remoteRuns = ref<AgentRunSummary[]>([]);
const persistedRuns = ref<AgentRunDetail[]>(getPersistedRuns());
const loading = ref(true);
const refreshing = ref(false);
const runBusy = ref(false);
const submitError = ref("");
const railCollapsed = ref(false);
const selectedAgentId = ref<AgentId>(DEFAULT_AGENT_ID);
const selectedRunId = ref("");
const selectedRunDetail = ref<AgentRunDetail | null>(null);
const pendingRun = ref<PendingRunState | null>(null);
const nowMs = ref(Date.now());

let clockTimer: number | null = null;

const aiDramaDraft = reactive({
  title: "暴雨车站",
  text: "暴雨夜，少女闯进废弃车站，在旧广播室里找到失踪哥哥留下的录音机。",
  aspectRatio: "9:16" as "9:16" | "16:9",
  totalDurationSeconds: 24 as number | null,
  continuitySeed: 2025,
  includeKeyframes: true,
  includeDubPlan: true,
  includeLipsyncPlan: true,
});

const dramaDraft = reactive({
  title: "黑场倒计时",
  sourceFiles: [] as File[],
  platform: "抖音",
  aspectRatio: "9:16" as "9:16" | "16:9",
  minDurationSeconds: 30,
  maxDurationSeconds: 60,
  outputCount: 4,
  introTemplate: "hook",
  outroTemplate: "brand",
  creativePrompt: "",
  transcriptText: "",
  editingMode: "drama" as "drama" | "mixcut",
  mixcutContentType: "drama",
  mixcutStylePreset: "director",
});

const visualDraft = reactive({
  prompt: "近黑背景中，一束红光穿透烟雾，电影感，超高对比。",
  mediaKind: "image" as "image" | "video",
  version: 1,
  stylePreset: "",
  providerModel: "",
  imageSize: "1024x1024",
  videoSize: "1080x1920",
  videoDurationSeconds: 6,
});

const scriptDraft = reactive({
  text: "一个故事片段：",
  visualStyle: "",
});

function currentAgentIdFromQuery(value: unknown): AgentId {
  if (Array.isArray(value)) {
    return currentAgentIdFromQuery(value[0]);
  }
  if (isAgentId(value)) {
    return value;
  }
  return DEFAULT_AGENT_ID;
}

function normalizeGenerationOptions(raw: GenerationOptionsResponse | null | undefined): GenerationOptionsResponse {
  if (!raw) {
    return {
      ...FALLBACK_GENERATION_OPTIONS,
      versions: [...FALLBACK_GENERATION_OPTIONS.versions],
      stylePresets: [...FALLBACK_GENERATION_OPTIONS.stylePresets],
      imageSizes: [...FALLBACK_GENERATION_OPTIONS.imageSizes],
      videoModels: [...FALLBACK_GENERATION_OPTIONS.videoModels],
      videoSizes: [...FALLBACK_GENERATION_OPTIONS.videoSizes],
      videoDurations: [...FALLBACK_GENERATION_OPTIONS.videoDurations],
    };
  }
  return {
    versions: raw.versions?.length ? [...raw.versions] : [...FALLBACK_GENERATION_OPTIONS.versions],
    versionDetails: raw.versionDetails?.length ? [...raw.versionDetails] : undefined,
    defaultVersion: raw.defaultVersion ?? FALLBACK_GENERATION_OPTIONS.defaultVersion,
    stylePresets: raw.stylePresets?.length ? [...raw.stylePresets] : [],
    imageSizes: raw.imageSizes?.length ? [...raw.imageSizes] : [...FALLBACK_GENERATION_OPTIONS.imageSizes],
    videoModels: raw.videoModels?.length ? [...raw.videoModels] : [...FALLBACK_GENERATION_OPTIONS.videoModels],
    defaultVideoModel: raw.defaultVideoModel ?? FALLBACK_GENERATION_OPTIONS.defaultVideoModel,
    videoSizes: raw.videoSizes?.length ? [...raw.videoSizes] : [...FALLBACK_GENERATION_OPTIONS.videoSizes],
    videoDurations: raw.videoDurations?.length ? [...raw.videoDurations] : [...FALLBACK_GENERATION_OPTIONS.videoDurations],
    defaultStylePreset: raw.defaultStylePreset ?? null,
    defaultImageSize: raw.defaultImageSize ?? FALLBACK_GENERATION_OPTIONS.defaultImageSize,
    defaultVideoSize: raw.defaultVideoSize ?? FALLBACK_GENERATION_OPTIONS.defaultVideoSize,
    defaultVideoDurationSeconds: raw.defaultVideoDurationSeconds ?? FALLBACK_GENERATION_OPTIONS.defaultVideoDurationSeconds,
  };
}

function filterByVideoModel<T extends { supportedModels?: string[] }>(items: T[], model: string): T[] {
  const normalizedModel = model.trim();
  if (!normalizedModel) {
    return items;
  }
  const filtered = items.filter((item) => !item.supportedModels?.length || item.supportedModels.includes(normalizedModel));
  return filtered.length ? filtered : items;
}

function asBool(value: unknown, fallback = false) {
  if (typeof value === "boolean") {
    return value;
  }
  return fallback;
}

function stageStateLabel(state: FlowStageState) {
  if (state === "completed") {
    return "已完成";
  }
  if (state === "running") {
    return "进行中";
  }
  if (state === "error") {
    return "出错";
  }
  return "待开始";
}

function parseTimestampMs(value: string | undefined | null) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatElapsedMs(value: number | null | undefined) {
  if (value === null || value === undefined || value <= 0) {
    return "--";
  }
  const totalSeconds = Math.max(0, Math.round(value / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
  }
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function findLastReachedStageIndex(stages: FlowStageView[]) {
  for (let index = stages.length - 1; index >= 0; index -= 1) {
    if (stages[index].state !== "pending") {
      return index;
    }
  }
  return -1;
}

function buildFlowDefinitions(agentId: AgentId, input: Record<string, unknown>) {
  const definitions: FlowStageDefinition[] = [];
  if (agentId === "ai-drama") {
    definitions.push(
      {
        key: "accepted",
        label: "任务受理",
        description: "接收正文、风格和全局成片约束。",
        match: (event) => event.event === "run.accepted" || event.stage === "api",
      },
      {
        key: "direction",
        label: "导演决策",
        description: "判断视觉风格、镜头规模、总时长、片头片尾和转场策略。",
        match: (event) => event.stage === "showrunner" && event.event === "direction.decided",
      },
      {
        key: "script",
        label: "脚本编排",
        description: "生成角色档案、场景锚点和分镜脚本。",
        match: (event) => event.stage === "script-writer",
      },
      {
        key: "consistency",
        label: "一致性锁定",
        description: "锁定角色锚点、统一视觉风格和 continuity seed。",
        match: (event) => event.stage === "consistency-director",
      },
      {
        key: "media",
        label: "镜头生成",
        description: "生成关键帧与镜头视频素材。",
        match: (event) => event.stage === "media-artist",
      },
      {
        key: "stitch",
        label: "成片拼接",
        description: "统一转场节奏并输出最终 AI 剧成片。",
        match: (event) => event.stage === "stitch-algorithm",
      }
    );
    if (asBool(input.includeDubPlan, aiDramaDraft.includeDubPlan)) {
      definitions.push({
        key: "voice",
        label: "配音规划",
        description: "给出对白节奏与 AI 配音建议。",
        match: (event) => event.stage === "voice-director",
      });
    }
    if (asBool(input.includeLipsyncPlan, aiDramaDraft.includeLipsyncPlan)) {
      definitions.push({
        key: "lipsync",
        label: "口型规划",
        description: "生成角色口型绑定与驱动计划。",
        match: (event) => event.stage === "lipsync-agent",
      });
    }
  } else if (agentId === "drama-editor") {
    definitions.push(
      {
        key: "accepted",
        label: "任务受理",
        description: "接收素材、平台和投放约束。",
        match: (event) => event.stage === "api" || event.stage === "dispatch",
      },
      {
        key: "analysis",
        label: "素材理解",
        description: "分析素材、字幕和上下文语义。",
        match: (event) => ["pipeline", "source", "transcript", "semantic"].includes(event.stage),
      },
      {
        key: "planning",
        label: "分镜规划",
        description: "产出混剪或短剧剪辑时间线计划。",
        match: (event) => event.stage.includes("planning") || event.event.includes("plan"),
      },
      {
        key: "render",
        label: "成片输出",
        description: "渲染片段并输出最终成片文件。",
        match: (event) => event.stage.includes("render") || event.stage.includes("output") || event.event.includes("render"),
      }
    );
  } else if (agentId === "visual-lab") {
    definitions.push(
      {
        key: "accepted",
        label: "请求接入",
        description: "接收提示词和尺寸参数。",
        match: (event) => event.event === "run.accepted" || event.stage === "request" || event.stage === "api",
      },
      {
        key: "prompt",
        label: "提示词整形",
        description: "把用户提示词整理成稳定的生成提示。",
        match: (event) => event.stage === "prompt",
      },
      {
        key: "provider",
        label: "模型生成",
        description: "调用模型完成图片或视频生成。",
        match: (event) => ["remote_request", "remote_response", "media_extract"].includes(event.stage),
      },
      {
        key: "output",
        label: "产物落盘",
        description: "保存媒体文件并回传下载地址。",
        match: (event) => event.stage === "output" || event.stage === "generation",
      }
    );
  } else {
    definitions.push(
      {
        key: "accepted",
        label: "请求接入",
        description: "接收故事正文与视觉风格要求。",
        match: (event) => event.event === "run.accepted" || event.stage === "request" || event.stage === "api",
      },
      {
        key: "directing",
        label: "导演生成",
        description: "调度大模型生成角色与分镜脚本。",
        match: (event) => ["remote_request", "remote_response"].includes(event.stage),
      },
      {
        key: "markdown",
        label: "Markdown 整理",
        description: "抽取并整理最终 Markdown 脚本。",
        match: (event) => event.stage === "response_extract",
      },
      {
        key: "delivery",
        label: "脚本交付",
        description: "写入脚本文件并生成下载产物。",
        match: () => false,
      }
    );
  }

  definitions.push({
    key: "delivery",
    label: agentId === "script-director" ? "脚本交付" : "结果交付",
    description: agentId === "script-director" ? "写入 Markdown 并准备下载。" : "归档运行结果并写入历史。",
    match: () => false,
  });

  const unique = new Map<string, FlowStageDefinition>();
  for (const definition of definitions) {
    unique.set(definition.key, definition);
  }
  return Array.from(unique.values());
}

function summarizeProgress(
  agentId: AgentId,
  run: AgentRunDetail | null,
  fallbackInput: Record<string, unknown>,
  pending: PendingRunState | null,
  now: number,
  submitMessage: string,
) {
  const input = (run?.input ?? fallbackInput) as Record<string, unknown>;
  const definitions = buildFlowDefinitions(agentId, input);
  const events = [...(run?.events ?? [])].sort((left, right) => {
    const leftMs = parseTimestampMs(left.timestamp) ?? 0;
    const rightMs = parseTimestampMs(right.timestamp) ?? 0;
    return leftMs - rightMs;
  });
  const runStartedMs = parseTimestampMs(run?.createdAt) ?? pending?.startedMs ?? now;
  const runFinishedMs = run && run.status !== "queued" && run.status !== "running" ? parseTimestampMs(run.updatedAt) ?? now : now;
  const stages: FlowStageView[] = definitions.map((definition) => ({
    key: definition.key,
    label: definition.label,
    description: definition.description,
    state: "pending",
    stateLabel: stageStateLabel("pending"),
    elapsedMs: null,
    elapsedLabel: "--",
    startedMs: null,
    finishedMs: null,
    message: "",
  }));

  for (const event of events) {
    const stageIndex = definitions.findIndex((definition) => definition.match(event));
    if (stageIndex < 0) {
      continue;
    }
    const stage = stages[stageIndex];
    const eventMs = parseTimestampMs(event.timestamp) ?? runStartedMs;
    if (stage.startedMs === null) {
      stage.startedMs = eventMs;
    }
    stage.finishedMs = eventMs;
    stage.message = event.message || stage.message;
    stage.state = event.level === "error" ? "error" : "completed";
  }

  let reachedIndex = findLastReachedStageIndex(stages);
  if (reachedIndex < 0 && pending) {
    reachedIndex = 0;
  }

  if (run?.status === "completed") {
    for (let index = 0; index < stages.length; index += 1) {
      if (stages[index].state === "pending") {
        stages[index].state = "completed";
      }
    }
  } else if (run?.status === "failed") {
    const errorIndex = stages.findIndex((stage) => stage.state === "error");
    const targetIndex = errorIndex >= 0 ? errorIndex : Math.min(Math.max(reachedIndex, 0), stages.length - 1);
    stages[targetIndex].state = "error";
    stages[targetIndex].message = stages[targetIndex].message || run.summary || submitMessage || "运行失败";
  } else if (pending || run?.status === "running" || run?.status === "queued") {
    const targetIndex = Math.min(Math.max(reachedIndex + 1, 0), stages.length - 1);
    if (stages[targetIndex].state === "pending") {
      stages[targetIndex].state = "running";
    }
    if (stages[targetIndex].startedMs === null) {
      stages[targetIndex].startedMs = stages[Math.max(0, targetIndex - 1)].finishedMs ?? runStartedMs;
    }
  }

  let previousFinishedMs = runStartedMs;
  for (const stage of stages) {
    if (stage.startedMs === null && stage.state !== "pending") {
      stage.startedMs = previousFinishedMs;
    }
    if (stage.finishedMs === null) {
      if (stage.state === "completed" || stage.state === "error") {
        stage.finishedMs = runFinishedMs;
      } else if (stage.state === "running") {
        stage.finishedMs = now;
      }
    }
    if (stage.finishedMs !== null) {
      previousFinishedMs = stage.finishedMs;
    }
    stage.elapsedMs = stage.startedMs !== null && stage.finishedMs !== null ? Math.max(0, stage.finishedMs - stage.startedMs) : null;
    if (stage.state === "running" && stage.startedMs !== null) {
      stage.elapsedMs = Math.max(0, now - stage.startedMs);
    }
    stage.stateLabel = stageStateLabel(stage.state);
    stage.elapsedLabel = stage.state === "pending" ? "--" : formatElapsedMs(stage.elapsedMs);
  }

  const currentStage =
    stages.find((stage) => stage.state === "running") ??
    stages.find((stage) => stage.state === "error") ??
    [...stages].reverse().find((stage) => stage.state === "completed") ??
    stages[0];

  const totalElapsedMs = pending ? Math.max(0, now - pending.startedMs) : Math.max(0, runFinishedMs - runStartedMs);
  const errorMessage =
    submitMessage ||
    stages.find((stage) => stage.state === "error")?.message ||
    (run?.status === "failed" ? run.summary : "");

  return {
    stages,
    totalElapsedMs,
    currentStageLabel: currentStage?.label || "未开始",
    currentStageElapsedMs: currentStage?.state === "pending" ? null : currentStage?.elapsedMs ?? totalElapsedMs,
    errorMessage,
  };
}

const availableStylePresets = computed(() => generationOptions.value.stylePresets);
const availableVideoModels = computed(() =>
  generationOptions.value.videoModels.length ? generationOptions.value.videoModels : FALLBACK_GENERATION_OPTIONS.videoModels
);
const availableVideoSizes = computed(() =>
  filterByVideoModel(
    generationOptions.value.videoSizes.length ? generationOptions.value.videoSizes : FALLBACK_GENERATION_OPTIONS.videoSizes,
    visualDraft.providerModel
  )
);
const availableVideoDurations = computed(() =>
  filterByVideoModel(
    generationOptions.value.videoDurations.length ? generationOptions.value.videoDurations : FALLBACK_GENERATION_OPTIONS.videoDurations,
    visualDraft.providerModel
  )
);
const versionOptions = computed(() =>
  generationOptions.value.versions.map((version) => {
    const detail = generationOptions.value.versionDetails?.find((item) => item.version === version);
    return {
      version,
      label: detail ? `v${version} · ${detail.label}` : `v${version}`,
    };
  })
);
const selectedAgent = computed(() => getAgentDefinition(selectedAgentId.value));
const selectedVideoModel = computed(
  () => availableVideoModels.value.find((item) => item.value === visualDraft.providerModel) ?? null
);
const historyEntries = computed<Array<AgentRunDetail | AgentRunSummary>>(() => {
  const map = new Map<string, AgentRunDetail | AgentRunSummary>();
  for (const run of remoteRuns.value) {
    map.set(run.id, run);
  }
  for (const run of persistedRuns.value) {
    map.set(run.id, run);
  }
  return Array.from(map.values()).sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));
});
const activeRun = computed(() => selectedRunDetail.value);
const runtimeStatusLabel = computed(() => {
  if (runBusy.value && pendingRun.value?.agentId === selectedAgentId.value) {
    return "running";
  }
  return activeRun.value?.status || "idle";
});

function currentProgressInput() {
  if (selectedAgentId.value === "ai-drama") {
    return {
      includeDubPlan: aiDramaDraft.includeDubPlan,
      includeLipsyncPlan: aiDramaDraft.includeLipsyncPlan,
    };
  }
  return {};
}

const progressSummary = computed(() =>
  summarizeProgress(
    selectedAgentId.value,
    pendingRun.value?.agentId === selectedAgentId.value ? null : activeRun.value,
    currentProgressInput(),
    pendingRun.value?.agentId === selectedAgentId.value ? pendingRun.value : null,
    nowMs.value,
    submitError.value
  )
);
const progressStages = computed(() => progressSummary.value.stages);
const progressTotalRuntimeLabel = computed(() => formatElapsedMs(progressSummary.value.totalElapsedMs));
const progressCurrentStageLabel = computed(() => progressSummary.value.currentStageLabel);
const progressCurrentStageElapsedLabel = computed(() => formatElapsedMs(progressSummary.value.currentStageElapsedMs));
const progressErrorMessage = computed(() => progressSummary.value.errorMessage);

const previewArtifact = computed<AgentRunArtifact | null>(() => {
  if (!activeRun.value?.artifacts?.length) {
    return null;
  }
  const artifacts = activeRun.value.artifacts;
  if (selectedAgentId.value === "ai-drama") {
    return (
      artifacts.find((item) => item.label.includes("成片") || item.label.includes("拼接")) ??
      artifacts.find((item) => item.kind === "video") ??
      artifacts.find((item) => item.kind === "image") ??
      artifacts.find((item) => item.kind === "markdown") ??
      artifacts[0] ??
      null
    );
  }
  if (selectedAgentId.value === "visual-lab") {
    return (
      artifacts.find((item) => item.kind === "image") ??
      artifacts.find((item) => item.kind === "video") ??
      artifacts.find((item) => item.url) ??
      artifacts[0] ??
      null
    );
  }
  if (selectedAgentId.value === "script-director") {
    return (
      artifacts.find((item) => item.kind === "markdown") ??
      artifacts.find((item) => Boolean(item.text)) ??
      artifacts[0] ??
      null
    );
  }
  return artifacts.find((item) => ["image", "video", "markdown"].includes(item.kind)) ?? artifacts[0] ?? null;
});

const previewKind = computed(() => {
  const artifact = previewArtifact.value;
  const output = activeRun.value?.output ?? {};
  const outputUrl = typeof output.outputUrl === "string" ? output.outputUrl : typeof output.finalVideoUrl === "string" ? output.finalVideoUrl : "";
  const outputKind = typeof output.kind === "string" ? output.kind : typeof output.mediaKind === "string" ? output.mediaKind : "";
  const outputMimeType = typeof output.mimeType === "string" ? output.mimeType : "";
  const markdownText = typeof output.scriptMarkdown === "string"
    ? output.scriptMarkdown
    : typeof output.outputText === "string"
      ? output.outputText
      : "";
  if (!artifact) {
    if (selectedAgentId.value === "ai-drama") {
      if (outputKind === "video" || outputMimeType.startsWith("video/") || /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(outputUrl)) {
        return "video";
      }
      if (markdownText.trim()) {
        return "markdown";
      }
    }
    if (selectedAgentId.value === "visual-lab") {
      if (outputKind === "video" || outputMimeType.startsWith("video/") || /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(outputUrl)) {
        return "video";
      }
      if (outputKind === "image" || outputMimeType.startsWith("image/") || /\.(png|jpe?g|webp|gif|avif)(\?|#|$)/i.test(outputUrl)) {
        return "image";
      }
    }
    if (selectedAgentId.value === "script-director" && markdownText.trim()) {
      return "markdown";
    }
    return "none";
  }
  if (artifact.kind === "image") {
    return "image";
  }
  if (artifact.kind === "video") {
    return "video";
  }
  if (artifact.kind === "markdown") {
    return "markdown";
  }
  if (selectedAgentId.value === "ai-drama") {
    if (outputKind === "video" || outputMimeType.startsWith("video/") || /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(outputUrl)) {
      return "video";
    }
    if (markdownText.trim()) {
      return "markdown";
    }
  }
  if (selectedAgentId.value === "visual-lab") {
    if (outputKind === "video" || outputMimeType.startsWith("video/") || /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(outputUrl)) {
      return "video";
    }
    if (outputKind === "image" || outputMimeType.startsWith("image/") || /\.(png|jpe?g|webp|gif|avif)(\?|#|$)/i.test(outputUrl)) {
      return "image";
    }
  }
  if (selectedAgentId.value === "script-director" && markdownText.trim()) {
    return "markdown";
  }
  return "none";
});

const resolvedPreviewUrl = computed(() => {
  const artifact = previewArtifact.value;
  const output = activeRun.value?.output ?? {};
  const outputUrl = typeof output.outputUrl === "string" ? output.outputUrl : typeof output.finalVideoUrl === "string" ? output.finalVideoUrl : "";
  const url = artifact?.url || outputUrl;
  if (!url) {
    return "";
  }
  return resolveRuntimeUrl(url, getRuntimeConfig().storageBaseUrl);
});

const previewMarkdown = computed(() => {
  const artifact = previewArtifact.value;
  if (artifact?.kind === "markdown" && artifact.text) {
    return artifact.text;
  }
  const output = activeRun.value?.output ?? {};
  const outputMarkdown = typeof output.scriptMarkdown === "string" ? output.scriptMarkdown : "";
  const outputText = typeof output.outputText === "string" ? output.outputText : "";
  return outputMarkdown || outputText || artifact?.text || "";
});
const renderedMarkdown = computed(() => renderMarkdown(previewMarkdown.value));
const dramaFileNames = computed(() => dramaDraft.sourceFiles.map((file) => file.name));

const submitHint = computed(() => {
  if (selectedAgentId.value === "ai-drama") {
    return "总控 Agent 会自动决定视觉风格、镜头规模、节奏、转场和成片包装，并遵守总时长约束。";
  }
  if (selectedAgentId.value === "drama-editor") {
    return dramaDraft.sourceFiles.length > 1 ? "多文件会自动切到 mixcut 轨道。" : "上传素材后会先生成创意提示词，再创建任务。";
  }
  if (selectedAgentId.value === "visual-lab") {
    return visualDraft.mediaKind === "image"
      ? "图像输出会优先渲染预览图。"
      : `视频输出会使用 ${visualDraft.providerModel || "默认视频模型"} 生成 MP4 结果。`;
  }
  return "脚本 Agent 会强制输出 Markdown 角色档案 + 分镜表。";
});

const runDisabled = computed(() => {
  if (runBusy.value) {
    return true;
  }
  if (selectedAgentId.value === "ai-drama") {
    return !aiDramaDraft.title.trim() || !aiDramaDraft.text.trim();
  }
  if (selectedAgentId.value === "drama-editor") {
    return !dramaDraft.title.trim() || dramaDraft.sourceFiles.length === 0;
  }
  if (selectedAgentId.value === "visual-lab") {
    return !visualDraft.prompt.trim();
  }
  return !scriptDraft.text.trim();
});

const runLabel = computed(() => {
  if (runBusy.value) {
    return "Running...";
  }
  if (selectedAgentId.value === "ai-drama") {
    return "一键生成 AI 剧";
  }
  if (selectedAgentId.value === "drama-editor") {
    return "启动短剧 Agent";
  }
  if (selectedAgentId.value === "visual-lab") {
    return "启动视觉 Agent";
  }
  return "启动脚本 Agent";
});

function prettyJson(value: unknown) {
  if (value === undefined || value === null) {
    return "{}";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(value: string) {
  const escaped = escapeHtml(value);
  return escaped
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label: string, rawUrl: string) => {
      const safeUrl = sanitizeMarkdownUrl(rawUrl);
      return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>`;
    });
}

function sanitizeMarkdownUrl(rawUrl: string) {
  const trimmed = rawUrl.trim();
  if (/^(https?:|mailto:|\/|#|\.)/i.test(trimmed)) {
    return escapeHtml(trimmed);
  }
  return "#";
}

function renderMarkdown(input: string) {
  const lines = input.replace(/\r\n/g, "\n").split("\n");
  const blocks: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !(lines[index] ?? "").trim().startsWith("```")) {
        codeLines.push(lines[index] ?? "");
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push(`<pre class="md-code"><code data-language="${escapeHtml(language)}">${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    const nextLine = lines[index + 1] ?? "";
    const isTableSeparator = /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(nextLine);
    if (trimmed.includes("|") && isTableSeparator) {
      const tableLines: string[] = [line, nextLine];
      index += 2;
      while (index < lines.length) {
        const current = lines[index] ?? "";
        const currentTrimmed = current.trim();
        if (!currentTrimmed || !currentTrimmed.includes("|")) {
          break;
        }
        tableLines.push(current);
        index += 1;
      }
      const headerCells = splitMarkdownRow(tableLines[0] ?? "");
      const bodyRows = tableLines.slice(2).map((row) => splitMarkdownRow(row));
      blocks.push(
        [
          '<div class="md-table-wrap"><table class="md-table">',
          `<thead><tr>${headerCells.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>`,
          `<tbody>${bodyRows.map((cells) => `<tr>${cells.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("")}</tbody>`,
          "</table></div>",
        ].join("")
      );
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2] ?? "")}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^[-*+]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (index < lines.length) {
        const current = (lines[index] ?? "").trim();
        if (!/^[-*+]\s+/.test(current)) {
          break;
        }
        items.push(current.replace(/^[-*+]\s+/, ""));
        index += 1;
      }
      blocks.push(`<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`);
      continue;
    }

    const paragraphLines: string[] = [line];
    index += 1;
    while (index < lines.length) {
      const current = lines[index] ?? "";
      const currentTrimmed = current.trim();
      if (!currentTrimmed || currentTrimmed.startsWith("```") || /^#{1,6}\s+/.test(currentTrimmed) || /^[-*+]\s+/.test(currentTrimmed) || currentTrimmed.includes("|")) {
        break;
      }
      paragraphLines.push(current);
      index += 1;
    }
    blocks.push(`<p>${renderInlineMarkdown(paragraphLines.join(" ").trim())}</p>`);
  }

  return blocks.join("");
}

function splitMarkdownRow(row: string) {
  return row
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function formatDate(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}

function agentStatusLabel(agentId: AgentId) {
  const latest = historyEntries.value.find((entry) => entry.agentId === agentId);
  return latest ? latest.status : "idle";
}

function isTerminalRunStatus(status: AgentRunSummary["status"] | AgentRunDetail["status"] | undefined) {
  return status === "completed" || status === "failed" || status === "idle";
}

function selectedHistoryEntry() {
  return selectedRunId.value ? historyEntries.value.find((entry) => entry.id === selectedRunId.value) ?? null : null;
}

async function refreshSelectedRunDetail() {
  const entry = selectedHistoryEntry();
  if (!entry) {
    return;
  }

  const shouldFetch =
    !selectedRunDetail.value ||
    selectedRunDetail.value.id !== entry.id ||
    selectedRunDetail.value.updatedAt !== entry.updatedAt ||
    selectedRunDetail.value.progress !== entry.progress ||
    !isTerminalRunStatus(entry.status) ||
    !isTerminalRunStatus(selectedRunDetail.value.status);

  if (!shouldFetch) {
    return;
  }

  const detail = await fetchAgentRun(entry.id);
  persistedRuns.value = upsertAgentRun(detail);
  selectedRunDetail.value = detail;
}

async function refreshWorkspace(showLoading = false) {
  if (showLoading) {
    loading.value = true;
  } else {
    refreshing.value = true;
  }
  try {
    const [runsResult, generationResult] = await Promise.all([
      fetchAgentRuns().catch(() => []),
      fetchGenerationOptions().catch(() => null),
    ]);
    remoteRuns.value = runsResult;
    generationOptions.value = normalizeGenerationOptions(generationResult);
    persistedRuns.value = getPersistedRuns();
    syncAgentDefaults();
    await syncSelectionAfterRefresh();
    await refreshSelectedRunDetail();
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "加载工作台失败";
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}

function syncAgentDefaults() {
  const availableVersions = generationOptions.value.versions;
  if (!availableVersions.includes(visualDraft.version)) {
    visualDraft.version = generationOptions.value.defaultVersion ?? availableVersions[0] ?? 1;
  }
  if (!generationOptions.value.stylePresets.some((preset) => preset.key === visualDraft.stylePreset)) {
    visualDraft.stylePreset = generationOptions.value.defaultStylePreset || "";
  }
  const imageSizes = generationOptions.value.imageSizes.map((item) => item.value);
  if (!imageSizes.includes(visualDraft.imageSize)) {
    visualDraft.imageSize = generationOptions.value.defaultImageSize || imageSizes[0] || "1024x1024";
  }
  const sizes = availableVideoSizes.value.map((item) => item.value);
  if (!sizes.includes(visualDraft.videoSize)) {
    visualDraft.videoSize = generationOptions.value.defaultVideoSize || sizes[0] || "1080x1920";
  }
  const durations = availableVideoDurations.value.map((item) => item.value);
  if (!durations.includes(visualDraft.videoDurationSeconds)) {
    visualDraft.videoDurationSeconds = generationOptions.value.defaultVideoDurationSeconds || durations[0] || 6;
  }
}

async function syncSelectionAfterRefresh() {
  if (selectedHistoryEntry()) {
    return;
  }
  const fallback = historyEntries.value.find((entry) => entry.agentId === selectedAgentId.value);
  if (fallback) {
    await openHistoryEntry(fallback);
    return;
  }
  selectedRunDetail.value = null;
  selectedRunId.value = "";
}

async function handleSelectAgent(agentId: string) {
  if (!isAgentId(agentId)) {
    return;
  }
  selectedAgentId.value = agentId;
  const latest = historyEntries.value.find((entry) => entry.agentId === agentId) ?? null;
  if (latest) {
    await openHistoryEntry(latest);
  } else {
    selectedRunDetail.value = null;
    selectedRunId.value = "";
  }
  await router.replace({ path: "/studio", query: { ...route.query, agent: agentId, run: selectedRunId.value || undefined } });
}

async function openHistoryEntry(entry: AgentRunDetail | AgentRunSummary) {
  selectedAgentId.value = entry.agentId;
  selectedRunId.value = entry.id;
  if ("events" in entry && entry.events.length) {
    selectedRunDetail.value = entry;
    await router.replace({ path: "/studio", query: { ...route.query, agent: entry.agentId, run: entry.id } });
    return;
  }
  const detail = await fetchAgentRun(entry.id);
  persistedRuns.value = upsertAgentRun(detail);
  selectedRunDetail.value = detail;
  await router.replace({ path: "/studio", query: { ...route.query, agent: entry.agentId, run: entry.id } });
}

function latestRunForAgent(agentId: AgentId) {
  return historyEntries.value.find((entry) => entry.agentId === agentId) ?? null;
}

function resetDraft() {
  submitError.value = "";
  if (selectedAgentId.value === "ai-drama") {
    aiDramaDraft.title = "暴雨车站";
    aiDramaDraft.text = "";
    aiDramaDraft.totalDurationSeconds = 24;
  } else if (selectedAgentId.value === "drama-editor") {
    dramaDraft.creativePrompt = "";
    dramaDraft.transcriptText = "";
    dramaDraft.sourceFiles = [];
  } else if (selectedAgentId.value === "visual-lab") {
    visualDraft.prompt = selectedAgent.value.defaultPrompt;
  } else {
    scriptDraft.text = "";
    scriptDraft.visualStyle = "";
  }
}

function handleDramaFiles(event: Event) {
  const input = event.target as HTMLInputElement | null;
  dramaDraft.sourceFiles = input?.files ? Array.from(input.files) : [];
}

async function handleAIDramaTextFile(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (!file) {
    return;
  }
  try {
    aiDramaDraft.text = await file.text();
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "TXT 文件读取失败";
  } finally {
    if (input) {
      input.value = "";
    }
  }
}

function parseImageSize(size: string) {
  const match = size.trim().match(/^(\d+)\s*[xX]\s*(\d+)$/);
  if (!match) {
    return { width: 1024, height: 1024 };
  }
  return {
    width: Number(match[1]) || 1024,
    height: Number(match[2]) || 1024,
  };
}

async function handleRun() {
  if (runDisabled.value) {
    return;
  }
  runBusy.value = true;
  submitError.value = "";
  pendingRun.value = {
    agentId: selectedAgentId.value,
    title: selectedAgent.value.name,
    startedMs: Date.now(),
  };
  try {
    let detail: AgentRunDetail;
    if (selectedAgentId.value === "ai-drama") {
      const totalDurationSeconds =
        typeof aiDramaDraft.totalDurationSeconds === "number" && Number.isFinite(aiDramaDraft.totalDurationSeconds)
          ? aiDramaDraft.totalDurationSeconds
          : null;
      detail = await runAIDramaAgent({
        title: aiDramaDraft.title.trim(),
        text: aiDramaDraft.text.trim(),
        aspectRatio: aiDramaDraft.aspectRatio,
        continuitySeed: aiDramaDraft.continuitySeed,
        totalDurationSeconds,
        includeKeyframes: aiDramaDraft.includeKeyframes,
        includeDubPlan: aiDramaDraft.includeDubPlan,
        includeLipsyncPlan: aiDramaDraft.includeLipsyncPlan,
      });
    } else if (selectedAgentId.value === "drama-editor") {
      detail = await runDramaAgent({
        title: dramaDraft.title.trim(),
        sourceFiles: dramaDraft.sourceFiles,
        platform: dramaDraft.platform,
        aspectRatio: dramaDraft.aspectRatio,
        minDurationSeconds: dramaDraft.minDurationSeconds,
        maxDurationSeconds: dramaDraft.maxDurationSeconds,
        outputCount: dramaDraft.outputCount,
        introTemplate: dramaDraft.introTemplate,
        outroTemplate: dramaDraft.outroTemplate,
        creativePrompt: dramaDraft.creativePrompt.trim(),
        transcriptText: dramaDraft.transcriptText.trim(),
        editingMode: dramaDraft.sourceFiles.length > 1 ? "mixcut" : dramaDraft.editingMode,
        mixcutContentType: dramaDraft.mixcutContentType,
        mixcutStylePreset: dramaDraft.mixcutStylePreset,
      });
    } else if (selectedAgentId.value === "visual-lab") {
      detail = await runVisualAgent(selectedAgentId.value, {
        prompt: visualDraft.prompt.trim(),
        mediaKind: visualDraft.mediaKind,
        version: visualDraft.version,
        stylePreset: visualDraft.stylePreset,
        imageSize: visualDraft.mediaKind === "image" ? visualDraft.imageSize : visualDraft.videoSize,
        videoDurationSeconds: visualDraft.videoDurationSeconds,
      });
    } else {
      detail = await runScriptAgent(selectedAgentId.value, {
        text: scriptDraft.text.trim(),
        visualStyle: scriptDraft.visualStyle.trim(),
      });
    }
    persistedRuns.value = getPersistedRuns();
    selectedRunDetail.value = detail;
    selectedRunId.value = detail.id;
    await router.replace({ path: "/studio", query: { ...route.query, agent: selectedAgentId.value, run: detail.id } });
    await refreshWorkspace(false);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "Agent 运行失败";
  } finally {
    pendingRun.value = null;
    runBusy.value = false;
  }
}

function getMarkdownDownloadName() {
  const title = activeRun.value?.title || selectedAgent.value.name || "script";
  return `${title.replace(/[\\/:*?"<>|]+/g, "_")}.md`;
}

function downloadMarkdown() {
  const markdown = previewMarkdown.value;
  if (!markdown) {
    return;
  }
  const anchor = document.createElement("a");
  anchor.download = getMarkdownDownloadName();
  if (previewArtifact.value?.url) {
    anchor.href = resolveRuntimeUrl(previewArtifact.value.url, getRuntimeConfig().storageBaseUrl);
  } else {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    anchor.href = url;
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

const poll = usePolling(() => refreshWorkspace(false), 7000);

watch(
  () => route.query.agent,
  async (value) => {
    const next = currentAgentIdFromQuery(value);
    if (next !== selectedAgentId.value) {
      selectedAgentId.value = next;
      const latest = latestRunForAgent(next);
      if (latest) {
        await openHistoryEntry(latest);
      }
    }
  },
  { immediate: true }
);

watch(
  () => route.query.run,
  async (value) => {
    if (typeof value !== "string" || !value.trim()) {
      return;
    }
    const run = historyEntries.value.find((entry) => entry.id === value.trim());
    if (run) {
      await openHistoryEntry(run);
    }
  },
  { immediate: true }
);

watch(
  () => historyEntries.value.length,
  () => {
    if (!selectedRunDetail.value) {
      const latest = latestRunForAgent(selectedAgentId.value);
      if (latest) {
        void openHistoryEntry(latest);
      }
    }
  }
);

onMounted(async () => {
  clockTimer = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 1000);
  await refreshWorkspace(true);
  await poll.start(false);
  const initialRun = historyEntries.value.find((entry) => entry.id === selectedRunId.value) ?? latestRunForAgent(selectedAgentId.value);
  if (initialRun) {
    await openHistoryEntry(initialRun);
  }
});

onUnmounted(() => {
  if (clockTimer !== null) {
    window.clearInterval(clockTimer);
    clockTimer = null;
  }
});
</script>

<style scoped>
.studio-page {
  display: grid;
  grid-template-columns: 18rem minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}

.agent-rail,
.console-panel,
.hero-card,
.progress-card {
  border: 1px solid rgba(206, 214, 226, 0.92);
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 40px rgba(148, 163, 184, 0.12);
}

.agent-rail {
  position: sticky;
  top: 5.75rem;
  display: grid;
  gap: 1rem;
  padding: 1rem;
  transition: width 220ms ease, padding 220ms ease, transform 220ms ease;
}

.agent-rail-collapsed {
  width: 5.5rem;
  padding-inline: 0.8rem;
}

.agent-rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.agent-rail-title {
  margin: 0;
  color: #122033;
  font-size: 1.1rem;
}

.rail-toggle {
  border: 1px solid #d6deea;
  border-radius: 999px;
  background: #f8fafc;
  padding: 0.46rem 0.8rem;
  color: #475569;
  font-size: 0.78rem;
  font-weight: 700;
  transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.rail-toggle:hover {
  transform: translateY(-1px);
  background: #fff;
  box-shadow: 0 10px 22px rgba(148, 163, 184, 0.16);
}

.agent-rail-list {
  display: grid;
  gap: 0.72rem;
}

.agent-rail-item {
  display: grid;
  grid-template-columns: 2.7rem minmax(0, 1fr);
  gap: 0.85rem;
  align-items: center;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 1.2rem;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 0.8rem;
  text-align: left;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

.agent-rail-collapsed .agent-rail-item {
  grid-template-columns: 1fr;
  justify-items: center;
}

.agent-rail-item:hover {
  transform: translateY(-2px);
  border-color: rgba(191, 219, 254, 0.92);
  box-shadow: 0 14px 28px rgba(148, 163, 184, 0.14);
}

.agent-rail-item-active {
  border-color: color-mix(in srgb, var(--agent-accent) 24%, #d7e3f3);
  background: linear-gradient(180deg, color-mix(in srgb, var(--agent-accent-soft) 60%, #ffffff), #ffffff);
  box-shadow: 0 18px 32px rgba(79, 124, 255, 0.14);
}

.agent-rail-icon {
  display: grid;
  place-items: center;
  width: 2.7rem;
  height: 2.7rem;
  border-radius: 1rem;
  background: color-mix(in srgb, var(--agent-accent-soft) 86%, white);
  color: #122033;
  font-weight: 800;
}

.agent-rail-copy {
  min-width: 0;
}

.agent-rail-copy-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.agent-rail-copy strong {
  color: #122033;
  font-size: 0.92rem;
}

.agent-rail-copy p,
.agent-rail-status {
  margin: 0.28rem 0 0;
  color: #64748b;
  font-size: 0.75rem;
}

.studio-content {
  display: grid;
  gap: 1.25rem;
}

.hero-card,
.progress-card,
.console-panel {
  padding: 1.2rem;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.hero-title {
  margin: 0.08rem 0 0;
  color: #122033;
  font-size: clamp(1.8rem, 3vw, 2.8rem);
  line-height: 1.02;
}

.hero-description {
  margin: 0.7rem 0 0;
  max-width: 46rem;
  color: #5f6f86;
  line-height: 1.7;
}

.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: flex-end;
}

.hero-badge {
  border: 1px solid color-mix(in srgb, var(--agent-accent) 18%, #d6deea);
  border-radius: 999px;
  background: color-mix(in srgb, var(--agent-accent) 10%, #ffffff);
  padding: 0.48rem 0.78rem;
  color: #244160;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.hero-badge-soft {
  border-color: #d6deea;
  background: #f8fafc;
  color: #64748b;
}

.section-eyebrow {
  margin: 0 0 0.4rem;
  color: #6b7b92;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.section-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.section-title {
  margin: 0;
  color: #122033;
  font-size: 1.15rem;
}

.progress-metrics {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-card {
  min-width: 8.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 1rem;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 0.8rem 0.95rem;
}

.metric-card span {
  display: block;
  color: #64748b;
  font-size: 0.76rem;
}

.metric-card strong {
  display: block;
  margin-top: 0.35rem;
  color: #122033;
  font-size: 1rem;
}

.flow-track {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
}

.flow-stage {
  position: relative;
}

.flow-stage-line {
  position: absolute;
  top: 1.1rem;
  left: 1.1rem;
  right: -0.6rem;
  height: 2px;
  background: #dbe4ee;
}

.flow-stage:last-child .flow-stage-line {
  display: none;
}

.flow-stage-dot {
  position: absolute;
  top: 0.7rem;
  left: 0.7rem;
  z-index: 1;
  width: 0.9rem;
  height: 0.9rem;
  border: 3px solid #dbe4ee;
  border-radius: 999px;
  background: #fff;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.flow-stage-card {
  height: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 1.2rem;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 1.35rem 1rem 1rem 2.1rem;
}

.flow-stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.flow-stage-head strong {
  color: #122033;
  font-size: 0.92rem;
}

.flow-stage-head span,
.flow-stage-card p,
.flow-stage-card small {
  color: #64748b;
}

.flow-stage-card p {
  margin: 0.55rem 0 0.45rem;
  font-size: 0.84rem;
  line-height: 1.6;
}

.flow-stage-message {
  display: block;
  margin-top: 0.35rem;
}

.flow-stage-completed .flow-stage-dot {
  border-color: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.12);
}

.flow-stage-running .flow-stage-dot {
  border-color: #4f7cff;
  box-shadow: 0 0 0 7px rgba(79, 124, 255, 0.16);
  transform: scale(1.08);
}

.flow-stage-error .flow-stage-dot {
  border-color: #ef4444;
  box-shadow: 0 0 0 7px rgba(239, 68, 68, 0.12);
}

.flow-stage-completed .flow-stage-line,
.flow-stage-running .flow-stage-line,
.flow-stage-error .flow-stage-line {
  background: linear-gradient(90deg, #4f7cff, #2dd4bf);
}

.progress-error,
.form-error {
  margin: 0.9rem 0 0;
  border: 1px solid rgba(239, 68, 68, 0.22);
  border-radius: 1rem;
  background: rgba(254, 242, 242, 0.9);
  padding: 0.8rem 0.95rem;
  color: #b91c1c;
}

.studio-main-grid {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: minmax(0, 0.96fr) minmax(0, 1.04fr);
}

.console-form,
.console-form-stack {
  display: grid;
  gap: 0.95rem;
}

.console-grid-2,
.console-grid-3 {
  display: grid;
  gap: 0.9rem;
}

.console-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.console-grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.console-field {
  display: grid;
  gap: 0.48rem;
}

.console-field > span {
  color: #334155;
  font-size: 0.82rem;
  font-weight: 700;
}

.console-input,
.console-select,
.console-textarea,
.console-file {
  width: 100%;
  border: 1px solid #d6deea;
  border-radius: 1rem;
  background: #fff;
  padding: 0.8rem 0.9rem;
  color: #122033;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.console-input:focus,
.console-select:focus,
.console-textarea:focus {
  outline: none;
  border-color: rgba(79, 124, 255, 0.46);
  box-shadow: 0 0 0 4px rgba(79, 124, 255, 0.12);
}

.console-textarea {
  min-height: 7rem;
  resize: vertical;
}

.console-hint {
  margin: 0;
  color: #64748b;
  font-size: 0.8rem;
  line-height: 1.6;
}

.console-actions,
.console-file-list,
.segmented-shell,
.output-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  align-items: center;
}

.agent-run-button,
.agent-secondary-button,
.btn-segment {
  border-radius: 999px;
  font-weight: 700;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

.agent-run-button {
  border: 1px solid rgba(79, 124, 255, 0.26);
  background: linear-gradient(135deg, #4f7cff, #2dd4bf);
  padding: 0.78rem 1.25rem;
  color: #fff;
  box-shadow: 0 14px 30px rgba(79, 124, 255, 0.22);
}

.agent-run-button:hover:not(:disabled),
.agent-secondary-button:hover,
.btn-segment:hover {
  transform: translateY(-1px);
}

.agent-run-button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
  box-shadow: none;
}

.agent-secondary-button,
.btn-segment {
  border: 1px solid #d6deea;
  background: #f8fafc;
  padding: 0.72rem 1rem;
  color: #475569;
}

.agent-secondary-button:hover,
.btn-segment:hover {
  box-shadow: 0 10px 22px rgba(148, 163, 184, 0.14);
}

.btn-segment-active {
  border-color: rgba(79, 124, 255, 0.24);
  background: rgba(79, 124, 255, 0.1);
  color: #1d4ed8;
}

.soft-pill {
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  background: #f8fafc;
  padding: 0.42rem 0.75rem;
  color: #4b5563;
  font-size: 0.78rem;
}

.output-stack {
  display: grid;
  gap: 1rem;
}

.output-preview {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 1.35rem;
  background: linear-gradient(180deg, #fff, #f8fafc);
  min-height: 18rem;
}

.output-media {
  display: block;
  width: 100%;
  height: auto;
}

.output-empty,
.console-placeholder {
  display: grid;
  place-items: center;
  min-height: 15rem;
  color: #64748b;
  text-align: center;
  line-height: 1.7;
}

.output-meta-grid {
  display: grid;
  gap: 0.8rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.output-meta {
  border: 1px solid #e2e8f0;
  border-radius: 1rem;
  background: #f8fafc;
  padding: 0.8rem 0.9rem;
}

.output-meta span {
  display: block;
  color: #64748b;
  font-size: 0.74rem;
}

.output-meta strong {
  display: block;
  margin-top: 0.35rem;
  color: #122033;
  font-size: 0.86rem;
}

.data-drawer {
  border: 1px solid #e2e8f0;
  border-radius: 1rem;
  background: #f8fafc;
  padding: 0.85rem 0.95rem;
}

.data-drawer summary {
  cursor: pointer;
  color: #334155;
  font-weight: 700;
}

.output-json-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 0.9rem;
}

.output-json-block {
  border: 1px solid #dbe4ee;
  border-radius: 1rem;
  background: #fff;
  padding: 0.9rem;
}

.output-json-block p {
  margin: 0 0 0.55rem;
  color: #475569;
  font-weight: 700;
}

.output-json-block pre {
  margin: 0;
  overflow: auto;
  color: #1e293b;
  font-size: 0.8rem;
  line-height: 1.7;
}

.history-panel {
  overflow: hidden;
}

.history-list {
  display: grid;
  gap: 0.8rem;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
}

.history-item {
  border: 1px solid #dbe4ee;
  border-radius: 1.2rem;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 0.9rem;
  text-align: left;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.history-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 26px rgba(148, 163, 184, 0.16);
}

.history-item-active {
  border-color: rgba(79, 124, 255, 0.3);
  box-shadow: 0 18px 32px rgba(79, 124, 255, 0.14);
}

.history-item-head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.history-item-head strong {
  color: #122033;
}

.history-item-head span {
  border: 1px solid color-mix(in srgb, var(--agent-accent) 20%, #d6deea);
  border-radius: 999px;
  background: color-mix(in srgb, var(--agent-accent) 10%, #ffffff);
  padding: 0.28rem 0.55rem;
  color: #1e3a8a;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
}

.history-item p,
.history-item small {
  color: #64748b;
}

.output-markdown {
  padding: 1.2rem;
  color: #1f2937;
  line-height: 1.8;
}

.output-markdown :deep(h1),
.output-markdown :deep(h2),
.output-markdown :deep(h3),
.output-markdown :deep(h4),
.output-markdown :deep(h5),
.output-markdown :deep(h6) {
  margin: 1rem 0 0.5rem;
  color: #122033;
}

.output-markdown :deep(p) {
  margin: 0.5rem 0;
}

.output-markdown :deep(ul) {
  margin: 0.6rem 0;
  padding-left: 1.2rem;
}

.output-markdown :deep(code) {
  border-radius: 0.45rem;
  background: #eff6ff;
  padding: 0.15rem 0.35rem;
}

.output-markdown :deep(pre) {
  overflow: auto;
  border-radius: 1rem;
  background: #eff6ff;
  padding: 0.9rem;
}

.output-markdown :deep(a) {
  color: #2563eb;
}

.output-markdown :deep(.md-table-wrap) {
  overflow: auto;
}

.output-markdown :deep(.md-table) {
  width: 100%;
  border-collapse: collapse;
}

.output-markdown :deep(.md-table th),
.output-markdown :deep(.md-table td) {
  border: 1px solid #dbe4ee;
  padding: 0.7rem;
  text-align: left;
}

@media (max-width: 1200px) {
  .studio-page {
    grid-template-columns: 1fr;
  }

  .agent-rail {
    position: static;
  }

  .studio-main-grid {
    grid-template-columns: 1fr;
  }

  .progress-metrics,
  .output-meta-grid,
  .output-json-grid,
  .console-grid-3 {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .section-head {
    grid-template-columns: 1fr;
    display: grid;
  }

  .progress-metrics,
  .console-grid-2,
  .history-list {
    grid-template-columns: 1fr;
  }

  .flow-track {
    grid-template-columns: 1fr;
  }
}
</style>

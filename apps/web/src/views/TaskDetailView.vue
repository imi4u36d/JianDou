<template>
  <section class="task-detail-shell">
    <div v-if="errorMessage" class="task-alert">
      <p>{{ errorMessage }}</p>
      <button class="btn-secondary btn-sm" type="button" @click="loadTask">重新加载</button>
    </div>

    <div v-if="loading" class="glass-panel glass-placeholder">
      正在加载任务详情...
    </div>

    <div v-else-if="task" class="glass-panel">
      <header class="glass-hero">
        <div class="hero-copy">
          <div class="hero-title-row">
            <p class="eyebrow">{{ statusHint }}</p>
            <HintBell
              title="详情页说明"
              text="这里只保留当前任务的执行状态、配置摘要和规划结果。更偏帮助性的解释都放在这里。"
              :items="['先看进度和时间线', '再看配置摘要', '最后再检查 planning deck 和输出']"
              align="left"
            />
          </div>
          <h1>{{ task.title || '任务详情' }}</h1>
        </div>
        <div class="hero-actions">
          <button class="button primary" :disabled="actionLoading" type="button" @click="openCloneFlow">复制参数</button>
          <button
            v-if="task.status === 'FAILED'"
            class="button warning"
            :disabled="actionLoading"
            type="button"
            @click="handleRetry"
          >
            失败重试
          </button>
          <button
            class="button danger"
            :disabled="actionLoading || runningTask"
            type="button"
            @click="handleDelete"
          >
            删除任务
          </button>
        </div>
      </header>

      <div class="glass-stats">
        <article>
          <span>进度</span>
          <strong>{{ task.progress }}%</strong>
          <small>{{ completedOutputCount }} / {{ task.outputCount }} 输出</small>
        </article>
        <article>
          <span>输出轨</span>
          <strong>{{ completedOutputCount }}</strong>
          <small>已完成 {{ task.outputCount }} 条</small>
        </article>
        <article>
          <span>时间</span>
          <strong>{{ formatTime(task.startedAt) }}</strong>
          <small>{{ formatTime(task.finishedAt) }}</small>
        </article>
        <article>
          <span>重试</span>
          <strong>{{ task.retryCount ?? 0 }}</strong>
          <small>保留 {{ task.retryCount ?? 0 }} 次</small>
        </article>
      </div>

      <div class="glass-timeline">
        <TimelineStage label="素材分析" description="读取源/切点" :state="getStageState('analysis')" />
        <TimelineStage label="剪辑规划" description="构建剪辑方案" :state="getStageState('planning')" />
        <TimelineStage label="视频渲染" description="渲染输出素材" :state="getStageState('rendering')" />
      </div>

      <div class="glass-config">
        <dl>
          <div>
            <dt>平台 / 比例</dt>
            <dd>{{ task.platform }} · {{ task.aspectRatio }}</dd>
          </div>
          <div>
            <dt>时长 / 输出</dt>
            <dd>{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒 · {{ task.outputCount }} 条</dd>
          </div>
          <div>
            <dt>模式</dt>
            <dd>{{ planningModeSummary.label }}</dd>
          </div>
          <div>
            <dt>语义</dt>
            <dd>{{ task.hasTranscript ? (task.hasTimedTranscript ? '带时间戳字幕' : '文本语义') : '无' }}</dd>
          </div>
        </dl>
        <div class="config-row">
          <div>
            <p class="label">主素材</p>
            <p>{{ task.source?.originalFileName || task.sourceFileName }}</p>
          </div>
          <div>
            <p class="label">策略速览</p>
            <p>{{ strategyOverviewHeadline }}</p>
          </div>
        </div>
        <p v-if="task.creativePrompt" class="creative">{{ task.creativePrompt }}</p>
      </div>

      <div v-if="task.plan?.length" class="glass-plan">
        <div class="plan-head">
          <div>
            <p class="eyebrow">Planning Deck</p>
            <div class="flex items-center gap-3">
              <h2>{{ planningDeckTitle }}</h2>
              <HintBell
                title="Deck 指南"
                :text="planningDeckDescription"
                align="left"
              />
            </div>
          </div>
          <div class="plan-metrics">
            <span>{{ planOverview.clipCount }} 方案</span>
            <span>{{ planOverview.sourceCount }} 素材</span>
          </div>
        </div>

        <div class="plan-tabs">
          <button
            v-for="(clip, index) in task.plan"
            :key="clip.clipIndex"
            :class="['plan-tab', { active: index === activePlanIndex }]"
            type="button"
            @click="activePlanIndex = index"
          >
            <p>Plan {{ clip.clipIndex }}</p>
            <strong>{{ clip.title }}</strong>
            <span>{{ clip.durationSeconds.toFixed(1) }}s · {{ clip.segments?.length ?? 1 }} 单元</span>
          </button>
        </div>

        <article v-if="currentPlanClip" class="plan-hero">
          <div class="plan-title">
            <h3>#{{ currentPlanClip.clipIndex }} {{ currentPlanClip.title }}</h3>
            <span>{{ currentPlanClip.durationSeconds.toFixed(1) }}s</span>
          </div>
          <p>{{ currentPlanClip.reason }}</p>
          <div class="plan-tags">
            <span>{{ editingModeLabel }}</span>
            <span>转场 · {{ storyboardTransitionLabel(currentPlanClip.transitionStyle || task.mixcutTransitionStyle, task.mixcutStylePreset) }}</span>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>


<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getRuntimeConfig } from "@/api/runtime-config";
import { deleteTask, fetchTask, retryTask } from "@/api/tasks";
import type { TaskDetail, TaskPlanClip, TaskPlanSegment, TaskStatus, TaskTraceEvent } from "@/types";
import HintBell from "@/components/HintBell.vue";
import TimelineStage from "@/components/TimelineStage.vue";
import { usePolling } from "@/composables/usePolling";
import { formatTaskStatus, getTaskLifecycleGroup, isTerminalTaskStatus } from "@/utils/task";
import { resolveRuntimeUrl } from "@/utils/url";

type TraceTone = "slate" | "emerald" | "sky" | "fuchsia" | "amber" | "rose";
type ProgressStatus = "pending" | "active" | "done" | "error";

interface TraceFocusItem {
  title: string;
  detail: string;
  tone: TraceTone;
  timestamp?: string;
}

interface TraceProgressItem {
  key: string;
  label: string;
  description: string;
  hint: string;
  progress: number;
  status: ProgressStatus;
  tone: TraceTone;
}

interface ReadableTraceItem {
  key: string;
  stageLabel: string;
  title: string;
  detail: string;
  tags: string[];
  tone: TraceTone;
  important: boolean;
  timestamp: string;
  event: string;
}

interface PlanningModeSummary {
  label: string;
  title: string;
  detail: string;
  tone: TraceTone;
}

interface StoryboardLane {
  key: string;
  label: string;
  title: string;
  detail: string;
  tone: TraceTone;
  kind: "flash" | "insert" | "motion" | "landing" | "single";
  segments: TaskPlanSegment[];
}

interface StoryboardSegmentMeta {
  label: string;
  detail: string;
  tone: TraceTone;
  kind: "flash" | "insert" | "motion" | "landing" | "single";
}

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const loading = ref(true);
const errorMessage = ref("");
const traceEvents = ref<TaskTraceEvent[]>([]);
const traceLoading = ref(false);
const traceErrorMessage = ref("");
const traceExpanded = ref(false);
const outputsExpanded = ref(false);
const actionLoading = ref(false);
const activePlanIndex = ref(0);

const taskId = computed(() => {
  const value = route.params.id;
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return typeof value === "string" ? value : "";
});

const statusHint = computed(() => {
  if (!task.value) {
    return "";
  }
  return formatTaskStatus(task.value.status);
});

const completedOutputCount = computed(() => task.value?.completedOutputCount ?? task.value?.outputs.length ?? 0);
const runningTask = computed(() => Boolean(task.value && !isTerminalTaskStatus(task.value.status)));
const traceEventsDesc = computed(() => [...traceEvents.value].reverse());
const planOverview = computed(() => {
  const plan = task.value?.plan ?? [];
  const segments = plan.flatMap((clip) => clip.segments ?? []);
  const sourceCount = new Set(segments.map((segment) => segment.sourceAssetId).filter(Boolean)).size;
  return {
    clipCount: plan.length,
    segmentCount: segments.length,
    frameCount: segments.filter((segment) => (segment.segmentKind || "").toLowerCase() === "frame").length,
    sourceCount,
  };
});
const isMixcutMode = computed(() => (task.value?.editingMode || "drama") === "mixcut");
const editingModeLabel = computed(() => (isMixcutMode.value ? "混剪模式" : "短剧剪辑模式"));
const planningDeckTitle = computed(() => (isMixcutMode.value ? "导演规划方案" : "剧情卡点方案"));
const planningDeckDescription = computed(() =>
  isMixcutMode.value
    ? "先看整体脚本密度和镜头结构，再聚焦单条方案的导演意图、分镜单元和素材轨道。"
    : "先看整体卡点分布和对白保护，再聚焦单条方案的剧情意图、时间窗和情绪落点。"
);
const sourceModeSummary = computed(() => {
  const sourceCount = task.value?.sourceAssetCount ?? task.value?.sourceAssetIds?.length ?? 1;
  return isMixcutMode.value ? `混剪编排 · 共 ${sourceCount} 条素材` : "短剧剪辑 · 单素材剧情卡点";
});
const strategyOverviewTitle = computed(() => (isMixcutMode.value ? "导演策略" : "短剧策略"));
const strategyOverviewHeadline = computed(() =>
  isMixcutMode.value
    ? `混剪导演编排 · ${mixcutMetaLabel(task.value?.mixcutContentType, task.value?.mixcutStylePreset)}`
    : "短剧高燃卡点 · 对白完整 / 情绪推进"
);
const strategyOverviewBadge = computed(() =>
  isMixcutMode.value
    ? mixcutTransitionLabel(task.value?.mixcutTransitionStyle, task.value?.mixcutStylePreset)
    : "对白边界保护"
);
const strategyCenterHeadline = computed(() =>
  isMixcutMode.value
    ? `${mixcutContentTypeLabel(task.value?.mixcutContentType)} / ${mixcutStyleLabel(task.value?.mixcutContentType, task.value?.mixcutStylePreset)}`
    : "高燃卡点 / 对白完整"
);
const strategyCenterDetail = computed(() =>
  isMixcutMode.value
    ? mixcutMetaLabel(task.value?.mixcutContentType, task.value?.mixcutStylePreset)
    : "当前会优先围绕冲突升级、反转爆点和完整对白去规划时间窗，不做导演式跨素材分镜。"
);
const currentPlanClip = computed(() => {
  const plan = task.value?.plan ?? [];
  if (!plan.length) {
    return null;
  }
  const normalizedIndex = Math.max(0, Math.min(activePlanIndex.value, plan.length - 1));
  return plan[normalizedIndex] ?? plan[0] ?? null;
});

function lastTraceEvent(...events: string[]) {
  for (const entry of traceEventsDesc.value) {
    if (events.includes(entry.event)) {
      return entry;
    }
  }
  return null;
}

function hasTraceEvent(...events: string[]) {
  return Boolean(lastTraceEvent(...events));
}

function resolveStorageUrl(value: string) {
  return resolveRuntimeUrl(value, getRuntimeConfig().storageBaseUrl);
}

function formatTime(value?: string | null) {
  if (!value) {
    return "等待生成";
  }
  return new Date(value).toLocaleString();
}

function formatDuration(value?: number | null) {
  if (typeof value !== "number") {
    return "时长未知";
  }
  return `${value.toFixed(1)} 秒`;
}

function formatResolution(width?: number | null, height?: number | null) {
  if (!width || !height) {
    return "分辨率待探测";
  }
  return `${width} × ${height}`;
}

function formatBytes(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "体积未知";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function clipSegmentSourcesLabel(clip: TaskPlanClip) {
  const sourceNames = Array.from(new Set((clip.segments ?? []).map((segment) => segment.sourceFileName).filter(Boolean)));
  if (!sourceNames.length) {
    return "未拆分出素材来源";
  }
  if (sourceNames.length === 1) {
    return `来源素材：${sourceNames[0]}`;
  }
  return `涉及素材：${sourceNames.join("、")}`;
}

function clipUniqueSourceCount(clip: TaskPlanClip) {
  return new Set((clip.segments ?? []).map((segment) => segment.sourceAssetId).filter(Boolean)).size || 1;
}

function clipFrameCount(clip: TaskPlanClip) {
  return (clip.segments ?? []).filter((segment) => (segment.segmentKind || "").toLowerCase() === "frame").length;
}

function clipInsertCount(clip: TaskPlanClip) {
  return (clip.segments ?? []).filter((segment) => ((segment.segmentRole || segment.shotRole || "").toLowerCase().includes("insert"))).length;
}

function clipMotionCount(clip: TaskPlanClip) {
  return (clip.segments ?? []).filter((segment) => (segment.segmentKind || "video").toLowerCase() !== "frame").length;
}

function storyboardSegmentMeta(clip: TaskPlanClip, segment: TaskPlanSegment, segmentIndex: number): StoryboardSegmentMeta {
  const total = clip.segments?.length ?? 0;
  const explicitKind = (segment.segmentKind || "").toLowerCase();
  const explicitRole = (segment.segmentRole || segment.shotRole || "").toLowerCase();
  const isStill = explicitKind.includes("frame") || explicitRole.includes("flash");

  if (total <= 1) {
    return {
      label: "单段完整镜头",
      detail: "这一段会直接完整展开，不额外拆成插叙或静帧脚本。",
      tone: "sky",
      kind: "single",
    };
  }

  if (explicitRole.includes("flashback") || explicitRole.includes("insert")) {
    return {
      label: "插叙镜头",
      detail: "用来提前透露后置信息、制造对照或做回望感插入。",
      tone: "fuchsia",
      kind: "insert",
    };
  }

  if (isStill) {
    return {
      label: "静帧快闪",
      detail: "从视频中截出的定格帧，适合快速轮播、地点建立或信息预埋。",
      tone: "amber",
      kind: "flash",
    };
  }

  if (explicitRole.includes("landing") || segmentIndex >= total - 1) {
    return {
      label: "收束镜头",
      detail: "适合情绪收束、悬念落点或结尾定格。",
      tone: "rose",
      kind: "landing",
    };
  }

  return {
    label: explicitRole.includes("scene_open") ? "起势运动镜头" : "运动展开",
    detail: explicitRole.includes("scene_open")
      ? "负责把画面从静帧/预埋信息推进到真正运动状态。"
      : "用于动作展开、内容推进和节奏承接。",
    tone: "sky",
    kind: "motion",
  };
}

function storyboardLanes(clip: TaskPlanClip): StoryboardLane[] {
  const segments = clip.segments ?? [];
  if (!segments.length) {
    return [];
  }
  if (segments.length === 1) {
    return [
      {
        key: "single",
        label: "单段直剪",
        title: "完整镜头",
        detail: "当前片段没有拆成分镜，直接作为完整镜头处理。",
        tone: "sky",
        kind: "single",
        segments,
      },
    ];
  }
  const lanes: StoryboardLane[] = [];
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const meta = storyboardSegmentMeta(clip, segment, index);
    const lastLane = lanes[lanes.length - 1];
    if (lastLane && lastLane.kind === meta.kind) {
      lastLane.segments.push(segment);
      lastLane.title = `${lastLane.segments.length} 个${lastLane.label}`;
      continue;
    }
    lanes.push({
      key: `${meta.kind}-${lanes.length}`,
      label: meta.label,
      title: `1 个${meta.label}`,
      detail: meta.detail,
      tone: meta.tone,
      kind: meta.kind,
      segments: [segment],
    });
  }
  return lanes;
}

function storyboardSegmentActualIndex(clip: TaskPlanClip, segment: TaskPlanSegment, fallbackIndex: number) {
  const segments = clip.segments ?? [];
  const exactIndex = segments.findIndex((entry) => (
    entry.sourceAssetId === segment.sourceAssetId
    && entry.sourceFileName === segment.sourceFileName
    && entry.startSeconds === segment.startSeconds
    && entry.endSeconds === segment.endSeconds
    && (entry.segmentKind || "") === (segment.segmentKind || "")
  ));
  return exactIndex >= 0 ? exactIndex : fallbackIndex;
}

function storyboardSegmentRange(segment: TaskPlanSegment) {
  if ((segment.segmentKind || "").toLowerCase() === "frame" && segment.frameTimestampSeconds !== undefined && segment.frameTimestampSeconds !== null) {
    return `截帧 ${segment.frameTimestampSeconds.toFixed(1)}s`;
  }
  return `${segment.startSeconds.toFixed(1)}s - ${segment.endSeconds.toFixed(1)}s`;
}

function mixcutMetaLabel(contentType?: string | null, stylePreset?: string | null) {
  const contentTypeLabelMap: Record<string, string> = {
    generic: "通用混剪",
    drama: "剧情混剪",
    vlog: "Vlog 混剪",
    food: "美食混剪",
    fashion: "时尚混剪",
    sports: "运动混剪",
  };
  const styleLabelMap: Record<string, string> = {
    director: "导演感推进",
    music_sync: "音乐卡点",
  };
  const contentTypeLabel = contentType ? contentTypeLabelMap[contentType] || "通用混剪" : "通用混剪";
  const styleLabel = stylePreset ? styleLabelMap[stylePreset] || stylePreset : "导演感推进";
  return `策略：${contentTypeLabel} / ${styleLabel}`;
}

function mixcutTransitionLabel(transitionStyle?: string | null, stylePreset?: string | null) {
  if (transitionStyle === "crossfade") {
    return "叠化转场";
  }
  if (transitionStyle === "flash") {
    return "白闪转场";
  }
  if (transitionStyle === "fade_black") {
    return "黑场过渡";
  }
  if (stylePreset === "music_sync") {
    return "白闪转场";
  }
  return "硬切转场";
}

function mixcutTemplateLabel(template?: string | null) {
  switch (template) {
    case "director_crossfade_story":
      return "导演感叠化混剪模板";
    case "music_sync_flash_montage":
      return "音乐白闪混剪模板";
    default:
      return "单素材直切模板";
  }
}

function introTemplateLabel(template?: string | null) {
  switch (template) {
    case "cold_open":
      return "冷开场直切";
    case "flash_hook":
      return "爆点闪切片头";
    case "pressure_build":
      return "情绪压迫片头";
    default:
      return "不加片头";
  }
}

function introTemplateHint(template?: string | null) {
  switch (template) {
    case "cold_open":
      return "开头直接进入剧情现场，尽量不做额外铺垫。";
    case "flash_hook":
      return "先给爆点，再回剧情，适合首刷拉停。";
    case "pressure_build":
      return "先压氛围和情绪，再推进到关键对白。";
    default:
      return "直接切入正文，不额外增加片头。";
  }
}

function outroTemplateLabel(template?: string | null) {
  switch (template) {
    case "suspense_hold":
      return "悬念停顿片尾";
    case "follow_hook":
      return "追更钩子片尾";
    case "question_freeze":
      return "反问定格片尾";
    default:
      return "不加片尾";
  }
}

function outroTemplateHint(template?: string | null) {
  switch (template) {
    case "suspense_hold":
      return "停在一句没说完或表情反转前，制造停留。";
    case "follow_hook":
      return "保留下一集欲望，适合连续剧切条。";
    case "question_freeze":
      return "停在质问、反讽或答案未揭晓的位置。";
    default:
      return "直接收尾，不额外增加片尾。";
  }
}

function mixcutContentTypeLabel(contentType?: string | null) {
  switch (contentType) {
    case "drama":
      return "剧情混剪";
    case "vlog":
      return "Vlog 混剪";
    case "food":
      return "美食混剪";
    case "fashion":
      return "时尚混剪";
    case "sports":
      return "运动混剪";
    default:
      return "通用混剪";
  }
}

function mixcutStyleLabel(contentType?: string | null, stylePreset?: string | null) {
  switch (stylePreset) {
    case "music_sync":
      return "音乐卡点";
    default:
      return contentType === "drama" ? "导演感推进" : "导演感推进";
  }
}

function storyboardSegmentStyle(clip: TaskPlanClip, segment: TaskPlanSegment, segmentIndex: number, tone: TraceTone) {
  const ratio = clip.durationSeconds > 0 ? segment.durationSeconds / clip.durationSeconds : 1;
  const growth = Math.max(1.3, Math.min(4.6, ratio * 4.8));
  const accentShift = Math.max(0, Math.min(100, segmentIndex * 8));
  return {
    "--storyboard-grow": String(growth),
    "--storyboard-accent-shift": `${accentShift}%`,
    "--storyboard-accent-color": storyboardAccentColor(tone),
  } as Record<string, string>;
}

function storyboardAccentColor(tone?: TraceTone) {
  switch (tone) {
    case "amber":
      return "rgba(245, 158, 11, 0.9)";
    case "sky":
      return "rgba(56, 189, 248, 0.9)";
    case "fuchsia":
      return "rgba(217, 70, 239, 0.88)";
    case "emerald":
      return "rgba(16, 185, 129, 0.88)";
    case "rose":
      return "rgba(244, 63, 94, 0.9)";
    default:
      return "rgba(59, 130, 246, 0.88)";
  }
}

function storyboardTransitionLabel(transitionStyle?: string | null, stylePreset?: string | null) {
  return mixcutTransitionLabel(transitionStyle, stylePreset);
}

function storyboardSourceLabel(segment: TaskPlanSegment, segmentIndex: number) {
  const source = segment.sourceFileName || "未知素材";
  const role = (segment.segmentRole || "").toLowerCase();
  if ((segment.segmentKind || "").toLowerCase() === "frame") {
    return role.includes("flashback") ? `插叙定格 · ${source}` : `定格来源 · ${source}`;
  }
  return segmentIndex === 0 ? `起势来源 · ${source}` : `镜头来源 · ${source}`;
}

function storyboardSegmentRole(clip: TaskPlanClip, segment: TaskPlanSegment, segmentIndex: number) {
  return storyboardSegmentMeta(clip, segment, segmentIndex).label;
}

function storyboardSegmentClass(tone: TraceTone) {
  switch (tone) {
    case "amber":
      return "border-amber-400/20 bg-gradient-to-br from-amber-500/12 via-white/[0.035] to-white/[0.02]";
    case "sky":
      return "border-sky-400/20 bg-gradient-to-br from-sky-500/12 via-white/[0.035] to-white/[0.02]";
    case "rose":
      return "border-rose-400/20 bg-gradient-to-br from-rose-500/12 via-white/[0.035] to-white/[0.02]";
    case "fuchsia":
      return "border-fuchsia-400/20 bg-gradient-to-br from-fuchsia-500/12 via-white/[0.035] to-white/[0.02]";
    case "emerald":
      return "border-emerald-400/20 bg-gradient-to-br from-emerald-500/12 via-white/[0.035] to-white/[0.02]";
    default:
      return "border-white/8 bg-gradient-to-br from-white/[0.05] via-white/[0.03] to-white/[0.02]";
  }
}

function payloadString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function payloadNumber(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function payloadBoolean(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "boolean" ? value : null;
}

function payloadStringArray(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : String(item ?? "").trim()))
    .filter(Boolean);
}

function payloadNumberRange(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  if (!Array.isArray(value) || value.length < 2) {
    return [];
  }
  const start = Number(value[0]);
  const end = Number(value[1]);
  return Number.isFinite(start) && Number.isFinite(end) ? [start, end] : [];
}

function clipTimeLabel(start?: number | null, end?: number | null) {
  if (typeof start !== "number" || typeof end !== "number") {
    return "";
  }
  return `${start.toFixed(1)}s - ${end.toFixed(1)}s`;
}

function shortText(value: string, max = 80) {
  if (!value) {
    return "";
  }
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function joinParts(parts: Array<string | null | undefined>, separator = "，") {
  return parts.filter(Boolean).join(separator);
}

function stageLabel(stage: string) {
  switch (stage) {
    case "api":
      return "任务";
    case "dispatch":
      return "调度";
    case "pipeline":
      return "流程";
    case "analysis":
      return "素材分析";
    case "audio":
      return "音频节奏";
    case "scene":
      return "镜头边界";
    case "planning":
      return "方案规划";
    case "vision":
      return "视频理解";
    case "fusion":
      return "融合规划";
    case "llm":
      return "大模型";
    case "render":
      return "FFmpeg";
    default:
      return stage || "日志";
  }
}

function toneBadgeClass(tone: TraceTone) {
  switch (tone) {
    case "emerald":
      return "bg-emerald-500/15 text-emerald-100";
    case "sky":
      return "bg-sky-500/15 text-sky-100";
    case "fuchsia":
      return "bg-fuchsia-500/15 text-fuchsia-100";
    case "amber":
      return "bg-amber-500/15 text-amber-100";
    case "rose":
      return "bg-rose-500/15 text-rose-100";
    default:
      return "bg-white/10 text-slate-200";
  }
}

function focusCardClass(tone: TraceTone) {
  switch (tone) {
    case "emerald":
      return "border-emerald-400/20 bg-emerald-500/8";
    case "sky":
      return "border-sky-400/20 bg-sky-500/8";
    case "fuchsia":
      return "border-fuchsia-400/20 bg-fuchsia-500/8";
    case "amber":
      return "border-amber-400/20 bg-amber-500/8";
    case "rose":
      return "border-rose-400/25 bg-rose-500/8";
    default:
      return "border-white/8 bg-white/[0.04]";
  }
}

function progressBarClass(tone: TraceTone) {
  switch (tone) {
    case "emerald":
      return "bg-gradient-to-r from-emerald-500 to-teal-300";
    case "sky":
      return "bg-gradient-to-r from-sky-500 to-cyan-300";
    case "fuchsia":
      return "bg-gradient-to-r from-fuchsia-500 to-pink-300";
    case "amber":
      return "bg-gradient-to-r from-amber-500 to-orange-300";
    case "rose":
      return "bg-gradient-to-r from-rose-500 to-red-300";
    default:
      return "bg-gradient-to-r from-slate-500 to-slate-300";
  }
}

function stageStatusLabel(status: ProgressStatus) {
  switch (status) {
    case "done":
      return "已完成";
    case "active":
      return "进行中";
    case "error":
      return "异常";
    default:
      return "待开始";
  }
}

function describeTraceEvent(entry: TaskTraceEvent) {
  const payload = entry.payload || {};
  const model = payloadString(payload, "model");
  const clipTitles = payloadStringArray(payload, "clip_titles");
  const clipIndex = payloadNumber(payload, "clip_index");
  const clipCount = payloadNumber(payload, "clip_count");
  const startSeconds = payloadNumber(payload, "start_seconds");
  const endSeconds = payloadNumber(payload, "end_seconds");
  const progress = payloadNumber(payload, "progress");
  const contentExcerpt = payloadString(payload, "content_excerpt");
  const promptLength = payloadNumber(payload, "prompt_length");
  const transcriptCueCount = payloadNumber(payload, "transcript_cue_count");
  const audioPeakCount = payloadNumber(payload, "audio_peak_count");
  const frameCount = payloadNumber(payload, "frame_count");
  const error = payloadString(payload, "error");

  switch (entry.event) {
    case "task.created": {
      const durationRange = payloadNumberRange(payload, "duration_range");
      const outputCount = payloadNumber(payload, "output_count");
      return {
        title: "任务已创建",
        detail: joinParts([
          payloadString(payload, "platform") ? `平台 ${payloadString(payload, "platform")}` : "",
          durationRange.length === 2 ? `时长 ${durationRange[0]}-${durationRange[1]} 秒` : "",
          outputCount ? `目标输出 ${outputCount} 条` : "",
          payloadBoolean(payload, "has_transcript") ? "已附带字幕/台词输入" : "未附带字幕/台词输入",
        ]),
        tags: [payloadString(payload, "aspect_ratio"), payloadString(payload, "title")].filter(Boolean),
        tone: "emerald" as const,
        important: true,
      };
    }
    case "task.enqueued":
      return {
        title: "任务已进入队列",
        detail: "等待 worker 拉取后继续执行。",
        tags: [],
        tone: "sky" as const,
        important: false,
      };
    case "task.dispatched_inline":
      return {
        title: "任务已直接启动",
        detail: "当前环境使用本地线程执行，不经过外部队列。",
        tags: [],
        tone: "sky" as const,
        important: false,
      };
    case "task.enqueue_failed":
      return {
        title: "入队失败，已切回本地执行",
        detail: "队列不可用时任务不会卡住，会直接改走本地线程。",
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "task.claimed":
    case "task.processing_started":
      return {
        title: "任务开始处理",
        detail: "执行器已接管任务，流程正式开始。",
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "analysis.started":
      return {
        title: "开始分析源视频",
        detail: "正在识别时长、分辨率、音轨等素材信息。",
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "analysis.completed":
      return {
        title: "素材分析完成",
        detail: joinParts([
          payloadNumber(payload, "durationSeconds") ? `时长 ${payloadNumber(payload, "durationSeconds")?.toFixed(1)} 秒` : "",
          payloadNumber(payload, "width") && payloadNumber(payload, "height")
            ? `分辨率 ${payloadNumber(payload, "width")} × ${payloadNumber(payload, "height")}`
            : "",
          payloadBoolean(payload, "hasAudio") === false ? "无音轨" : "含音轨",
        ]),
        tags: [],
        tone: "emerald" as const,
        important: true,
      };
    case "planning.started":
      return {
        title: "开始生成剪辑方案",
        detail: joinParts([
          transcriptCueCount ? `带 ${transcriptCueCount} 条时间轴字幕` : payloadBoolean(payload, "has_transcript") ? "带文本字幕输入" : "无字幕输入",
          payloadBoolean(payload, "creative_prompt_present") ? "带创意补充" : "无创意补充",
          payloadString(payload, "primary_model") ? `主模型 ${payloadString(payload, "primary_model")}` : "",
          payloadString(payload, "mixcut_content_type") ? mixcutMetaLabel(payloadString(payload, "mixcut_content_type"), payloadString(payload, "mixcut_style_preset")) : "",
        ]),
        tags: [
          payloadString(payload, "fallback_model") ? `回退 ${payloadString(payload, "fallback_model")}` : "",
          payloadString(payload, "vision_model") ? `视觉 ${payloadString(payload, "vision_model")}` : "",
        ].filter(Boolean),
        tone: "sky" as const,
        important: true,
      };
    case "planning.subtitle_signals":
      return {
        title: "已锁定字幕冲突点",
        detail: transcriptCueCount ? `本次从 ${transcriptCueCount} 条字幕时间轴里提取了强信号切点。` : "已提取字幕强信号时间轴。",
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "audio.peaks_detected":
      return {
        title: audioPeakCount ? `已检测到 ${audioPeakCount} 个音频卡点` : "已检测到音频峰值卡点",
        detail: "这些音频峰值会和字幕时间轴、画面高点一起参与切点判断。",
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "scene.changes_detected":
      return {
        title: payloadNumber(payload, "scene_change_count") ? `已检测到 ${payloadNumber(payload, "scene_change_count")} 个镜头切换点` : "已检测到镜头切换边界",
        detail: "这些镜头边界会参与抽帧和最终裁剪边界修正，减少从动作半截切入或切出。",
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "heuristic.start":
      return {
        title: "未使用大模型，已切到本地规则规划",
        detail: transcriptCueCount ? `当前按本地规则规划，参考 ${transcriptCueCount} 条字幕时间轴。` : "当前没有拿到大模型结果，系统改用本地规则规划候选片段。",
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "heuristic.completed":
      return {
        title: "本地规则规划已完成",
        detail: clipCount ? `没有使用大模型，本地规则生成了 ${clipCount} 条候选片段。` : "没有使用大模型，本地规则已生成候选片段。",
        tags: clipTitles.slice(0, 3),
        tone: "amber" as const,
        important: true,
      };
    case "vision.attempt":
      return {
        title: "开始逐素材分析完整镜头",
        detail: joinParts([
          model ? `视觉模型 ${model}` : "",
          payloadNumber(payload, "source_count") ? `共 ${payloadNumber(payload, "source_count")} 条素材` : "",
          frameCount ? `单次请求含 ${frameCount} 张镜头采样帧` : "准备分析完整镜头采样帧",
        ]),
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "vision.request":
      return {
        title: "视觉模型已收到逐镜头分析请求",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadString(payload, "source_file_name") ? `素材 ${payloadString(payload, "source_file_name")}` : "",
          payloadNumber(payload, "shot_count") ? `覆盖 ${payloadNumber(payload, "shot_count")} 个镜头段` : "",
          frameCount ? `${frameCount} 张镜头采样帧` : "",
          transcriptCueCount ? `带 ${transcriptCueCount} 条字幕上下文` : payloadBoolean(payload, "has_transcript") ? "带字幕上下文" : "无字幕上下文",
        ]),
        tags: [],
        tone: "sky" as const,
        important: true,
      };
    case "vision.analysis_saved":
      return {
        title: "完整镜头分析 JSON 已落盘",
        detail: joinParts([
          payloadNumber(payload, "source_count") ? `${payloadNumber(payload, "source_count")} 条素材` : "",
          payloadNumber(payload, "shot_count") ? `${payloadNumber(payload, "shot_count")} 个镜头段` : "",
          payloadString(payload, "analysis_path") ? shortText(payloadString(payload, "analysis_path"), 120) : "",
        ]),
        tags: ["可用于复盘"],
        tone: "emerald" as const,
        important: true,
      };
    case "vision.response":
      {
        const parsedShotCount = payloadNumber(payload, "parsed_shot_count");
        const parsedEventCount = payloadNumber(payload, "parsed_event_count");
        const eventTitles = payloadStringArray(payload, "event_titles");
        const eventTypes = payloadStringArray(payload, "event_types");
        const parsedClipCount = payloadNumber(payload, "parsed_clip_count");
        return {
          title: parsedShotCount
            ? `视觉理解返回了 ${parsedShotCount} 个镜头分析结果`
            : parsedEventCount
              ? `视觉理解返回了 ${parsedEventCount} 个高层事件`
              : parsedClipCount
                ? `视频内容理解返回了 ${parsedClipCount} 条高点方案`
                : "视频内容理解已返回结果",
          detail: contentExcerpt
            ? `返回摘录：${shortText(contentExcerpt, 160)}`
            : parsedShotCount
              ? "视觉模型已经覆盖式分析了该素材的完整镜头内容，接下来会交给融合模型自动生成分镜脚本和时间点。"
              : parsedEventCount
                ? "视觉模型已经归纳出高层事件，后续会再做最终切点规划。"
                : "视觉模型已返回完整镜头内容理解结果。",
          tags: [model ? `模型 ${model}` : "", ...(parsedShotCount ? [`镜头 ${parsedShotCount} 段`] : []), ...eventTypes.slice(0, 3), ...eventTitles.slice(0, 2), ...clipTitles.slice(0, 2)].filter(Boolean),
          tone: "sky" as const,
          important: true,
        };
      }
    case "fusion.vision_fallback":
      return {
        title: "完整镜头分析失败，已降级继续规划",
        detail: "视觉模型这轮没成功返回完整镜头 JSON，系统会改用字幕时间轴、音频卡点和候选片段继续做最终剪辑规划。",
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "fusion.attempt":
      return {
        title: "开始生成最终剪辑时间点",
        detail: joinParts([
          model ? `融合模型 ${model}` : "",
          payloadNumber(payload, "visual_shot_count") ? `已接入 ${payloadNumber(payload, "visual_shot_count")} 个镜头段分析` : payloadBoolean(payload, "used_visual_events") ? "已接入视觉分析结果" : "当前不带视觉分析结果",
        ]),
        tags: [payloadString(payload, "visual_model") ? `视觉 ${payloadString(payload, "visual_model")}` : ""].filter(Boolean),
        tone: "fuchsia" as const,
        important: true,
      };
    case "fusion.request":
      return {
        title: "融合规划请求已发出",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          promptLength ? `Prompt ${promptLength} 字符` : "",
          transcriptCueCount ? `字幕时间轴 ${transcriptCueCount} 条` : "",
          audioPeakCount ? `音频卡点 ${audioPeakCount} 个` : "",
          payloadNumber(payload, "scene_change_count") ? `镜头边界 ${payloadNumber(payload, "scene_change_count")} 个` : "",
          payloadNumber(payload, "visual_shot_count") ? `镜头分析 ${payloadNumber(payload, "visual_shot_count")} 段` : "",
          payloadNumber(payload, "visual_event_count") ? `视觉事件 ${payloadNumber(payload, "visual_event_count")} 个` : "",
          payloadString(payload, "mixcut_content_type") ? mixcutMetaLabel(payloadString(payload, "mixcut_content_type"), payloadString(payload, "mixcut_style_preset")) : "",
        ]),
        tags: [payloadNumber(payload, "visual_shot_count") ? "完整镜头分析已接入" : payloadBoolean(payload, "used_visual_events") ? "视觉事件已接入" : "未接入视觉分析"].filter(Boolean),
        tone: "fuchsia" as const,
        important: true,
      };
    case "fusion.response":
      return {
        title: clipCount ? `融合规划返回了 ${clipCount} 条最终方案` : "融合规划已返回结果",
        detail: contentExcerpt ? `返回摘录：${shortText(contentExcerpt, 160)}` : "最终剪辑时间点已经确定，后续会按这些切点执行 FFmpeg 渲染。",
        tags: [
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "visual_shot_count") ? `已结合 ${payloadNumber(payload, "visual_shot_count")} 段镜头分析` : payloadBoolean(payload, "used_visual_events") ? "已结合视觉事件" : "未结合视觉分析",
          ...clipTitles.slice(0, 3),
        ].filter(Boolean),
        tone: "fuchsia" as const,
        important: true,
      };
    case "fusion.http_error":
      return {
        title: "融合规划请求返回错误状态",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "status_code") ? `HTTP ${payloadNumber(payload, "status_code")}` : "",
          payloadString(payload, "response_excerpt") ? shortText(payloadString(payload, "response_excerpt"), 160) : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "fusion.timeout":
      return {
        title: "融合规划响应超时",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "timeout_seconds") ? `等待 ${payloadNumber(payload, "timeout_seconds")} 秒后仍未返回` : "",
          promptLength ? `Prompt ${promptLength} 字符` : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "fusion.network_error":
      return {
        title: "融合规划网络失败",
        detail: joinParts([model ? `模型 ${model}` : "", error || entry.message]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "fusion.attempt_failed":
      return {
        title: "当前融合模型失败，准备回退",
        detail: joinParts([model ? `模型 ${model}` : "", error ? shortText(error, 160) : "准备尝试下一个可用模型。"]),
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "vision.timeout":
      return {
        title: "视频内容理解超时",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "timeout_seconds") ? `等待 ${payloadNumber(payload, "timeout_seconds")} 秒后仍未返回` : "",
          frameCount ? `${frameCount} 张关键帧` : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "vision.http_error":
      return {
        title: "视频内容理解请求返回错误状态",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "status_code") ? `HTTP ${payloadNumber(payload, "status_code")}` : "",
          payloadString(payload, "response_excerpt") ? shortText(payloadString(payload, "response_excerpt"), 160) : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "vision.network_error":
      return {
        title: "视频内容理解网络失败",
        detail: joinParts([model ? `模型 ${model}` : "", error || entry.message]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "vision.attempt_failed":
      return {
        title: "当前视觉模型失败，准备回退",
        detail: joinParts([model ? `模型 ${model}` : "", error ? shortText(error, 160) : "准备尝试下一个可用视觉模型。"]),
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "qwen.attempt":
      return {
        title: "开始调用大模型",
        detail: model ? `当前尝试模型 ${model}。` : "开始向大模型发起规划请求。",
        tags: model ? [`模型 ${model}`] : [],
        tone: "fuchsia" as const,
        important: true,
      };
    case "qwen.request":
      return {
        title: "大模型请求已发出",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          promptLength ? `Prompt ${promptLength} 字符` : "",
          transcriptCueCount ? `字幕时间轴 ${transcriptCueCount} 条` : "",
        ]),
        tags: contentExcerpt ? [`返回前上下文已准备`] : [],
        tone: "fuchsia" as const,
        important: false,
      };
    case "qwen.response":
      return {
        title: clipCount ? `大模型返回了 ${clipCount} 条剪辑方案` : "大模型已返回规划结果",
        detail: contentExcerpt ? `返回摘录：${shortText(contentExcerpt, 160)}` : "已收到模型响应并完成结构化解析。",
        tags: [model ? `模型 ${model}` : "", ...clipTitles.slice(0, 3)].filter(Boolean),
        tone: "fuchsia" as const,
        important: true,
      };
    case "qwen.http_error":
      return {
        title: "大模型请求返回错误状态",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "status_code") ? `HTTP ${payloadNumber(payload, "status_code")}` : "",
          payloadString(payload, "response_excerpt") ? shortText(payloadString(payload, "response_excerpt"), 160) : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "qwen.timeout":
      return {
        title: "大模型响应超时",
        detail: joinParts([
          model ? `模型 ${model}` : "",
          payloadNumber(payload, "timeout_seconds") ? `等待 ${payloadNumber(payload, "timeout_seconds")} 秒后仍未返回` : "",
          promptLength ? `Prompt ${promptLength} 字符` : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "qwen.network_error":
      return {
        title: "大模型请求网络失败",
        detail: joinParts([model ? `模型 ${model}` : "", error || entry.message]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "qwen.attempt_failed":
      return {
        title: "当前模型失败，准备回退",
        detail: joinParts([model ? `模型 ${model}` : "", error ? shortText(error, 160) : "准备尝试下一个可用模型。"]),
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "planning.completed":
      return {
        title: clipCount ? `剪辑方案已生成，共 ${clipCount} 条` : "剪辑方案已生成",
        detail: clipTitles.length ? `方案摘要：${clipTitles.slice(0, 3).join(" / ")}` : "可以进入 FFmpeg 渲染阶段。",
        tags: [],
        tone: "emerald" as const,
        important: true,
      };
    case "render.started":
      return {
        title: "开始执行 FFmpeg 剪辑",
        detail: joinParts([
          clipCount ? `本轮计划输出 ${clipCount} 条成片` : "开始按规划方案输出成片",
          payloadString(payload, "transition_style") ? `默认转场 ${payloadString(payload, "transition_style")}` : "",
        ]),
        tags: [],
        tone: "amber" as const,
        important: true,
      };
    case "render.clip_started":
      return {
        title: clipIndex ? `开始剪第 ${clipIndex} 条素材` : "开始执行单条剪辑",
        detail: joinParts([
          payloadString(payload, "title"),
          clipTimeLabel(startSeconds, endSeconds),
          payloadNumber(payload, "segment_count") && payloadNumber(payload, "segment_count")! > 1
            ? `${payloadNumber(payload, "segment_count")} 段混剪`
            : "",
        ]),
        tags: [payloadString(payload, "transition_style") ? `转场 ${payloadString(payload, "transition_style")}` : ""].filter(Boolean),
        tone: "amber" as const,
        important: false,
      };
    case "render.clip_completed":
      return {
        title: clipIndex ? `第 ${clipIndex} 条剪辑成功` : "单条剪辑完成",
        detail: joinParts([
          payloadString(payload, "title"),
          progress ? `任务进度 ${progress}%` : "",
          payloadNumber(payload, "segment_count") && payloadNumber(payload, "segment_count")! > 1
            ? `${payloadNumber(payload, "segment_count")} 段混剪已拼接`
            : "",
        ]),
        tags: [
          payloadString(payload, "transition_style") ? `转场 ${payloadString(payload, "transition_style")}` : "",
          ...payloadStringArray(payload, "segment_sources").slice(0, 2),
        ].filter(Boolean),
        tone: "emerald" as const,
        important: true,
      };
    case "render.clip_failed":
      return {
        title: clipIndex ? `第 ${clipIndex} 条 FFmpeg 剪辑失败` : "FFmpeg 剪辑失败",
        detail: joinParts([
          payloadString(payload, "title"),
          clipTimeLabel(startSeconds, endSeconds),
          error ? shortText(error, 160) : "",
        ]),
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "task.completed":
      return {
        title: "任务已完成",
        detail: clipCount ? `共生成 ${clipCount} 条输出素材，可以直接预览和下载。` : "全部输出已完成。",
        tags: [],
        tone: "emerald" as const,
        important: true,
      };
    case "task.failed":
      return {
        title: "任务失败",
        detail: error ? shortText(error, 180) : entry.message,
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    case "task.source_missing":
      return {
        title: "任务源素材丢失",
        detail: "源文件不存在，任务无法继续。",
        tags: [],
        tone: "rose" as const,
        important: true,
      };
    default:
      return {
        title: entry.message || entry.event,
        detail: "",
        tags: [],
        tone: entry.level.toUpperCase() === "ERROR" ? ("rose" as const) : entry.level.toUpperCase() === "WARN" ? ("amber" as const) : ("slate" as const),
        important: false,
      };
  }
}

const readableTraceEvents = computed<ReadableTraceItem[]>(() =>
  traceEventsDesc.value.map((entry, index) => {
    const description = describeTraceEvent(entry);
    return {
      key: `${entry.timestamp}-${entry.event}-${index}`,
      stageLabel: stageLabel(entry.stage),
      title: description.title,
      detail: description.detail,
      tags: description.tags,
      tone: description.tone,
      important: description.important,
      timestamp: entry.timestamp,
      event: entry.event,
    };
  })
);

const collapsedTracePreview = computed(() => readableTraceEvents.value.slice(0, 3));

const renderStageProgress = computed(() => {
  const total = task.value?.outputCount ?? 0;
  const done = completedOutputCount.value;
  if (total <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((done / total) * 100)));
});

const planningModeSummary = computed<PlanningModeSummary>(() => {
  if (!task.value) {
    return {
      label: "等待任务加载",
      title: "尚未读取到任务信息",
      detail: "任务详情加载完成后会显示规划模式与当前状态。",
      tone: "slate",
    };
  }
  if (task.value.status === "FAILED") {
    return {
      label: "规划中断",
      title: "任务在执行过程中失败",
      detail: task.value.errorMessage || "请重试任务或复制参数重新创建。",
      tone: "rose",
    };
  }
  if (task.value.status === "COMPLETED") {
    return {
      label: "规划完成",
      title: "规划已落地并完成渲染",
      detail: `当前已生成 ${completedOutputCount.value} / ${task.value.outputCount} 条输出。`,
      tone: "emerald",
    };
  }
  if (task.value.status === "RENDERING") {
    return {
      label: "执行渲染中",
      title: "正在按规划方案输出成片",
      detail: `当前已完成 ${completedOutputCount.value} / ${task.value.outputCount} 条输出。`,
      tone: "amber",
    };
  }
  if (task.value.status === "PLANNING") {
    return {
      label: isMixcutMode.value ? "混剪规划中" : "短剧规划中",
      title: isMixcutMode.value ? "正在组织多素材分镜脚本" : "正在生成剧情卡点方案",
      detail: "任务会在规划完成后进入渲染阶段。",
      tone: "sky",
    };
  }
  if (task.value.status === "ANALYZING") {
    return {
      label: "素材分析中",
      title: "正在读取素材基础信息",
      detail: "分析完成后会自动进入规划阶段。",
      tone: "sky",
    };
  }
  return {
    label: "排队中",
    title: "任务已创建，等待执行器处理",
    detail: "进入执行后会自动刷新为分析与规划状态。",
    tone: "slate",
  };
});

const currentFocus = computed<TraceFocusItem>(() => {
  const failure = lastTraceEvent("render.clip_failed", "task.failed", "vision.timeout", "vision.http_error", "vision.network_error", "fusion.timeout", "fusion.http_error", "fusion.network_error", "qwen.timeout", "qwen.http_error", "qwen.network_error");
  if (task.value?.status === "FAILED") {
    return {
      title: "任务当前处于失败状态",
      detail: task.value.errorMessage || (failure ? describeTraceEvent(failure).detail : "请查看最近一条错误日志定位失败点。"),
      tone: "rose",
      timestamp: failure?.timestamp ?? task.value.finishedAt ?? undefined,
    };
  }

  if (task.value?.status === "COMPLETED") {
    return {
      title: "全部剪辑已经完成",
      detail: `当前共生成 ${completedOutputCount.value} / ${task.value.outputCount} 条输出，可直接预览和下载。`,
      tone: "emerald",
      timestamp: task.value.finishedAt ?? lastTraceEvent("task.completed")?.timestamp ?? undefined,
    };
  }

  const activeRender = lastTraceEvent("render.clip_started", "render.started");
  if (task.value?.status === "RENDERING" && activeRender) {
    return {
      title: "正在执行 FFmpeg 剪辑",
      detail: `当前已完成 ${completedOutputCount.value} / ${task.value.outputCount} 条输出，进度会随着每条成片生成实时刷新。`,
      tone: "amber",
      timestamp: activeRender.timestamp,
    };
  }

  const activeAudio = lastTraceEvent("audio.peaks_detected");
  if (task.value?.status === "PLANNING" && activeAudio && !hasTraceEvent("vision.response", "heuristic.completed", "planning.completed")) {
    return {
      title: "正在融合音频节奏卡点",
      detail: "系统已经提取音频峰值，正在把它和字幕时间轴、关键帧高点一起用于切点判断。",
      tone: "amber",
      timestamp: activeAudio.timestamp,
    };
  }

  const activeVision = lastTraceEvent("vision.request", "vision.attempt");
  if (task.value?.status === "PLANNING" && activeVision && !hasTraceEvent("vision.response", "fusion.response", "heuristic.completed", "planning.completed")) {
    return {
      title: "正在生成完整镜头分析 JSON",
      detail: describeTraceEvent(activeVision).detail || "系统正在把每个视频的镜头采样帧送给视觉模型，覆盖式分析每个镜头内容。",
      tone: "sky",
      timestamp: activeVision.timestamp,
    };
  }

  const activeFusion = lastTraceEvent("fusion.request", "fusion.attempt");
  if (task.value?.status === "PLANNING" && activeFusion && !hasTraceEvent("fusion.response", "heuristic.completed", "planning.completed")) {
    return {
      title: "正在输出最终剪辑时间点",
      detail: describeTraceEvent(activeFusion).detail || "系统正在把逐镜头完整分析 JSON、字幕和音频卡点融合成最终剪辑方案。",
      tone: "fuchsia",
      timestamp: activeFusion.timestamp,
    };
  }

  const activeLLM = lastTraceEvent("qwen.request", "qwen.attempt");
  if (activeLLM && !hasTraceEvent("qwen.response", "heuristic.completed", "planning.completed")) {
    return {
      title: "正在等待大模型返回方案",
      detail: describeTraceEvent(activeLLM).detail || "模型请求已经发出，返回后会自动进入下一阶段。",
      tone: "fuchsia",
      timestamp: activeLLM.timestamp,
    };
  }

  const activePlanning = lastTraceEvent("planning.started", "heuristic.start");
  if (task.value?.status === "PLANNING" && activePlanning) {
    return {
      title: "正在生成剪辑规划",
      detail: describeTraceEvent(activePlanning).detail || "正在整理切点、标题和理由。",
      tone: activePlanning.event.startsWith("heuristic") ? "amber" : "sky",
      timestamp: activePlanning.timestamp,
    };
  }

  const activeAnalysis = lastTraceEvent("analysis.started");
  if (task.value?.status === "ANALYZING" && activeAnalysis) {
    return {
      title: "正在分析源视频素材",
      detail: "系统正在识别时长、分辨率和音轨，为后续规划做准备。",
      tone: "sky",
      timestamp: activeAnalysis.timestamp,
    };
  }

  const created = lastTraceEvent("task.created", "task.enqueued", "task.dispatched_inline");
  return {
    title: "任务已创建，等待更多进度",
    detail: "详情页会每 5 秒自动刷新一次，新的大模型调用和剪辑结果会直接出现在这里。",
    tone: "slate",
    timestamp: created?.timestamp,
  };
});

const stageProgressItems = computed<TraceProgressItem[]>(() => {
  const queueEvent = lastTraceEvent("task.created", "task.enqueued", "task.dispatched_inline", "task.claimed", "task.processing_started");
  const analysisCompleted = lastTraceEvent("analysis.completed");
  const analysisStarted = lastTraceEvent("analysis.started");
  const audioDetected = lastTraceEvent("audio.peaks_detected");
  const sceneDetected = lastTraceEvent("scene.changes_detected");
  const visionResponse = lastTraceEvent("vision.response");
  const visionFailed = lastTraceEvent("vision.timeout", "vision.http_error", "vision.network_error");
  const visionAttempt = lastTraceEvent("vision.request", "vision.attempt");
  const fusionResponse = lastTraceEvent("fusion.response");
  const fusionFailed = lastTraceEvent("fusion.timeout", "fusion.http_error", "fusion.network_error", "fusion.attempt_failed");
  const fusionAttempt = lastTraceEvent("fusion.request", "fusion.attempt", "fusion.vision_fallback");
  const llmResponse = lastTraceEvent("qwen.response");
  const heuristicCompleted = lastTraceEvent("heuristic.completed");
  const llmFailed = lastTraceEvent("qwen.timeout", "qwen.http_error", "qwen.network_error");
  const llmAttempt = lastTraceEvent("qwen.request", "qwen.attempt", "planning.started", "heuristic.start");
  const renderStarted = lastTraceEvent("render.started", "render.clip_started");
  const renderFailed = lastTraceEvent("render.clip_failed");
  const renderCompleted = lastTraceEvent("task.completed", "render.clip_completed");

  const queueStatus: ProgressStatus = queueEvent ? "done" : "pending";
  const analysisStatus: ProgressStatus =
    analysisCompleted ? "done" : task.value?.status === "FAILED" && analysisStarted ? "error" : analysisStarted || task.value?.status === "ANALYZING" ? "active" : "pending";
  const llmStatus: ProgressStatus =
    fusionResponse || llmResponse || heuristicCompleted || lastTraceEvent("planning.completed")
      ? "done"
      : task.value?.status === "FAILED" && (visionFailed || fusionFailed || llmFailed)
        ? "error"
        : fusionAttempt || visionAttempt || llmAttempt || task.value?.status === "PLANNING"
          ? "active"
          : "pending";
  const renderStatus: ProgressStatus =
    task.value?.status === "COMPLETED" || (task.value && completedOutputCount.value >= task.value.outputCount && task.value.outputCount > 0)
      ? "done"
      : task.value?.status === "FAILED" && (renderFailed || renderStarted)
        ? "error"
        : renderStarted || task.value?.status === "RENDERING"
          ? "active"
          : "pending";

  return [
    {
      key: "queue",
      label: "任务接入",
      description: "创建任务并进入执行器。",
      hint: queueEvent ? describeTraceEvent(queueEvent).title : "等待任务正式创建。",
      progress: queueEvent ? 100 : 0,
      status: queueStatus,
      tone: queueStatus === "done" ? "emerald" : "slate",
    },
    {
      key: "analysis",
      label: "素材分析",
      description: "识别时长、分辨率和音轨。",
      hint: analysisCompleted ? describeTraceEvent(analysisCompleted).detail : analysisStarted ? "正在读取素材基础信息。" : "等待开始分析。",
      progress: analysisCompleted ? 100 : analysisStarted || task.value?.status === "ANALYZING" ? 55 : 0,
      status: analysisStatus,
      tone: analysisStatus === "error" ? "rose" : analysisStatus === "done" ? "emerald" : analysisStatus === "active" ? "sky" : "slate",
    },
    {
      key: "planning",
      label: "视频理解 / 规划",
      description: "先识别剧情事件，再融合字幕、音频节奏和关键帧内容生成最终切点。",
      hint: fusionResponse
        ? describeTraceEvent(fusionResponse).detail
        : visionResponse
        ? describeTraceEvent(visionResponse).detail
        : sceneDetected
          ? describeTraceEvent(sceneDetected).detail
        : audioDetected
          ? describeTraceEvent(audioDetected).detail
        : llmResponse
          ? describeTraceEvent(llmResponse).detail
          : heuristicCompleted
            ? describeTraceEvent(heuristicCompleted).detail
            : fusionFailed
              ? describeTraceEvent(fusionFailed).detail
          : visionFailed
            ? describeTraceEvent(visionFailed).detail
            : fusionAttempt
              ? describeTraceEvent(fusionAttempt).detail || "正在准备最终剪辑规划请求。"
            : llmFailed
              ? describeTraceEvent(llmFailed).detail
              : visionAttempt
                ? describeTraceEvent(visionAttempt).detail || "正在准备视频内容理解请求。"
              : llmAttempt
                ? describeTraceEvent(llmAttempt).detail || "正在准备规划请求。"
              : "等待进入规划阶段。",
      progress: fusionResponse || llmResponse || heuristicCompleted || lastTraceEvent("planning.completed") ? 100 : fusionAttempt ? 82 : visionResponse ? 62 : sceneDetected || audioDetected || visionAttempt || llmAttempt || task.value?.status === "PLANNING" ? 42 : 0,
      status: llmStatus,
      tone: llmStatus === "error" ? "rose" : heuristicCompleted ? "amber" : fusionResponse ? "fuchsia" : fusionAttempt ? "fuchsia" : visionResponse ? "sky" : sceneDetected ? "sky" : audioDetected ? "amber" : llmResponse ? "fuchsia" : visionAttempt ? "sky" : llmStatus === "active" ? "fuchsia" : "slate",
    },
    {
      key: "render",
      label: "FFmpeg 剪辑",
      description: "按规划切片并输出成片。",
      hint: renderFailed
        ? describeTraceEvent(renderFailed).detail
        : task.value?.status === "COMPLETED"
          ? `已完成 ${completedOutputCount.value} / ${task.value.outputCount} 条输出。`
          : renderStarted || task.value?.status === "RENDERING"
            ? `已完成 ${completedOutputCount.value} / ${task.value?.outputCount ?? 0} 条输出。`
            : "等待进入渲染阶段。",
      progress: renderStatus === "done" ? 100 : renderStageProgress.value,
      status: renderStatus,
      tone: renderStatus === "error" ? "rose" : renderStatus === "done" ? "emerald" : renderStatus === "active" ? "amber" : "slate",
    },
  ];
});

function getStageState(stage: "analysis" | "planning" | "rendering") {
  if (!task.value) {
    return "pending" as const;
  }

  const progress = task.value.progress ?? 0;
  if (task.value.status === "COMPLETED") {
    return "done" as const;
  }

  if (task.value.status === "FAILED") {
    if (stage === "analysis") {
      return progress >= 10 ? "done" as const : "current" as const;
    }
    if (stage === "planning") {
      return progress >= 25 ? "done" as const : progress >= 10 ? "current" as const : "pending" as const;
    }
    return progress >= 40 ? "current" as const : progress >= 25 ? "current" as const : "pending" as const;
  }

  if (task.value.status === "PENDING") {
    return stage === "analysis" ? "current" as const : "pending" as const;
  }

  if (task.value.status === "ANALYZING") {
    if (stage === "analysis") {
      return "current" as const;
    }
    return "pending" as const;
  }

  if (task.value.status === "PLANNING") {
    if (stage === "analysis") {
      return "done" as const;
    }
    if (stage === "planning") {
      return "current" as const;
    }
    return "pending" as const;
  }

  if (task.value.status === "RENDERING") {
    if (stage === "rendering") {
      return "current" as const;
    }
    return "done" as const;
  }

  return getTaskLifecycleGroup(task.value.status as TaskStatus) === "completed" ? "done" : "pending";
}

async function loadTask() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    loading.value = false;
    stop();
    return;
  }
  loading.value = task.value === null;
  try {
    task.value = await fetchTask(taskId.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载任务详情失败";
  } finally {
    loading.value = false;
  }
}

async function handleRetry() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    return;
  }
  actionLoading.value = true;
  try {
    task.value = await retryTask(taskId.value);
    if (isTerminalTaskStatus(task.value.status)) {
      stop();
    } else {
      await start(false);
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function handleDelete() {
  errorMessage.value = "";
  if (!taskId.value) {
    errorMessage.value = "缺少任务 ID";
    return;
  }
  if (!window.confirm(`确认删除任务“${task.value?.title || taskId.value}”吗？已生成的输出和日志也会一并清理。`)) {
    return;
  }
  actionLoading.value = true;
  try {
    await deleteTask(taskId.value);
    router.push("/tasks");
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除任务失败";
  } finally {
    actionLoading.value = false;
  }
}

function openCloneFlow() {
  if (!taskId.value) {
    return;
  }
  router.push({ path: "/tasks/new", query: { cloneFrom: taskId.value } });
}

const { start, stop } = usePolling(async () => {
  await loadTask();
  if (task.value && isTerminalTaskStatus(task.value.status)) {
    stop();
  }
}, 5000);

watch(
  () => task.value?.plan?.length ?? 0,
  (length) => {
    if (!length) {
      activePlanIndex.value = 0;
      return;
    }
    activePlanIndex.value = Math.max(0, Math.min(activePlanIndex.value, length - 1));
  }
);

watch(
  taskId,
  async (_, __, onCleanup) => {
    onCleanup(stop);
    task.value = null;
    activePlanIndex.value = 0;
    outputsExpanded.value = false;
    errorMessage.value = "";
    loading.value = true;
    await start();
  },
  { immediate: true }
);
</script>

<style scoped>
.task-detail-shell {
  display: grid;
  gap: 1.5rem;
}

.task-alert,
.glass-panel {
  border-radius: 1.5rem;
  border: 1px solid #dbe4ee;
  background: #ffffff;
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.08);
}

.task-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.2rem;
  color: #be123c;
  background: #fff1f2;
}

.glass-panel {
  display: grid;
  gap: 1.5rem;
  padding: 1.4rem;
}

.glass-placeholder {
  min-height: 10rem;
  place-items: center;
  color: #475569;
  text-align: center;
}

.glass-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.hero-copy {
  min-width: 0;
  flex: 1 1 24rem;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #475569;
}

.hero-copy h1,
.plan-head h2 {
  margin: 0.5rem 0 0;
  font-size: clamp(1.9rem, 3vw, 2.6rem);
  line-height: 1;
  letter-spacing: -0.04em;
  color: #0f172a;
}

.hero-subtext,
.plan-head p,
.glass-config p,
.plan-hero p {
  margin: 0.75rem 0 0;
  color: #475569;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.button {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid transparent;
  padding: 0.65rem 1rem;
  font-size: 0.9rem;
  font-weight: 700;
  transition: transform 180ms ease, box-shadow 180ms ease;
}

.button:hover {
  transform: translateY(-1px);
}

.button.primary {
  background: linear-gradient(135deg, #0e7490, #0891b2);
  color: #f8fbff;
  box-shadow: 0 10px 20px rgba(8, 145, 178, 0.22);
}

.button.warning {
  background: #fffbeb;
  color: #92400e;
  border-color: #fcd34d;
}

.button.danger {
  background: #fff1f2;
  color: #be123c;
  border-color: #fda4af;
}

.glass-stats {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
}

.glass-stats article,
.glass-config,
.glass-plan,
.plan-tab,
.plan-hero {
  border-radius: 1rem;
  border: 1px solid #dbe4ee;
  background: #f8fafc;
  box-shadow: none;
}

.glass-stats article {
  padding: 1rem 1.05rem;
}

.glass-stats span,
.glass-config dt,
.label,
.plan-tab p {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #64748b;
}

.glass-stats strong {
  display: block;
  margin-top: 0.6rem;
  font-size: 1.7rem;
  line-height: 1;
  letter-spacing: -0.04em;
  color: #0f172a;
}

.glass-stats small {
  display: block;
  margin-top: 0.4rem;
  color: #475569;
}

.glass-timeline {
  display: grid;
  gap: 0.9rem;
}

.glass-config {
  display: grid;
  gap: 1rem;
  padding: 1.1rem;
}

.glass-config dl {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  margin: 0;
}

.glass-config dd {
  margin: 0.45rem 0 0;
  color: #0f172a;
  font-weight: 600;
  line-height: 1.5;
}

.config-row {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
}

.creative {
  white-space: pre-wrap;
}

.glass-plan {
  display: grid;
  gap: 1rem;
  padding: 1.1rem;
}

.plan-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.plan-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.plan-metrics span,
.plan-tags span {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  padding: 0.45rem 0.8rem;
  color: #334155;
}

.plan-tabs {
  display: grid;
  gap: 0.8rem;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
}

.plan-tab {
  display: grid;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  text-align: left;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.plan-tab strong,
.plan-title h3 {
  color: #0f172a;
}

.plan-tab span {
  color: #475569;
  font-size: 0.85rem;
}

.plan-tab.active,
.plan-tab:hover {
  transform: translateY(-1px);
  border-color: #67e8f9;
  background: #ecfeff;
  box-shadow: 0 8px 18px rgba(8, 145, 178, 0.14);
}

.plan-hero {
  display: grid;
  gap: 0.8rem;
  padding: 1.1rem;
}

.plan-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.plan-title span {
  color: #475569;
  font-weight: 700;
}

.plan-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

@media (max-width: 768px) {
  .task-alert {
    flex-direction: column;
    align-items: flex-start;
  }

  .glass-panel {
    padding: 1rem;
  }

  .hero-actions {
    width: 100%;
  }

  .hero-actions .button {
    flex: 1 1 100%;
  }
}
</style>

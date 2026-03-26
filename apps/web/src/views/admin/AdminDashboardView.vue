<template>
  <section class="space-y-6">
    <PageHeader
      eyebrow="Admin Overview"
      title="运营总览"
      description="在一个视图里看清任务池、异常、模型健康和最近的关键日志。"
    />

    <div v-if="errorMessage" class="rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="rounded-[24px] border border-white/10 bg-white/[0.04] p-8 text-sm text-slate-300">
      正在读取管理台总览...
    </div>

    <template v-else-if="overview">
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <article
          v-for="metric in metricCards"
          :key="metric.key"
          :class="metricToneClass(metric.tone)"
          class="rounded-[24px] border p-5 shadow-[0_18px_60px_rgba(0,0,0,0.18)]"
        >
          <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">{{ metric.label }}</p>
          <p class="mt-3 text-3xl font-semibold text-slate-950">{{ metric.value }}</p>
          <p class="mt-2 text-sm leading-6 text-slate-700">{{ metric.hint }}</p>
        </article>
      </div>

      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <section class="grid gap-4 rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.95),rgba(9,14,28,0.92))] p-5 shadow-[0_24px_70px_rgba(0,0,0,0.35)]">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] uppercase tracking-[0.32em] text-sky-300/80">Attention</p>
              <h3 class="mt-2 text-lg font-semibold text-white">需要优先处理</h3>
              <p class="mt-1 text-sm text-slate-400">失败任务和运行中任务会在这里优先露出，方便值守。</p>
            </div>
            <RouterLink to="/admin/tasks" :class="adminSecondaryButton">
              进入任务台
            </RouterLink>
          </div>

          <div class="grid gap-3">
            <article
              v-for="task in overview.recentFailures"
              :key="task.id"
              class="rounded-[22px] border border-rose-400/15 bg-rose-500/10 p-4 transition duration-200 hover:border-rose-300/30 hover:bg-rose-500/14"
            >
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded-full border border-rose-300/20 bg-rose-500/15 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-100">
                      失败
                    </span>
                    <span class="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-200">
                      {{ task.platform }}
                    </span>
                  </div>
                  <p class="mt-3 break-words text-sm font-semibold text-white">{{ task.title }}</p>
                  <p class="mt-1 break-all text-xs text-slate-300">{{ task.sourceFileName }}</p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-200">进度 {{ task.progress }}%</span>
                  <RouterLink :to="`/admin/tasks/${task.id}`" :class="adminSecondaryButtonSm">
                    查看
                  </RouterLink>
                </div>
              </div>
              <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
                <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">{{ task.aspectRatio }}</span>
                <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">{{ task.minDurationSeconds }}-{{ task.maxDurationSeconds }} 秒</span>
                <span v-if="task.hasTimedTranscript" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-sky-100">时间轴字幕</span>
                <span v-else-if="task.hasTranscript" class="rounded-full border border-fuchsia-400/20 bg-fuchsia-500/10 px-3 py-1 text-fuchsia-100">文本语义</span>
              </div>
            </article>
            <div v-if="overview.recentFailures.length === 0" class="rounded-[22px] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
              当前没有失败任务。
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <article class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">运行中</p>
              <div class="mt-3 grid gap-2">
                <div
                  v-for="task in overview.recentRunningTasks"
                  :key="task.id"
                  class="rounded-2xl border border-white/8 bg-slate-950/45 px-3 py-2"
                >
                  <p class="truncate text-sm font-medium text-white">{{ task.title }}</p>
                  <p class="mt-1 text-xs text-slate-400">{{ task.status }} · {{ task.progress }}%</p>
                </div>
                <div v-if="overview.recentRunningTasks.length === 0" class="text-sm text-slate-400">
                  当前没有运行中的任务。
                </div>
              </div>
            </article>
            <article class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">模型状态</p>
              <p class="mt-3 text-sm font-semibold text-white">{{ overview.modelReady ? "模型链路已接通" : "模型链路未完全就绪" }}</p>
              <p class="mt-2 text-sm leading-6 text-slate-300">{{ overview.primaryModel }} / {{ overview.visionModel || "无视觉模型" }}</p>
              <div class="mt-4 flex flex-wrap gap-2">
                <span class="surface-chip text-[11px]">最近 trace {{ overview.recentTraceCount }} 条</span>
                <span class="surface-chip text-[11px]">时间戳字幕 {{ overview.counts.timedSemanticTasks }}</span>
              </div>
            </article>
          </div>
        </section>

        <section class="grid gap-4 rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.92),rgba(8,14,28,0.9))] p-5 shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] uppercase tracking-[0.32em] text-sky-300/80">Live Ops</p>
              <h3 class="mt-2 text-lg font-semibold text-white">最近系统日志</h3>
              <p class="mt-1 text-sm text-slate-400">默认显示摘要，重点异常会用更高对比强调。</p>
            </div>
            <button :class="adminSecondaryButton" type="button" @click="refreshAll">
              刷新
            </button>
          </div>

          <div class="flex flex-wrap gap-2">
            <select v-model="levelFilter" class="field-select min-w-[140px] rounded-full px-4 py-2 text-sm">
              <option value="">全部级别</option>
              <option value="ERROR">ERROR</option>
              <option value="WARN">WARN</option>
              <option value="INFO">INFO</option>
            </select>
            <select v-model="stageFilter" class="field-select min-w-[160px] rounded-full px-4 py-2 text-sm">
              <option value="">全部阶段</option>
              <option value="planning">planning</option>
              <option value="vision">vision</option>
              <option value="fusion">fusion</option>
              <option value="scene">scene</option>
              <option value="render">render</option>
            </select>
          </div>

          <div class="grid gap-3">
            <article
              v-for="entry in traces"
              :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`"
              :class="traceToneClass(entry.level)"
              class="rounded-[22px] border p-4 transition duration-200 hover:-translate-y-0.5"
            >
              <div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
                <span>{{ entry.level }}</span>
                <span>{{ entry.stage }}</span>
                <span>{{ formatTime(entry.timestamp) }}</span>
              </div>
              <p class="mt-3 text-sm font-semibold text-white">{{ entry.taskTitle || entry.taskId }}</p>
              <p class="mt-1 break-words text-sm leading-6 text-slate-300">{{ entry.message }}</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <RouterLink :to="`/admin/tasks/${entry.taskId}`" :class="adminSecondaryButtonSm">
                  打开任务
                </RouterLink>
                <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300">{{ entry.event }}</span>
              </div>
            </article>
            <div v-if="traces.length === 0" class="rounded-[22px] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
              当前没有符合筛选条件的日志。
            </div>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import { fetchAdminOverview, fetchAdminTraces } from "@/api/admin";
import { usePolling } from "@/composables/usePolling";
import type { AdminOverview, AdminTraceEvent } from "@/types";

const overview = ref<AdminOverview | null>(null);
const traces = ref<AdminTraceEvent[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const levelFilter = ref("");
const stageFilter = ref("");

const adminSecondaryButton = "btn-secondary";
const adminSecondaryButtonSm = "btn-secondary btn-sm";

const metricCards = computed(() => {
  if (!overview.value) {
    return [];
  }
  return [
    { key: "total", label: "总任务", value: overview.value.counts.totalTasks, hint: "系统内全部任务", tone: "blue" as const },
    { key: "running", label: "运行中", value: overview.value.counts.runningTasks, hint: "需要持续关注的处理任务", tone: "sky" as const },
    { key: "failed", label: "失败", value: overview.value.counts.failedTasks, hint: "优先处理异常和超时", tone: "rose" as const },
    { key: "progress", label: "平均进度", value: `${overview.value.counts.averageProgress}%`, hint: "任务池整体推进情况", tone: "amber" as const },
    { key: "trace", label: "近期日志", value: overview.value.recentTraceCount, hint: "最近捕获的关键事件", tone: "slate" as const },
  ];
});

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function metricToneClass(tone: "blue" | "sky" | "rose" | "amber" | "slate") {
  switch (tone) {
    case "blue":
      return "bg-[linear-gradient(180deg,rgba(219,234,254,0.95),rgba(191,219,254,0.9))] border-sky-200/80";
    case "sky":
      return "bg-[linear-gradient(180deg,rgba(224,242,254,0.95),rgba(186,230,253,0.9))] border-sky-200/80";
    case "rose":
      return "bg-[linear-gradient(180deg,rgba(255,228,230,0.96),rgba(254,202,202,0.9))] border-rose-200/70";
    case "amber":
      return "bg-[linear-gradient(180deg,rgba(254,243,199,0.96),rgba(253,230,138,0.9))] border-amber-200/70";
    default:
      return "bg-[linear-gradient(180deg,rgba(241,245,249,0.96),rgba(226,232,240,0.92))] border-slate-200/80";
  }
}

function traceToneClass(level: string) {
  if (level === "ERROR") {
    return "border-rose-400/20 bg-rose-500/10";
  }
  if (level === "WARN") {
    return "border-amber-400/20 bg-amber-500/10";
  }
  return "border-white/8 bg-slate-950/55";
}

async function loadOverview() {
  overview.value = await fetchAdminOverview();
}

async function loadTraces() {
  traces.value = await fetchAdminTraces({
    limit: 10,
    level: levelFilter.value || undefined,
    stage: stageFilter.value || undefined,
  });
}

async function refreshAll() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await Promise.all([loadOverview(), loadTraces()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取管理台总览失败";
  } finally {
    loading.value = false;
  }
}

const { start } = usePolling(refreshAll, 6000);

watch([levelFilter, stageFilter], () => {
  void loadTraces();
});

onMounted(async () => {
  await start();
});
</script>

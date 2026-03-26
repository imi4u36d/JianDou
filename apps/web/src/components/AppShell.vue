<template>
  <div class="relative z-10 mx-auto flex min-h-screen max-w-[1480px] flex-col px-3 py-3 sm:px-5 lg:px-8 lg:py-6">
    <header class="relative isolate mb-6 overflow-hidden rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,10,24,0.96),rgba(7,12,28,0.9))] shadow-[0_28px_110px_rgba(0,0,0,0.48)] backdrop-blur-2xl">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.2),transparent_30%),radial-gradient(circle_at_top_right,rgba(245,158,11,0.16),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_28%)]"></div>
      <div class="pointer-events-none absolute left-0 top-6 h-40 w-40 rounded-full bg-sky-500/10 blur-3xl"></div>
      <div class="pointer-events-none absolute right-0 top-10 h-52 w-52 rounded-full bg-amber-400/10 blur-3xl"></div>

      <div class="relative grid gap-6 border-b border-white/10 px-5 py-5 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] lg:px-7 lg:py-6">
        <div class="max-w-3xl">
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-100">AI Drama Clip Workbench</span>
            <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-200">{{ executionModeLabel }}</span>
          </div>
          <h1 class="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-[3.35rem] lg:leading-[1.02]">
            AI Cut
          </h1>
          <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-300 sm:text-[15px]">
            以任务为中心的视频切条工作台。上传、规划、渲染和复盘都在同一条路径里完成，适合批量素材生产和快速迭代。
          </p>
          <div class="mt-5 flex flex-wrap gap-2">
            <RouterLink
              to="/tasks"
              class="btn-secondary"
            >
              任务列表
            </RouterLink>
            <RouterLink
              to="/tasks/new"
              class="btn-primary"
            >
              新建任务
            </RouterLink>
            <RouterLink
              to="/admin"
              class="btn-ghost"
            >
              管理后台
            </RouterLink>
          </div>
        </div>

        <div class="grid gap-3">
          <div class="surface-tile p-4 backdrop-blur">
            <p class="text-[11px] uppercase tracking-[0.28em] text-slate-400">模型状态</p>
            <div class="mt-3 flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm font-medium text-white">{{ modelTitle }}</p>
                <p class="mt-1 text-xs leading-5 text-slate-400">{{ modelDescription }}</p>
              </div>
              <span
                class="shrink-0 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]"
                :class="modelBadgeClass"
              >
                {{ modelStatusLabel }}
              </span>
            </div>
          </div>

          <div class="surface-tile p-4">
            <p class="text-[11px] uppercase tracking-[0.28em] text-slate-400">运行窗口</p>
            <div class="mt-3 grid gap-2 rounded-2xl border border-white/8 bg-slate-950/40 p-3 text-sm">
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500">模式</span>
                <span class="font-medium text-white">{{ executionModeLabel }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500">主模型</span>
                <span class="truncate font-medium text-white">{{ health?.runtime.model.primary_model || "读取中" }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="relative grid gap-3 px-5 py-4 sm:grid-cols-2 xl:grid-cols-4 sm:px-6 lg:px-7">
        <div class="surface-tile p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">流程</p>
          <p class="mt-2 text-sm font-medium text-white">Upload → Plan → Render</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">把复杂参数变成可重复的生产流程。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">策略</p>
          <p class="mt-2 text-sm font-medium text-white">Preset + Clone + Review</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">先快跑，再根据结果回收优化。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">模式</p>
          <p class="mt-2 text-sm font-medium text-white">{{ executionModeLabel }}</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">高对比、低噪音、适合长时间盯任务队列。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">主模型</p>
          <p class="mt-2 text-sm font-medium text-white">{{ health?.runtime.model.primary_model || "读取中" }}</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">
            <template v-if="health?.runtime.model.fallback_model">{{ health.runtime.model.fallback_model }}</template>
            <template v-else>无回退模型</template>
          </p>
        </div>
      </div>
    </header>
    <main class="flex-1 pb-8">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchHealth } from "@/api/health";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);

const modelStatusLabel = computed(() => {
  if (!health.value) {
    return "加载中";
  }
  return health.value.runtime.model.ready ? "就绪" : "待配置";
});

const modelBadgeClass = computed(() => {
  if (!health.value) {
    return "bg-slate-500/15 text-slate-200";
  }
  return health.value.runtime.model.ready
    ? "bg-emerald-500/15 text-emerald-100"
    : "bg-amber-500/15 text-amber-100";
});

const modelTitle = computed(() => {
  if (!health.value) {
    return "读取运行状态中";
  }
  return health.value.runtime.model.ready ? "大模型规划已接通" : "模型配置未完成";
});

const modelDescription = computed(() => {
  if (!health.value) {
    return "正在读取 API、模型和规划能力配置。";
  }
  if (health.value.runtime.model.ready) {
    if (
      health.value.runtime.planning_capabilities.audio_peak_signal &&
      health.value.runtime.planning_capabilities.scene_boundary_signal &&
      health.value.runtime.planning_capabilities.fusion_timeline_planning
    ) {
      return "已启用四信号两阶段规划：视觉事件、字幕、音频卡点和镜头切换会一起决定最终切点。";
    }
    if (health.value.runtime.planning_capabilities.visual_event_reasoning) {
      return "已启用视觉事件识别，会先分析关键帧里的冲突、反转和高燃点，再交给规划模型决定切点。";
    }
    if (health.value.runtime.planning_capabilities.subtitle_visual_fusion) {
      return "已启用视频内容理解 + 字幕时间轴融合，会把关键帧高点和对白冲突点一起拿来决定切点。";
    }
    if (health.value.runtime.planning_capabilities.visual_content_analysis) {
      return "已启用视频内容理解规划，会先分析关键帧里的冲突、反转和高燃点，再决定切点。";
    }
    return health.value.runtime.planning_capabilities.timed_transcript_supported
      ? "支持带时间戳字幕驱动的语义规划，不需要消耗 token 做在线自检。"
      : "已配置模型，但语义规划能力未完全打开。";
  }
  const errors = health.value.runtime.model.config_errors.join(", ");
  return errors ? `缺失项：${errors}` : "当前仅能依赖本地启发式切条。";
});

const executionModeLabel = computed(() => {
  if (!health.value) {
    return "Dark workbench";
  }
  return health.value.runtime.execution_mode === "queue" ? "Queue workbench" : "Inline workbench";
});

onMounted(async () => {
  try {
    health.value = await fetchHealth();
  } catch {
    health.value = null;
  }
});
</script>

<template>
  <div class="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
    <header class="mb-6 overflow-hidden rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.94),rgba(8,11,24,0.82))] shadow-[0_24px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl">
      <div class="flex flex-col gap-5 border-b border-white/10 px-5 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <div class="max-w-3xl">
          <p class="text-xs font-semibold uppercase tracking-[0.4em] text-rose-300/90">AI Drama Clip Workbench</p>
          <h1 class="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            AI Cut
          </h1>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-300 sm:text-[15px]">
            以任务为中心的视频切条工作台。上传、规划、渲染和复盘都在同一条路径里完成，适合批量素材生产和快速迭代。
          </p>
        </div>
        <nav class="flex flex-wrap gap-2">
          <RouterLink to="/tasks" class="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-100 transition duration-200 hover:border-rose-300/40 hover:bg-white/10">
            任务列表
          </RouterLink>
          <RouterLink to="/tasks/new" class="rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-white transition duration-200 hover:bg-rose-400">
            新建任务
          </RouterLink>
        </nav>
      </div>

      <div class="grid gap-3 px-5 py-4 sm:grid-cols-2 xl:grid-cols-4 sm:px-6">
        <div class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">流程</p>
          <p class="mt-2 text-sm font-medium text-white">Upload → Plan → Render</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">把复杂参数变成可重复的生产流程。</p>
        </div>
        <div class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">策略</p>
          <p class="mt-2 text-sm font-medium text-white">Preset + Clone + Review</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">先快跑，再根据结果回收优化。</p>
        </div>
        <div class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.32em] text-slate-400">模式</p>
          <p class="mt-2 text-sm font-medium text-white">{{ executionModeLabel }}</p>
          <p class="mt-2 text-xs leading-5 text-slate-400">高对比、低噪音、适合长时间盯任务队列。</p>
        </div>
        <div class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.32em] text-slate-400">模型状态</p>
              <p class="mt-2 text-sm font-medium text-white">{{ modelTitle }}</p>
            </div>
            <span
              class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]"
              :class="modelBadgeClass"
            >
              {{ modelStatusLabel }}
            </span>
          </div>
          <p class="mt-2 text-xs leading-5 text-slate-400">{{ modelDescription }}</p>
          <p v-if="health?.runtime.model.primary_model" class="mt-2 text-[11px] text-slate-500">
            {{ health.runtime.model.primary_model }}
            <template v-if="health.runtime.model.fallback_model"> / {{ health.runtime.model.fallback_model }}</template>
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

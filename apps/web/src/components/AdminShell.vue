<template>
  <div class="relative min-h-screen overflow-x-hidden text-white">
    <div class="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(245,158,11,0.12),_transparent_24%),linear-gradient(180deg,_rgba(7,13,27,0.96)_0%,_rgba(4,8,18,0.98)_54%,_#020617_100%)]"></div>
    <div class="pointer-events-none absolute inset-x-0 top-0 z-0 h-40 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.05),transparent)] opacity-55"></div>

    <div class="relative z-10 mx-auto flex min-h-screen max-w-[1680px] flex-col px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
      <header class="overflow-hidden rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,13,28,0.96),rgba(7,11,22,0.9))] shadow-[0_24px_90px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <div class="grid gap-5 border-b border-white/10 px-5 py-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] xl:px-6">
          <div class="max-w-3xl">
            <p class="text-xs font-semibold uppercase tracking-[0.5em] text-sky-300/90">Admin Console</p>
            <h1 class="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">AI Cut 管理台</h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-300 sm:text-[15px]">
              集中处理任务、日志、系统健康和模型状态。前台继续保留创作流，后台只做高密度运营和排障。
            </p>
            <div class="mt-4 flex flex-wrap gap-2">
              <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-slate-200">
                {{ executionModeLabel }}
              </span>
              <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-slate-200">
                {{ modelTitle }}
              </span>
              <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-slate-200">
                {{ healthBadgeLabel }}
              </span>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div class="surface-tile p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">当前运行时</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ executionModeLabel }}</p>
              <p class="mt-1 text-xs text-slate-400">前后端共用同一后端运行时</p>
            </div>
            <div class="surface-tile p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">规划链路</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ modelTitle }}</p>
              <p class="mt-1 text-xs text-slate-400">{{ modelDescription }}</p>
            </div>
            <div class="surface-tile p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">Endpoint</p>
              <p class="mt-2 break-all text-sm font-semibold text-white">{{ health?.runtime.model.endpoint_host || "未读取到 endpoint" }}</p>
              <p class="mt-1 text-xs text-slate-400">仅展示 host，不暴露 key</p>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 px-5 py-4 xl:px-6">
          <nav class="flex flex-wrap gap-2">
            <RouterLink
              to="/admin"
              :class="[adminNavButton, isAdminNavActive('/admin') ? adminNavButtonActive : '']"
            >
              总览
            </RouterLink>
            <RouterLink
              to="/admin/tasks"
              :class="[adminNavButton, isAdminNavActive('/admin/tasks') ? adminNavButtonActive : '']"
            >
              任务管理
            </RouterLink>
            <RouterLink
              to="/admin/system"
              :class="[adminNavButton, isAdminNavActive('/admin/system') ? adminNavButtonActive : '']"
            >
              系统状态
            </RouterLink>
          </nav>

          <div class="flex flex-wrap gap-2">
            <RouterLink to="/tasks" :class="adminSecondaryButton">
              返回前台
            </RouterLink>
            <RouterLink to="/tasks/new" :class="adminPrimaryButton">
              新建任务
            </RouterLink>
          </div>
        </div>
      </header>

      <main class="flex-1 pb-8 pt-5">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { fetchHealth } from "@/api/health";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const route = useRoute();

const adminNavButton = "btn-nav";
const adminNavButtonActive = "btn-nav-active";
const adminSecondaryButton = "btn-secondary";
const adminPrimaryButton = "btn-primary";

function isAdminNavActive(path: string) {
  if (path === "/admin") {
    return route.path === "/admin";
  }
  return route.path === path || route.path.startsWith(`${path}/`);
}

const executionModeLabel = computed(() => {
  if (!health.value) {
    return "运行状态读取中";
  }
  return health.value.runtime.execution_mode === "queue" ? "Queue workbench" : "Inline workbench";
});

const modelTitle = computed(() => {
  if (!health.value) {
    return "模型状态读取中";
  }
  return health.value.runtime.model.ready ? "模型已就绪" : "模型待配置";
});

const modelDescription = computed(() => {
  if (!health.value) {
    return "正在读取规划能力和模型配置。";
  }
  if (health.value.runtime.model.ready) {
    if (health.value.runtime.planning_capabilities.scene_boundary_signal && health.value.runtime.planning_capabilities.fusion_timeline_planning) {
      return "四信号融合已启用，后台会围绕视觉事件、字幕、音频和镜头边界做规划。";
    }
    return "模型规划链路已接通。";
  }
  return health.value.runtime.model.config_errors.length
    ? `缺失项：${health.value.runtime.model.config_errors.join(" / ")}`
    : "本地启发式可用。";
});

const healthBadgeLabel = computed(() => {
  if (!health.value) {
    return "健康检查加载中";
  }
  return health.value.ok ? "服务正常" : "需要关注";
});

onMounted(async () => {
  try {
    health.value = await fetchHealth();
  } catch {
    health.value = null;
  }
});
</script>

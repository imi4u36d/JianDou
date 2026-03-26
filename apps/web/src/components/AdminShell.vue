<template>
  <div class="min-h-screen bg-slate-100 text-slate-900">
    <div class="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8">
      <header class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Admin Console</p>
            <h1 class="mt-1 text-xl font-semibold text-slate-900">AI Cut 管理系统</h1>
            <p class="mt-1 text-sm text-slate-600">
              面向运营与运维的数据管理界面，聚焦任务管理、异常处理和系统配置状态。
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <span class="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">{{ executionModeLabel }}</span>
            <span class="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">{{ modelTitle }}</span>
            <span :class="health?.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'" class="rounded-md border px-2.5 py-1 text-xs">
              {{ healthBadgeLabel }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
          <nav class="flex flex-wrap gap-2">
            <RouterLink to="/admin" :class="[navButtonClass, isAdminNavActive('/admin') ? navButtonActiveClass : '']">总览</RouterLink>
            <RouterLink to="/admin/tasks" :class="[navButtonClass, isAdminNavActive('/admin/tasks') ? navButtonActiveClass : '']">任务管理</RouterLink>
            <RouterLink to="/admin/system" :class="[navButtonClass, isAdminNavActive('/admin/system') ? navButtonActiveClass : '']">系统配置</RouterLink>
          </nav>

          <div class="flex flex-wrap gap-2">
            <RouterLink to="/tasks" :class="secondaryButtonClass">返回前台</RouterLink>
            <RouterLink to="/tasks/new" :class="primaryButtonClass">新建任务</RouterLink>
          </div>
        </div>
      </header>

      <main class="flex-1 py-4">
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

const navButtonClass =
  "inline-flex items-center rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900";
const navButtonActiveClass = "border-slate-900 bg-slate-900 text-white hover:bg-slate-800 hover:text-white";
const secondaryButtonClass =
  "inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50";
const primaryButtonClass =
  "inline-flex items-center rounded-md border border-slate-900 bg-slate-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-slate-800";

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

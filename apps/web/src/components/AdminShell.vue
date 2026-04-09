<template>
  <div class="admin-shell relative z-10 min-h-screen text-slate-900">
    <div class="admin-shell-decor" aria-hidden="true"></div>
    <div class="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
      <header class="admin-panel overflow-hidden">
        <div class="admin-panel-header border-b border-slate-300/80">
          <div class="admin-heading-block min-w-0">
            <p class="admin-eyebrow">Admin Console</p>
            <h1 class="admin-title">AI Cut 管理系统</h1>
            <p class="admin-subtitle max-w-3xl">
              面向运营与运维的数据管理界面，聚焦任务管理、异常处理和系统配置状态。
            </p>
          </div>
          <div class="admin-action-row">
            <span class="admin-chip">{{ executionModeLabel }}</span>
            <span class="admin-chip">{{ modelTitle }}</span>
            <span :class="health?.ok ? 'admin-chip admin-chip-success' : 'admin-chip admin-chip-warn'">
              {{ healthBadgeLabel }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-start justify-between gap-3 px-4 py-4 sm:px-5">
          <nav class="flex flex-wrap gap-2">
            <RouterLink to="/admin/dashboard" :class="[navButtonClass, isAdminNavActive('/admin/dashboard') ? navButtonActiveClass : '']">总览</RouterLink>
            <RouterLink to="/admin/tasks" :class="[navButtonClass, isAdminNavActive('/admin/tasks') ? navButtonActiveClass : '']">任务管理</RouterLink>
            <RouterLink to="/admin/system" :class="[navButtonClass, isAdminNavActive('/admin/system') ? navButtonActiveClass : '']">系统配置</RouterLink>
          </nav>

          <div class="admin-action-row">
            <RouterLink to="/tasks" :class="secondaryButtonClass">返回前台</RouterLink>
            <RouterLink to="/tasks/new" :class="primaryButtonClass">新建任务</RouterLink>
          </div>
        </div>
      </header>

      <main class="flex-1 py-5 sm:py-6">
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

const navButtonClass = "admin-nav-button";
const navButtonActiveClass = "admin-nav-button-active";
const secondaryButtonClass = "admin-btn-secondary";
const primaryButtonClass = "admin-btn-primary";

function isAdminNavActive(path: string) {
  if (path === "/admin/dashboard") {
    return route.path === "/admin" || route.path === "/admin/dashboard";
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
    : "大模型未就绪，规划链路不可用。";
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

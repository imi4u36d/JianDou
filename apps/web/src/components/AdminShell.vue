<template>
  <div class="admin-shell relative z-10 min-h-screen bg-slate-100 text-slate-900">
    <div class="admin-shell-decor" aria-hidden="true"></div>
    <div class="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
      <header class="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_18px_40px_rgba(15,23,42,0.08)]">
        <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 px-5 py-5">
          <div class="admin-heading-block min-w-0">
            <p class="admin-eyebrow">Admin Console</p>
            <h1 class="admin-title">JianDou 管理系统</h1>
            <p class="admin-subtitle max-w-3xl">
              面向运营与运维的数据管理界面，聚焦任务管理、异常处理、用户账号和邀请码状态。
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{{ executionModeLabel }}</span>
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{{ modelTitle }}</span>
            <span :class="health?.ok ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'" class="rounded-full px-3 py-1 text-xs font-semibold">
              {{ healthBadgeLabel }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
          <nav class="flex flex-wrap gap-2">
            <RouterLink to="/admin/tasks" :class="navButtonClass('/admin/tasks')">任务管理</RouterLink>
            <RouterLink to="/admin/system" :class="navButtonClass('/admin/system')">系统配置</RouterLink>
            <RouterLink to="/admin/users" :class="navButtonClass('/admin/users')">用户管理</RouterLink>
            <RouterLink to="/admin/invites" :class="navButtonClass('/admin/invites')">邀请码管理</RouterLink>
          </nav>

          <div class="flex flex-wrap items-center gap-2">
            <div class="hidden rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-right sm:block">
              <p class="text-sm font-semibold text-slate-900">{{ currentUser?.displayName || currentUser?.username }}</p>
              <p class="text-xs text-slate-500">{{ currentUser?.username }} · {{ currentUser?.role }}</p>
            </div>
            <RouterLink class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700" to="/tasks">返回前台</RouterLink>
            <RouterLink class="rounded-xl border border-slate-900 bg-slate-900 px-4 py-2 text-sm font-semibold text-white" to="/tasks/new">新建任务</RouterLink>
            <button class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700" type="button" @click="handleLogout">
              退出登录
            </button>
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
/**
 * 管理组件。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchHealth } from "@/api/health";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();

const currentUser = computed(() => authState.user.value);

function navButtonClass(path: string) {
  const active = route.path === path || route.path.startsWith(`${path}/`);
  return [
    "rounded-xl px-4 py-2 text-sm font-medium transition-colors",
    active ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
  ];
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

const healthBadgeLabel = computed(() => {
  if (!health.value) {
    return "健康检查加载中";
  }
  return health.value.ok ? "服务正常" : "需要关注";
});

async function handleLogout() {
  await logoutAndClearSession();
  await router.replace("/login");
}

onMounted(async () => {
  try {
    health.value = await fetchHealth();
  } catch {
    health.value = null;
  }
});
</script>

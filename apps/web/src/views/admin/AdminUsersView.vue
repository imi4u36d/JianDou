<template>
  <section class="admin-page admin-users-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Users</p>
          <h2 class="admin-title">用户管理</h2>
          <p class="admin-subtitle">管理可登录账号，控制启用状态，并查看最近登录时间。</p>
        </div>
        <div class="admin-action-row">
          <button class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700" type="button" @click="loadUsers">
            刷新
          </button>
        </div>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article class="admin-metric-card">
        <p class="admin-eyebrow">Total</p>
        <p class="admin-metric-value">{{ users.length }}</p>
        <p class="mt-1 text-xs text-slate-500">全部账号</p>
      </article>
      <article class="admin-metric-card">
        <p class="admin-eyebrow">Active</p>
        <p class="admin-metric-value">{{ activeCount }}</p>
        <p class="mt-1 text-xs text-slate-500">可登录账号</p>
      </article>
      <article class="admin-metric-card">
        <p class="admin-eyebrow">Disabled</p>
        <p class="admin-metric-value">{{ disabledCount }}</p>
        <p class="mt-1 text-xs text-slate-500">已禁用账号</p>
      </article>
      <article class="admin-metric-card">
        <p class="admin-eyebrow">Admins</p>
        <p class="admin-metric-value">{{ adminCount }}</p>
        <p class="mt-1 text-xs text-slate-500">管理员数量</p>
      </article>
    </div>

    <div v-if="errorMessage" class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMessage }}
    </div>

    <section class="admin-panel mt-4 overflow-hidden">
      <div class="admin-panel-header">
        <div>
          <h3 class="text-base font-semibold text-slate-900">账号列表</h3>
          <p class="mt-1 text-sm text-slate-600">用户名是唯一登录名，状态变更会在下一次请求时生效。</p>
        </div>
      </div>

      <div v-if="loading" class="px-5 py-8 text-sm text-slate-500">
        正在读取用户列表...
      </div>
      <div v-else-if="users.length === 0" class="px-5 py-8 text-sm text-slate-500">
        暂无用户数据。
      </div>
      <div v-else class="overflow-x-auto px-5 py-5">
        <table class="min-w-full text-left text-sm">
          <thead>
            <tr class="border-b border-slate-200 text-slate-500">
              <th class="pb-3 pr-4 font-medium">用户名</th>
              <th class="pb-3 pr-4 font-medium">显示名</th>
              <th class="pb-3 pr-4 font-medium">角色</th>
              <th class="pb-3 pr-4 font-medium">状态</th>
              <th class="pb-3 pr-4 font-medium">最近登录</th>
              <th class="pb-3 pr-4 font-medium">创建时间</th>
              <th class="pb-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" class="border-b border-slate-100">
              <td class="py-4 pr-4">
                <p class="font-medium text-slate-900">{{ user.username }}</p>
              </td>
              <td class="py-4 pr-4 text-slate-700">{{ user.displayName }}</td>
              <td class="py-4 pr-4">
                <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                  {{ user.role }}
                </span>
              </td>
              <td class="py-4 pr-4">
                <span :class="user.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'" class="rounded-full px-2.5 py-1 text-xs font-semibold">
                  {{ user.status === "ACTIVE" ? "启用" : "禁用" }}
                </span>
              </td>
              <td class="py-4 pr-4 text-slate-600">{{ formatDateTime(user.lastLoginAt) }}</td>
              <td class="py-4 pr-4 text-slate-600">{{ formatDateTime(user.createdAt) }}</td>
              <td class="py-4 text-right">
                <button
                  v-if="user.status === 'ACTIVE'"
                  :disabled="pendingUserId === user.id"
                  class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 disabled:opacity-50"
                  type="button"
                  @click="disableUser(user.id)"
                >
                  禁用
                </button>
                <button
                  v-else
                  :disabled="pendingUserId === user.id"
                  class="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 disabled:opacity-50"
                  type="button"
                  @click="enableUser(user.id)"
                >
                  启用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
/**
 * 管理端用户管理页。
 */
import { computed, onMounted, ref } from "vue";
import { disableAdminUser, enableAdminUser, fetchAdminUsers } from "@/api/admin";
import type { AdminUser } from "@/types";

const users = ref<AdminUser[]>([]);
const loading = ref(false);
const errorMessage = ref("");
const pendingUserId = ref<number | null>(null);

const activeCount = computed(() => users.value.filter((user) => user.status === "ACTIVE").length);
const disabledCount = computed(() => users.value.filter((user) => user.status === "DISABLED").length);
const adminCount = computed(() => users.value.filter((user) => user.role === "ADMIN").length);

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未登录";
  }
  return new Date(value).toLocaleString();
}

async function loadUsers() {
  loading.value = true;
  errorMessage.value = "";
  try {
    users.value = await fetchAdminUsers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取用户列表失败";
  } finally {
    loading.value = false;
  }
}

async function disableUser(id: number) {
  pendingUserId.value = id;
  errorMessage.value = "";
  try {
    await disableAdminUser(id);
    await loadUsers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "禁用用户失败";
  } finally {
    pendingUserId.value = null;
  }
}

async function enableUser(id: number) {
  pendingUserId.value = id;
  errorMessage.value = "";
  try {
    await enableAdminUser(id);
    await loadUsers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "启用用户失败";
  } finally {
    pendingUserId.value = null;
  }
}

onMounted(async () => {
  await loadUsers();
});
</script>

<style scoped>
.admin-users-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-users-view :deep(.admin-metric-card) {
  border: 1px solid #dbe4ee;
  border-radius: 1rem;
  background: #f8fafc;
  padding: 1rem 1.1rem;
}
</style>

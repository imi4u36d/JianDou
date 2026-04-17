<template>
  <section class="admin-page admin-invites-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Invites</p>
          <h2 class="admin-title">邀请码管理</h2>
          <p class="admin-subtitle">创建一次性邀请码、复制发放，并对未使用的邀请码执行撤销。</p>
        </div>
        <div class="admin-action-row">
          <button class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700" type="button" @click="loadInvites">
            刷新
          </button>
        </div>
      </div>
    </div>

    <section class="admin-panel mt-4 p-5">
      <div class="grid gap-4 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,0.9fr)_auto]">
        <label class="grid gap-2 text-sm text-slate-700">
          邀请角色
          <select v-model="inviteRole" class="rounded-2xl border border-slate-300 bg-white px-4 py-3">
            <option value="USER">USER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </label>
        <label class="grid gap-2 text-sm text-slate-700">
          过期时间
          <input v-model="expiresAtInput" class="rounded-2xl border border-slate-300 bg-white px-4 py-3" type="datetime-local" />
        </label>
        <div class="flex items-end">
          <button :disabled="creating" class="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50" type="button" @click="createInvite">
            {{ creating ? "创建中..." : "创建邀请码" }}
          </button>
        </div>
      </div>
      <p class="mt-3 text-xs text-slate-500">
        不填写过期时间时，后端按默认 7 天生效。
      </p>
      <div v-if="errorMessage" class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        {{ successMessage }}
      </div>
    </section>

    <section class="admin-panel mt-4 overflow-hidden">
      <div class="admin-panel-header">
        <div>
          <h3 class="text-base font-semibold text-slate-900">邀请码列表</h3>
          <p class="mt-1 text-sm text-slate-600">邀请码状态会自动反映已使用、已撤销和已过期。</p>
        </div>
      </div>

      <div v-if="loading" class="px-5 py-8 text-sm text-slate-500">
        正在读取邀请码...
      </div>
      <div v-else-if="invites.length === 0" class="px-5 py-8 text-sm text-slate-500">
        暂无邀请码。
      </div>
      <div v-else class="overflow-x-auto px-5 py-5">
        <table class="min-w-full text-left text-sm">
          <thead>
            <tr class="border-b border-slate-200 text-slate-500">
              <th class="pb-3 pr-4 font-medium">邀请码</th>
              <th class="pb-3 pr-4 font-medium">角色</th>
              <th class="pb-3 pr-4 font-medium">状态</th>
              <th class="pb-3 pr-4 font-medium">创建人</th>
              <th class="pb-3 pr-4 font-medium">过期时间</th>
              <th class="pb-3 pr-4 font-medium">使用人</th>
              <th class="pb-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invite in invites" :key="invite.id" class="border-b border-slate-100">
              <td class="py-4 pr-4">
                <p class="font-semibold tracking-[0.12em] text-slate-900">{{ invite.code }}</p>
                <p class="mt-1 text-xs text-slate-500">创建于 {{ formatDateTime(invite.createdAt) }}</p>
              </td>
              <td class="py-4 pr-4">
                <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{{ invite.role }}</span>
              </td>
              <td class="py-4 pr-4">
                <span :class="statusClass(invite.status)" class="rounded-full px-2.5 py-1 text-xs font-semibold">
                  {{ statusLabel(invite.status) }}
                </span>
              </td>
              <td class="py-4 pr-4 text-slate-700">
                {{ invite.createdBy?.displayName || invite.createdBy?.username || "-" }}
              </td>
              <td class="py-4 pr-4 text-slate-600">{{ formatDateTime(invite.expiresAt) }}</td>
              <td class="py-4 pr-4 text-slate-700">
                <span v-if="invite.usedBy">
                  {{ invite.usedBy.displayName || invite.usedBy.username }}
                </span>
                <span v-else>-</span>
              </td>
              <td class="py-4 text-right">
                <div class="flex flex-wrap justify-end gap-2">
                  <button
                    class="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700"
                    type="button"
                    @click="copyInviteCode(invite.code)"
                  >
                    复制
                  </button>
                  <button
                    v-if="invite.status === 'UNUSED'"
                    :disabled="pendingInviteId === invite.id"
                    class="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-50"
                    type="button"
                    @click="revokeInvite(invite.id)"
                  >
                    撤销
                  </button>
                </div>
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
 * 管理端邀请码管理页。
 */
import { onMounted, ref } from "vue";
import { createAdminInvite, fetchAdminInvites, revokeAdminInvite } from "@/api/admin";
import type { AdminInvite } from "@/types";

const invites = ref<AdminInvite[]>([]);
const loading = ref(false);
const creating = ref(false);
const pendingInviteId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
const inviteRole = ref<"USER" | "ADMIN">("USER");
const expiresAtInput = ref("");

function formatDateTime(value?: string | null) {
  if (!value) {
    return "默认有效期";
  }
  return new Date(value).toLocaleString();
}

function statusLabel(status: AdminInvite["status"]) {
  switch (status) {
    case "USED":
      return "已使用";
    case "REVOKED":
      return "已撤销";
    case "EXPIRED":
      return "已过期";
    default:
      return "未使用";
  }
}

function statusClass(status: AdminInvite["status"]) {
  switch (status) {
    case "USED":
      return "bg-emerald-100 text-emerald-700";
    case "REVOKED":
      return "bg-rose-100 text-rose-700";
    case "EXPIRED":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

async function loadInvites() {
  loading.value = true;
  errorMessage.value = "";
  try {
    invites.value = await fetchAdminInvites();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取邀请码失败";
  } finally {
    loading.value = false;
  }
}

async function createInvite() {
  creating.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const created = await createAdminInvite({
      role: inviteRole.value,
      expiresAt: expiresAtInput.value ? new Date(expiresAtInput.value).toISOString() : undefined
    });
    successMessage.value = `邀请码 ${created.code} 创建成功`;
    expiresAtInput.value = "";
    await loadInvites();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "创建邀请码失败";
  } finally {
    creating.value = false;
  }
}

async function revokeInvite(id: number) {
  pendingInviteId.value = id;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const invite = await revokeAdminInvite(id);
    successMessage.value = `邀请码 ${invite.code} 已撤销`;
    await loadInvites();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "撤销邀请码失败";
  } finally {
    pendingInviteId.value = null;
  }
}

async function copyInviteCode(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    successMessage.value = `邀请码 ${code} 已复制`;
  } catch {
    successMessage.value = `邀请码 ${code}`;
  }
}

onMounted(async () => {
  await loadInvites();
});
</script>

<style scoped>
.admin-invites-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}
</style>

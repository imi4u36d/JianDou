<template>
  <section class="invite-page">
    <div class="invite-page__summary">
      <el-card v-for="item in summaryCards" :key="item.label" class="surface-card invite-page__summary-card" shadow="never">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </el-card>
    </div>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="invite-page__toolbar">
          <span class="invite-page__toolbar-spacer" aria-hidden="true"></span>
          <div class="invite-page__toolbar-actions">
            <el-button :icon="Refresh" plain @click="loadInvites">刷新</el-button>
            <el-button :icon="Plus" type="primary" @click="openCreateDialog">生成</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="invites" class="invite-page__table">
        <el-table-column label="邀请码" min-width="180">
          <template #default="{ row }">
            <div class="invite-page__code-cell">
              <strong>{{ row.code }}</strong>
              <el-button link type="primary" title="复制" aria-label="复制邀请码" @click="copyInviteCode(row.code)">复制</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'ADMIN' ? 'warning' : 'info'" effect="plain">
              {{ row.role === "ADMIN" ? "管理员" : "普通用户" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="150">
          <template #default="{ row }">
            {{ actorLabel(row.createdBy) }}
          </template>
        </el-table-column>
        <el-table-column label="使用人" min-width="150">
          <template #default="{ row }">
            {{ actorLabel(row.usedBy) }}
          </template>
        </el-table-column>
        <el-table-column label="过期时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.expiresAt) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column align="right" fixed="right" label="操作" min-width="140">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'UNUSED'"
              link
              type="danger"
              title="撤销"
              aria-label="撤销邀请码"
              @click="revokeInvite(row)"
            >
              撤销
            </el-button>
            <span v-else class="invite-page__muted">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="生成邀请码" width="420px">
      <el-form label-position="top">
        <el-form-item label="账号角色">
          <el-select v-model="createForm.role">
            <el-option label="普通用户" value="USER" />
            <el-option label="管理员" value="ADMIN" />
          </el-select>
        </el-form-item>
        <el-alert
          :closable="false"
          show-icon
          type="info"
          title="邀请码仅可使用一次，生成后 12 小时内有效。"
        />
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button :loading="submitting" type="primary" @click="submitCreate">
          生成
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { createAdminInvite, fetchAdminInvites, revokeAdminInvite } from "@/admin/features/invites/services/inviteService";
import type { AdminInvite, AdminInviteActor, InviteStatus, UserRole } from "@/types";

const loading = ref(false);
const submitting = ref(false);
const invites = ref<AdminInvite[]>([]);
const createDialogVisible = ref(false);
const createForm = reactive({
  role: "USER" as UserRole
});

const summaryCards = computed(() => {
  const total = invites.value.length;
  const unused = invites.value.filter((invite) => invite.status === "UNUSED").length;
  const used = invites.value.filter((invite) => invite.status === "USED").length;
  const expired = invites.value.filter((invite) => invite.status === "EXPIRED").length;
  return [
    { label: "全部邀请码", value: total, note: "总数" },
    { label: "可使用", value: unused, note: "12 小时" },
    { label: "已使用", value: used, note: "已激活" },
    { label: "已过期", value: expired, note: "过期" }
  ];
});

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "未记录";
  }
  return date.toLocaleString("zh-CN");
}

function actorLabel(actor?: AdminInviteActor | null) {
  if (!actor) {
    return "-";
  }
  return actor.displayName || actor.username;
}

function statusLabel(status: InviteStatus) {
  switch (status) {
    case "UNUSED":
      return "可使用";
    case "USED":
      return "已使用";
    case "REVOKED":
      return "已撤销";
    case "EXPIRED":
      return "已过期";
    default:
      return status;
  }
}

function statusTagType(status: InviteStatus) {
  switch (status) {
    case "UNUSED":
      return "success";
    case "USED":
      return "info";
    case "REVOKED":
      return "warning";
    case "EXPIRED":
      return "danger";
    default:
      return "info";
  }
}

async function loadInvites() {
  loading.value = true;
  try {
    invites.value = (await fetchAdminInvites()) ?? [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取邀请码列表失败");
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  createForm.role = "USER";
  createDialogVisible.value = true;
}

async function submitCreate() {
  submitting.value = true;
  try {
    const created = await createAdminInvite({
      role: createForm.role
    });
    createDialogVisible.value = false;
    ElMessage.success(`邀请码 ${created.code} 已生成`);
    await copyInviteCode(created.code);
    await loadInvites();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "生成邀请码失败");
  } finally {
    submitting.value = false;
  }
}

async function revokeInvite(invite: AdminInvite) {
  try {
    await ElMessageBox.confirm(`确认撤销邀请码 ${invite.code} 吗？`, "撤销邀请码", {
      type: "warning",
      confirmButtonText: "确认撤销",
      cancelButtonText: "取消"
    });
    await revokeAdminInvite(invite.id);
    ElMessage.success("邀请码已撤销");
    await loadInvites();
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "撤销邀请码失败");
  }
}

async function copyInviteCode(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    ElMessage.success("邀请码已复制");
  } catch {
    ElMessage.info(`邀请码：${code}`);
  }
}

onMounted(async () => {
  await loadInvites();
});
</script>

<style scoped>
.invite-page {
  display: grid;
  gap: 20px;
}

.invite-page > *,
.invite-page .surface-card,
.invite-page__summary,
.invite-page__summary-card {
  min-width: 0;
  max-width: 100%;
}

.invite-page__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.invite-page__summary-card {
  border-radius: 22px;
}

.invite-page__summary-card :deep(.el-card__body) {
  display: grid;
  gap: 6px;
}

.invite-page__summary-card p {
  margin: 0;
  color: var(--jd-text-soft);
}

.invite-page__summary-card strong {
  font-family: inherit;
  font-size: 2rem;
}

.invite-page__summary-card span,
.invite-page__muted {
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.invite-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}

.invite-page__toolbar-spacer {
  flex: 1 1 auto;
  min-width: 0;
}

.invite-page__toolbar-actions,
.invite-page__code-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.invite-page__code-cell strong {
  font-family: inherit;
  letter-spacing: 0.1em;
}

.invite-page__alert {
  margin-bottom: 16px;
}

.invite-page__table {
  width: 100%;
}

.invite-page__code-cell :deep(.el-button),
.invite-page__table :deep(.el-button.is-link) {
  min-height: 34px;
  padding: 0 8px;
  border-radius: 9px;
  background: #eef2ff;
  font-size: 0.78rem;
  font-weight: 760;
}

.invite-page__code-cell :deep(.el-button:hover),
.invite-page__table :deep(.el-button.is-link:hover) {
  background: #eef2ff;
}

@media (max-width: 1200px) {
  .invite-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .invite-page__summary {
    grid-template-columns: 1fr;
  }

  .invite-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .invite-page__toolbar-actions {
    width: 100%;
  }

  .invite-page__toolbar-actions :deep(.el-button) {
    flex: 1;
    min-width: 0;
  }
}
</style>

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
import { Plus, Refresh } from "@element-plus/icons-vue";
import { useInviteManagement } from "@/admin/composables/useInviteManagement";
import {
  formatInviteDateTime as formatDateTime,
  inviteActorLabel as actorLabel,
  inviteStatusLabel as statusLabel,
  inviteStatusTagType as statusTagType,
} from "@/admin/features/invites/invite-management-presenters";

const {
  loading, submitting, invites, createDialogVisible, createForm, summaryCards,
  loadInvites, openCreateDialog, submitCreate, revokeInvite, copyInviteCode,
} = useInviteManagement();
</script>

<style scoped src="./invite-management-view.css"></style>

<template>
  <section class="user-page">
    <div class="user-page__summary">
      <el-card v-for="item in summaryCards" :key="item.label" class="surface-card user-page__summary-card" shadow="never">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </el-card>
    </div>

    <div v-if="initialLoading" class="user-page__summary">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <transition name="fade" mode="out-in">
      <div v-show="!initialLoading" key="content">
        <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="user-page__toolbar">
          <span class="user-page__toolbar-spacer" aria-hidden="true"></span>
          <div class="user-page__toolbar-actions">
            <el-button plain @click="resetFilters">重置</el-button>
            <el-button :icon="Refresh" plain @click="loadUsers">刷新</el-button>
            <el-button :icon="Plus" type="primary" @click="openCreateDialog">新建</el-button>
          </div>
        </div>
      </template>

      <el-form class="user-page__filters" inline @submit.prevent="loadUsers">
        <el-form-item label="关键词">
          <el-input v-model.trim="filters.q" clearable placeholder="用户名 / 显示名" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" clearable placeholder="全部角色" style="width: 160px">
            <el-option label="管理员" value="ADMIN" />
            <el-option label="普通用户" value="USER" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 160px">
            <el-option label="启用" value="ACTIVE" />
            <el-option label="禁用" value="DISABLED" />
          </el-select>
        </el-form-item>
        <el-form-item class="user-page__filters-action">
          <el-button :loading="loading" native-type="submit" type="primary">查询</el-button>
        </el-form-item>
      </el-form>

      <div class="user-page__table-scroll">
        <el-table v-loading="loading" :data="users" class="user-page__table">
          <el-table-column label="用户名" min-width="140" prop="username" />
          <el-table-column label="角色" min-width="110">
            <template #default="{ row }">
              <el-tag :type="row.role === 'ADMIN' ? 'warning' : 'info'" effect="plain">
                {{ row.role === "ADMIN" ? "管理员" : "普通用户" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" min-width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" effect="light">
                {{ row.status === "ACTIVE" ? "启用" : "禁用" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="并发额度" min-width="100">
            <template #default="{ row }">
              {{ row.taskConcurrencyLimit ?? 1 }}
            </template>
          </el-table-column>
          <el-table-column label="运行中" min-width="90">
            <template #default="{ row }">
              {{ row.runningTaskCount ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column label="排队中" min-width="90">
            <template #default="{ row }">
              {{ row.queuedTaskCount ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column label="最近登录" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.lastLoginAt) }}
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.createdAt) }}
            </template>
          </el-table-column>
          <el-table-column align="right" label="操作" min-width="210">
            <template #default="{ row }">
              <div class="user-page__actions">
                <el-button link type="primary" title="编辑" aria-label="编辑" @click="openEditDialog(row)">编辑</el-button>
                <el-button link type="warning" title="重置密码" aria-label="重置密码" @click="openPasswordDialog(row)">密码</el-button>
                <el-button
                  v-if="row.role === 'ADMIN'"
                  link
                  type="primary"
                  title="配置 Key"
                  aria-label="配置 Key"
                  @click="openModelKeyDialog(row)"
                >
                  Key
                </el-button>
                <el-button
                  v-if="row.status === 'ACTIVE'"
                  link
                  type="warning"
                  @click="toggleUserStatus(row, 'disable')"
                >
                  停用
                </el-button>
                <el-button
                  v-else
                  link
                  type="success"
                  @click="toggleUserStatus(row, 'enable')"
                >
                  启用
                </el-button>
                <el-button link type="danger" @click="removeUser(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="user-page__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalUsers"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <UserManagementDialogs
      v-model:editor-visible="editorVisible"
      v-model:model-key-dialog-visible="modelKeyDialogVisible"
      v-model:password-dialog-visible="passwordDialogVisible"
      :editor-form="editorForm"
      :editor-mode="editorMode"
      :loading-model-config="loadingModelConfig"
      :model-key-dialog-title="modelKeyDialogTitle"
      :model-key-form="modelKeyForm"
      :password-form="passwordForm"
      :submitting-editor="submittingEditor"
      :submitting-model-keys="submittingModelKeys"
      :submitting-password="submittingPassword"
      @submit-editor="submitEditor"
      @submit-model-keys="submitModelKeys"
      @submit-password="submitPassword"
      @update:editor-form="Object.assign(editorForm, $event)"
      @update:model-key-form="Object.assign(modelKeyForm, $event)"
      @update:password-form="Object.assign(passwordForm, $event)"
    />
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { Plus, Refresh } from "@element-plus/icons-vue";
import UserManagementDialogs from "@/admin/components/UserManagementDialogs.vue";
import { useUserManagement } from "@/admin/composables/useUserManagement";
import { formatDateTime } from "@/admin/features/users/user-management-presenters";

const {
  initialLoading, loading, submittingEditor, submittingPassword, loadingModelConfig,
  submittingModelKeys, users, totalUsers, currentPage, pageSize, filters, editorVisible,
  editorMode, editorForm, passwordDialogVisible, passwordForm, modelKeyDialogVisible,
  modelKeyForm, modelKeyDialogTitle, summaryCards, loadUsers, handlePageChange,
  handleSizeChange, resetFilters, openCreateDialog, openEditDialog, openPasswordDialog,
  openModelKeyDialog, submitEditor, submitPassword, submitModelKeys, toggleUserStatus, removeUser,
} = useUserManagement();
</script>

<style scoped src="./user-management-view.css"></style>

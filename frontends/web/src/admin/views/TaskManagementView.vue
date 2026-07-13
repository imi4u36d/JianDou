<template>
  <section class="task-page">
    <div class="task-page__summary">
      <el-card
        v-for="item in summaryCards"
        :key="item.label"
        class="surface-card task-page__summary-card"
        shadow="never"
      >
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </el-card>
    </div>

    <div v-if="initialLoading" class="task-page__summary">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <transition name="fade" mode="out-in">
      <div v-show="!initialLoading" key="content">
        <el-card class="surface-card" shadow="never">
          <template #header>
            <div class="task-page__toolbar">
              <div class="task-page__toolbar-spacer" aria-hidden="true"></div>
              <div class="task-page__toolbar-actions">
                <el-button plain @click="resetFilters">重置</el-button>
                <el-button
                  plain
                  type="danger"
                  :disabled="selectedTerminableIds.length === 0 || actionLoading"
                  :loading="actionLoading"
                  @click="terminateSelected"
                >
                  批量终止
                </el-button>
                <el-button
                  plain
                  type="danger"
                  :disabled="selectedTasks.length === 0 || actionLoading"
                  :loading="actionLoading"
                  @click="deleteSelected"
                >
                  批量删除
                </el-button>
                <el-button :icon="Refresh" plain @click="loadTasks">刷新</el-button>
              </div>
            </div>
          </template>

          <el-form class="task-page__filters" inline @submit.prevent="loadTasks">
            <el-form-item label="关键词">
              <el-input v-model.trim="filters.q" clearable placeholder="任务或素材" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 180px">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="排序">
              <el-select v-model="filters.sort" placeholder="排序方式" style="width: 180px">
                <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item class="task-page__filters-action">
              <el-button :loading="refreshing" native-type="submit" type="primary">查询</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="successMessage"
            :closable="false"
            class="task-page__alert"
            show-icon
            type="success"
            :title="successMessage"
          />

          <el-table
            ref="taskTable"
            v-loading="refreshing"
            :data="tasks"
            :expand-row-keys="expandedTaskIds"
            class="task-page__table"
            row-key="id"
            @expand-change="handleExpandChange"
            @row-click="handleRowClick"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column type="expand" width="48">
              <template #default="{ row }">
                <AdminTaskDetailExpansion
                  :task="row"
                  :detail="taskDetails[row.id]"
                  :loading="Boolean(detailLoading[row.id])"
                  :error="detailErrors[row.id] || ''"
                />
              </template>
            </el-table-column>
            <el-table-column label="任务信息" min-width="260">
              <template #default="{ row }">
                <div class="task-page__task-cell">
                  <strong>{{ row.title || "未命名任务" }}</strong>
                  <span>{{ row.id }}</span>
                  <span>{{ row.sourceFileName || "未记录素材文件" }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="创建人" min-width="180">
              <template #default="{ row }">
                <div class="task-page__owner-cell">
                  <strong>{{ row.ownerUsername }}</strong>
                  <el-tag v-if="row.ownerRole === 'ADMIN'" effect="plain" size="small" type="warning">管理员</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="{ row }">
                <div class="task-page__status-cell">
                  <el-tag :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
                  <span>{{ row.currentStage || "等待处理" }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="进度" min-width="180">
              <template #default="{ row }">
                <div class="task-page__progress-cell">
                  <div class="task-page__progress-head">
                    <strong>{{ row.progress ?? 0 }}%</strong>
                    <span>{{ progressHint(row) }}</span>
                  </div>
                  <el-progress :percentage="row.progress ?? 0" :show-text="false" :stroke-width="8" />
                </div>
              </template>
            </el-table-column>
            <el-table-column label="任务参数" min-width="170">
              <template #default="{ row }">
                <div class="task-page__meta-cell">
                  <span>{{ row.aspectRatio || "比例未记录" }}</span>
                  <span>{{ durationLabel(row) }}</span>
                  <span>重试 {{ row.retryCount ?? 0 }} 次</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="素材 / 结果" min-width="150">
              <template #default="{ row }">
                <div class="task-page__meta-cell">
                  <span>素材 {{ row.sourceAssetCount ?? 0 }}</span>
                  <span>成片 {{ row.completedOutputCount ?? 0 }}</span>
                  <span>镜头 {{ renderedClipLabel(row) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.createdAt) }}
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" min-width="160">
              <template #default="{ row }">
                <div class="task-page__action-cell">
                  <el-button
                    v-if="terminableStatus(row.status)"
                    link
                    type="warning"
                    :disabled="actionLoading"
                    @click.stop="terminateSingle(row)"
                  >
                    终止
                  </el-button>
                  <el-button link type="danger" :disabled="actionLoading" @click.stop="deleteSingle(row)">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="task-page__pagination">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="totalTasks"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ADMIN_TASK_SORT_OPTIONS, ADMIN_TASK_STATUS_OPTIONS, createAdminTaskPresenters } from "@/admin/features/tasks/task-management-presenters";
import AdminTaskDetailExpansion from "@/admin/components/AdminTaskDetailExpansion.vue";
import { useAdminTaskCommands } from "@/admin/composables/useAdminTaskCommands";
import { useAdminTaskList } from "@/admin/composables/useAdminTaskList";
import type { AdminTaskListItem } from "@/types";

const taskTable = ref();
const {
  initialLoading,
  refreshing,
  tasks,
  selectedTasks,
  expandedTaskIds,
  taskDetails,
  detailLoading,
  detailErrors,
  totalTasks,
  currentPage,
  pageSize,
  filters,
  summaryCards,
  selectedTerminableIds,
  loadTaskDetail,
  handleExpandChange,
  handleSelectionChange,
  loadTasks: loadTaskPage,
  handlePageChange: changeTaskPage,
  handleSizeChange: changeTaskPageSize,
  resetFilters: resetTaskFilters,
} = useAdminTaskList();

const statusOptions = ADMIN_TASK_STATUS_OPTIONS;
const sortOptions = ADMIN_TASK_SORT_OPTIONS;

const {
  actionLoading,
  successMessage,
  terminateSingle,
  terminateSelected,
  deleteSingle,
  deleteSelected,
} = useAdminTaskCommands({
  selectedTasks,
  selectedTerminableIds,
  reloadTasks: loadTasks,
});

const {
  formatDateTime,
  statusLabel,
  statusTagType,
  durationLabel,
  renderedClipLabel,
  progressHint,
  terminableStatus,
} = createAdminTaskPresenters((task) => taskDetails[task.id]);

function handleRowClick(row: AdminTaskListItem, column?: { type?: string; label?: string }) {
  if (column?.type === "selection" || column?.type === "expand" || column?.label === "操作") {
    return;
  }
  const expanding = !expandedTaskIds.value.includes(row.id);
  taskTable.value?.toggleRowExpansion(row, expanding);
  if (expanding) {
    void loadTaskDetail(row.id);
  }
}

async function loadTasks() {
  successMessage.value = "";
  await loadTaskPage();
}

function handlePageChange() {
  successMessage.value = "";
  changeTaskPage();
}

function handleSizeChange() {
  successMessage.value = "";
  changeTaskPageSize();
}

function resetFilters() {
  successMessage.value = "";
  resetTaskFilters();
}

onMounted(() => {
  void loadTasks();
});
</script>

<style scoped src="./task-management-view.css"></style>

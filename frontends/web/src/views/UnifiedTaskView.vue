<template>
  <section class="unified-tasks-view" :class="{ 'unified-tasks-view-detail-active': selectedId }">
    <UnifiedListPanel
        v-model:search-text="list.searchText.value"
        v-model:status-filter="list.statusFilter.value"
        v-model:sort-mode="list.sortMode.value"
        :filtered-items="list.filteredItems.value"
        :loading="list.loading.value"
        :selected-id="selection.selectedId.value"
        @select="handleSelect"
        @delete="handleDelete"
      />

      <section class="unified-detail-area">
      <div v-if="!selectedId" class="unified-detail-empty">
        <div class="unified-detail-empty__content">
          <h3>选择项目查看详情</h3>
          <p>或点击"新建"开始创作</p>
        </div>
      </div>

      <TaskDetailPanel
        v-else-if="selectedDetailMode === 'task'"
        :key="`task-${selectedId}`"
        :selected-task-id="selectedId"
        :tasks="list.tasks.value"
        :reload-tasks="list.load"
        @deleted="handleDeleted"
        @open-workflow="openTaskWorkflowStage"
      />

      <WorkflowResultPanel
        v-else-if="selectedDetailMode === 'workflow-result'"
        :key="`workflow-result-${selectedId}`"
        :selected-workflow-id="selectedId"
        @open-stage="openSelectedWorkflowStage"
      />

      <WorkflowDetailPanel
        v-else-if="selectedDetailMode === 'workflow-stage'"
        :key="`workflow-${activeWorkflowDetailId}`"
        :selected-workflow-id="activeWorkflowDetailId"
        :reload-workflows="list.load"
        :show-return-button="Boolean(taskWorkflowOverrideId)"
        return-button-label="任务详情"
        @open-result="openSelectedWorkflowResult"
        @return="openSelectedTaskDetail"
      />

      <div v-else class="unified-detail-empty">
        <div class="unified-detail-empty__content">
          <h3>加载中</h3>
        </div>
      </div>
    </section>

    <button
      class="unified-create-fab"
      type="button"
      aria-label="新建"
      title="新建"
      @click="createDialogOpen = true"
    >
      <IconPlus size="md" />
    </button>

    <CreateTaskDialog
      :open="createDialogOpen"
      @close="createDialogOpen = false"
      @created="handleCreated"
    />

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
/**
 * 统一任务视图。
 * 所有创作均以任务形式管理。
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUnifiedList } from "@/composables/unified/useUnifiedList";
import { useUnifiedSelection } from "@/composables/unified/useUnifiedSelection";
import UnifiedListPanel from "./unified/components/UnifiedListPanel.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
import WorkflowDetailPanel from "./unified/components/WorkflowDetailPanel.vue";
import WorkflowResultPanel from "./unified/components/WorkflowResultPanel.vue";
import CreateTaskDialog from "./unified/components/CreateTaskDialog.vue";
import { IconPlus } from "@/components/icons";
import type { UnifiedListItem } from "@/types/unified-task";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { messageApi } from "@/composables/useMessage";
import { deleteTask } from "@/api/tasks";
import { deleteWorkflow } from "@/features/workflows";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";

const list = useUnifiedList();
const selection = useUnifiedSelection();
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const route = useRoute();
const router = useRouter();

const selectedId = selection.selectedId;
const selectedItem = computed(() => selectedId.value ? list.findItem(selectedId.value) : undefined);
const createDialogOpen = ref(false);
const managingId = ref("");
const workflowStageOverrideId = ref("");
const taskWorkflowOverrideId = ref("");
const activeWorkflowDetailId = computed(() => taskWorkflowOverrideId.value || selectedId.value);

const selectedDetailMode = computed(() => {
  if (taskWorkflowOverrideId.value) {
    return "workflow-stage";
  }
  const item = selectedItem.value;
  if (!item) {
    if (list.loading.value) return "";
    return selection.selectedKind.value === "workflow" && route.query.view === "stage" ? "workflow-stage" : "task";
  }
  if (item.kind === "task") return "task";
  return workflowStageOverrideId.value === item.id ? "workflow-stage" : "workflow-result";
});

function handleSelect(item: UnifiedListItem) {
  workflowStageOverrideId.value = "";
  taskWorkflowOverrideId.value = "";
  selection.selectItem(item);
}

function openSelectedWorkflowStage() {
  if (selectedItem.value?.kind !== "workflow") return;
  workflowStageOverrideId.value = selectedItem.value.id;
  syncWorkflowViewQuery("stage");
}

function openSelectedWorkflowResult() {
  if (selectedItem.value?.kind !== "workflow") return;
  workflowStageOverrideId.value = "";
  syncWorkflowViewQuery("result");
}

function openTaskWorkflowStage(workflowId: string) {
  const resolvedWorkflowId = resolveWorkflowIdForSelectedTask(workflowId);
  if (!resolvedWorkflowId) {
    messageApi.info("当前视频任务还没有找到关联的阶段工作流");
    return;
  }
  taskWorkflowOverrideId.value = resolvedWorkflowId;
  syncWorkflowViewQuery("stage");
}

function resolveWorkflowIdForSelectedTask(workflowId: string) {
  const explicitId = String(workflowId || "").trim();
  if (explicitId) {
    return explicitId;
  }
  const item = selectedItem.value;
  if (!item || item.kind !== "task") {
    return "";
  }
  const task = item.task;
  const title = String(task?.title || item.title || "").trim();
  const taskCreatedAt = Date.parse(task?.createdAt || item.createdAt || "");
  const candidates = list.workflows.value
    .filter((workflow) => String(workflow.title || "").trim() === title)
    .sort((left, right) => {
      if (!Number.isFinite(taskCreatedAt)) {
        return 0;
      }
      return Math.abs(Date.parse(left.createdAt || "") - taskCreatedAt) - Math.abs(Date.parse(right.createdAt || "") - taskCreatedAt);
    });
  return candidates[0]?.id || "";
}

function openSelectedTaskDetail() {
  taskWorkflowOverrideId.value = "";
  syncWorkflowViewQuery("task");
}

function syncWorkflowViewQuery(view: "result" | "stage" | "task") {
  router.replace({
    query: {
      ...route.query,
      view,
    },
  }).catch(() => {});
}

async function handleDelete(item: UnifiedListItem) {
  if (managingId.value) return;
  const isWorkflow = item.kind === "workflow";
  const authenticated = await requireAuth({
    title: isWorkflow ? "登录后操作工作流" : "登录后操作任务",
    message: isWorkflow ? "删除工作流后无法恢复，请先登录或使用邀请码注册。" : "删除后无法恢复，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error(isWorkflow ? "登录后可继续操作工作流" : "登录后可继续操作任务");
    return;
  }
  const ok = await requestConfirm({
    title: isWorkflow ? "删除工作流" : "删除任务",
    message: `删除后无法恢复：${item.title || (isWorkflow ? "未命名工作流" : "未命名任务")}`,
    confirmText: "删除",
  });
  if (!ok) return;
  managingId.value = item.id;
  try {
    if (isWorkflow) {
      await deleteWorkflow(item.id);
    } else {
      await deleteTask(item.id);
    }
    if (selectedId.value === item.id) {
      workflowStageOverrideId.value = "";
      taskWorkflowOverrideId.value = "";
      selection.clearSelection();
    }
    await list.load();
    messageApi.success(isWorkflow ? "工作流已删除" : "任务已删除");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : (isWorkflow ? "删除工作流失败" : "删除任务失败"));
  } finally {
    managingId.value = "";
  }
}

function handleDeleted(taskId: string) {
  if (selectedId.value === taskId) {
    workflowStageOverrideId.value = "";
    taskWorkflowOverrideId.value = "";
    selection.clearSelection();
  }
}

function handleCreated(id: string) {
  createDialogOpen.value = false;
  // 刷新列表并选中新创建的项
  void list.load().then(() => {
    const found = list.findItem(id);
    if (found) {
      workflowStageOverrideId.value = "";
      taskWorkflowOverrideId.value = "";
      selection.selectItem(found);
    }
  });
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && selectedId.value) {
    workflowStageOverrideId.value = "";
    taskWorkflowOverrideId.value = "";
    selection.clearSelection();
  }
}

onMounted(() => {
  list.startPolling();
  // 根据 URL 恢复选中状态
  selection.resolveKind(list.findItem);
  window.addEventListener("keydown", handleKeydown);
});

watch(
  () => [selectedId.value, list.items.value.length],
  () => selection.resolveKind(list.findItem),
  { immediate: true }
);

watch(
  () => [route.query.view, selectedId.value, selectedItem.value?.kind],
  () => {
    if (selectedItem.value?.kind !== "workflow") {
      workflowStageOverrideId.value = "";
      return;
    }
    workflowStageOverrideId.value = route.query.view === "stage" ? selectedItem.value.id : "";
  },
  { immediate: true }
);

onUnmounted(() => {
  list.stopPolling();
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.unified-tasks-view {
  height: 100%;
  min-height: 0;
  background: linear-gradient(180deg, #f6fbff 0%, #ffffff 48%, #f4f5f7 100%);
  color: var(--text-strong);
  padding: 18px 22px 18px 18px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(280px, 300px) minmax(0, 1fr);
  align-content: stretch;
  gap: 22px;
  position: relative;
}

.unified-detail-area {
  min-height: 0;
  min-width: 0;
  overflow: auto;
}

.unified-detail-empty {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 200px;
}

.unified-detail-empty__content {
  text-align: center;
  color: var(--text-muted);
}

.unified-detail-empty__content h3 {
  margin: 0 0 6px;
  font-size: 1rem;
  color: var(--text-body);
}

.unified-detail-empty__content p {
  margin: 0;
  font-size: 0.85rem;
}

.unified-create-fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 50;
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border: 0;
  border-radius: 50%;
  background: var(--accent-indigo);
  color: white;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}

.unified-create-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45);
}

.unified-create-fab:active {
  transform: scale(0.95);
}

/* ── Responsive ── */

@media (max-width: 900px) {
  .unified-tasks-view {
    grid-template-columns: 1fr;
    padding: 12px;
    gap: 12px;
  }

  .unified-tasks-view-detail-active .unified-list-panel {
    display: none;
  }

  .unified-tasks-view:not(.unified-tasks-view-detail-active) .unified-detail-area {
    display: none;
  }
}

@media (max-width: 640px) {
  .unified-create-fab {
    bottom: 16px;
    right: 16px;
    width: 48px;
    height: 48px;
  }
}
</style>

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
        v-else
        :key="`task-${selectedId}`"
        :selected-task-id="selectedId"
        :tasks="list.tasks.value"
        :reload-tasks="list.load"
        @deleted="handleDeleted"
      />
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
import { onMounted, onUnmounted, ref } from "vue";
import { useUnifiedList } from "@/composables/unified/useUnifiedList";
import { useUnifiedSelection } from "@/composables/unified/useUnifiedSelection";
import UnifiedListPanel from "./unified/components/UnifiedListPanel.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
import CreateTaskDialog from "./unified/components/CreateTaskDialog.vue";
import { IconPlus } from "@/components/icons";
import type { UnifiedListItem } from "@/types/unified-task";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { messageApi } from "@/composables/useMessage";
import { deleteTask } from "@/api/tasks";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";

const list = useUnifiedList();
const selection = useUnifiedSelection();
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

const selectedId = selection.selectedId;
const createDialogOpen = ref(false);
const managingId = ref("");

function handleSelect(item: UnifiedListItem) {
  selection.selectItem(item);
}

async function handleDelete(item: UnifiedListItem) {
  if (managingId.value) return;
  const authenticated = await requireAuth({
    title: "登录后操作任务",
    message: "删除后无法恢复，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.error("登录后可继续操作任务");
    return;
  }
  const ok = await requestConfirm({
    title: "删除任务",
    message: `删除后无法恢复：${item.title || "未命名任务"}`,
    confirmText: "删除",
  });
  if (!ok) return;
  managingId.value = item.id;
  try {
    await deleteTask(item.id);
    if (selectedId.value === item.id) {
      selection.clearSelection();
    }
    await list.load();
    messageApi.success("任务已删除");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "删除任务失败");
  } finally {
    managingId.value = "";
  }
}

function handleDeleted(taskId: string) {
  if (selectedId.value === taskId) {
    selection.clearSelection();
  }
}

function handleCreated(id: string) {
  createDialogOpen.value = false;
  // 刷新列表并选中新创建的项
  void list.load().then(() => {
    const found = list.findItem(id);
    if (found) {
      selection.selectItem(found);
    }
  });
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && selectedId.value) {
    selection.clearSelection();
  }
}

onMounted(() => {
  list.startPolling();
  // 根据 URL 恢复选中状态
  selection.resolveKind(list.findItem);
  window.addEventListener("keydown", handleKeydown);
});

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

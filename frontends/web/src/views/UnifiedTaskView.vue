<template>
  <section class="unified-tasks-view" :class="{ 'unified-tasks-view-detail-active': selectedId }">
    <UnifiedListPanel
      v-model:search-text="list.searchText.value"
      v-model:status-filter="list.statusFilter.value"
      v-model:kind-filter="list.kindFilter.value"
      v-model:sort-mode="list.sortMode.value"
      :filtered-items="list.filteredItems.value"
      :loading="list.loading.value"
      :selected-id="selection.selectedId.value"
      :selected-kind="selection.selectedKind.value"
      @select="handleSelect"
    />

    <section class="unified-detail-area">
      <div v-if="!selectedId" class="unified-detail-empty">
        <div class="unified-detail-empty__content">
          <h3>选择项目查看详情</h3>
          <p>或点击"新建"开始创作</p>
        </div>
      </div>

      <TaskDetailPanel
        v-else-if="selectedKind === 'task'"
        :key="`task-${selectedId}`"
        :selected-task-id="selectedId"
        :tasks="list.tasks.value"
        :reload-tasks="list.load"
        @close="selection.clearSelection()"
        @deleted="handleDeleted"
      />

      <WorkflowDetailPanel
        v-else-if="selectedKind === 'workflow'"
        :key="`workflow-${selectedId}`"
        :selected-workflow-id="selectedId"
        :reload-workflows="list.load"
      />
    </section>

    <button
      class="unified-create-fab"
      type="button"
      aria-label="新建任务"
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
  </section>
</template>

<script setup lang="ts">
/**
 * 统一任务视图。
 * 合并工作台、阶段工作流和任务监控为单一页面。
 */
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useUnifiedList } from "@/composables/unified/useUnifiedList";
import { useUnifiedSelection } from "@/composables/unified/useUnifiedSelection";
import type { UnifiedListItem } from "@/types/unified-task";
import UnifiedListPanel from "./unified/components/UnifiedListPanel.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
import WorkflowDetailPanel from "./unified/components/WorkflowDetailPanel.vue";
import CreateTaskDialog from "./unified/components/CreateTaskDialog.vue";
import { IconPlus } from "@/components/icons";

const list = useUnifiedList();
const selection = useUnifiedSelection();

const selectedId = selection.selectedId;
const selectedKind = selection.selectedKind;
const createDialogOpen = ref(false);

function handleSelect(item: UnifiedListItem) {
  selection.selectItem(item);
}

function handleCreated(id: string, kind: "task" | "workflow") {
  createDialogOpen.value = false;
  // 刷新列表并选中新创建的项
  void list.load().then(() => {
    const found = list.findItem(id, kind);
    if (found) {
      selection.selectItem(found);
    }
  });
}

function handleDeleted(taskId: string) {
  // 删除的是当前选中的任务，清除选中状态
  if (selectedId.value === taskId) {
    selection.clearSelection();
  }
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

// 当选中的 ID 变化但 kind 为空时，尝试解析
watch(selectedId, () => {
  selection.resolveKind(list.findItem);
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
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
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

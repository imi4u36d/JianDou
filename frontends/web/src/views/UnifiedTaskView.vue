<template>
  <section class="unified-tasks-view" :class="{ 'unified-tasks-view-detail-active': selectedId }">
    <UnifiedListPanel
        v-model:search-text="list.searchText.value"
        v-model:status-filter="list.statusFilter.value"
        :filtered-items="list.filteredItems.value"
        :loading="list.loading.value"
        :loading-more="list.loadingMore.value"
        :has-more="list.hasMore.value"
        :selected-id="selection.selectedId.value"
        @select="handleSelect"
        @delete="handleDelete"
        @load-more="list.loadMore"
        @page-size-change="handlePageSizeChange"
      />

      <section class="unified-detail-area">
      <div v-if="!selectedId" class="unified-detail-empty">
        <div class="unified-detail-empty__content">
          <h3>选择项目查看详情</h3>
          <p>图片任务会在这里显示</p>
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

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
/**
 * 图片任务视图。
 */
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useUnifiedList } from "@/composables/unified/useUnifiedList";
import { useUnifiedSelection } from "@/composables/unified/useUnifiedSelection";
import UnifiedListPanel from "./unified/components/UnifiedListPanel.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
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
const managingId = ref("");
const listStarted = ref(false);
let fallbackListStartTimer: number | null = null;

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

function startListOnce() {
  if (listStarted.value) {
    return;
  }
  listStarted.value = true;
  list.startPolling();
}

function handlePageSizeChange(size: number) {
  list.setPageSize(size);
  startListOnce();
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && selectedId.value) {
    selection.clearSelection();
  }
}

onMounted(() => {
  fallbackListStartTimer = window.setTimeout(() => {
    fallbackListStartTimer = null;
    startListOnce();
  }, 300);
  // 根据 URL 恢复选中状态
  selection.resolveKind(list.findItem);
  window.addEventListener("keydown", handleKeydown);
});

watch(
  () => [selectedId.value, list.items.value.length],
  () => selection.resolveKind(list.findItem),
  { immediate: true }
);

onUnmounted(() => {
  if (fallbackListStartTimer !== null) {
    window.clearTimeout(fallbackListStartTimer);
    fallbackListStartTimer = null;
  }
  list.stopPolling();
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.unified-tasks-view {
  height: 100%;
  min-height: 0;
  background: var(--bg-base);
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
}
</style>

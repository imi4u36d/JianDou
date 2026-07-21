<template>
  <section class="image-task-view" :class="{ 'image-task-view-detail-active': selectedId }">
    <Teleport defer to="#workspace-page-actions">
      <ImageTaskToolbar
        v-model:search-text="list.searchText.value"
        v-model:status-filter="list.statusFilter.value"
        :loading="list.loading.value"
        :loading-more="list.loadingMore.value"
        :refreshing="refreshingList"
        @refresh="handleRefresh"
      />
    </Teleport>

    <ImageTaskListPanel
      :filtered-items="list.filteredItems.value"
      :loading="list.loading.value"
      :loading-more="list.loadingMore.value"
      :has-more="list.hasMore.value"
      :selected-id="selection.selectedId.value"
      :filter-active="Boolean(list.searchText.value.trim()) || list.statusFilter.value !== 'all'"
      @select="handleSelect"
      @delete="handleDelete"
      @load-more="list.loadMore"
      @page-size-change="handlePageSizeChange"
    />

    <section class="image-task-detail-area">
      <div v-if="!detailSelectedId" class="image-task-detail-empty">
        <div class="image-task-detail-empty__content">
          <span class="image-task-detail-empty__icon" aria-hidden="true">
            <IconImage size="md" />
          </span>
          <h3>选择项目查看详情</h3>
          <p>从左侧选择一项图片任务，这里会显示生成进度、结果预览和任务信息。</p>
        </div>
      </div>

      <TaskDetailPanel
        v-else
        :key="`task-${detailSelectedId}`"
        :selected-task-id="detailSelectedId"
        :tasks="list.tasks.value"
        :reload-tasks="list.load"
        detail-mode="image-task"
        :show-result-materials="false"
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
import { useImageTaskList } from "@/composables/image-tasks/useImageTaskList";
import { useImageTaskSelection } from "@/composables/image-tasks/useImageTaskSelection";
import ImageTaskListPanel from "./image-tasks/components/ImageTaskListPanel.vue";
import ImageTaskToolbar from "./image-tasks/components/ImageTaskToolbar.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
import type { ImageTaskListItem } from "@/types/image-task-list";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { messageApi } from "@/composables/useMessage";
import { deleteTask } from "@/api/tasks";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import { IconImage } from "@/components/icons";

const list = useImageTaskList();
const selection = useImageTaskSelection();
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const selectedId = selection.selectedId;
const detailSelectedId = ref("");
const managingId = ref("");
const refreshingList = ref(false);
const listStarted = ref(false);
let fallbackListStartTimer: number | null = null;
let detailSelectionTimer: number | null = null;
const DETAIL_SELECTION_DEFER_MS = 32;

function clearDetailSelectionTimer() {
  if (detailSelectionTimer !== null) {
    window.clearTimeout(detailSelectionTimer);
    detailSelectionTimer = null;
  }
}

function scheduleDetailSelection(nextId: string) {
  clearDetailSelectionTimer();
  if (!nextId) {
    detailSelectedId.value = "";
    return;
  }
  detailSelectionTimer = window.setTimeout(() => {
    detailSelectionTimer = null;
    detailSelectedId.value = nextId;
  }, DETAIL_SELECTION_DEFER_MS);
}

function handleSelect(item: ImageTaskListItem) {
  selection.selectItem(item);
}

async function handleRefresh() {
  if (refreshingList.value || list.loading.value || list.loadingMore.value) {
    return;
  }
  refreshingList.value = true;
  try {
    await list.load({ mode: "refresh" });
  } finally {
    refreshingList.value = false;
  }
}

async function handleDelete(item: ImageTaskListItem) {
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
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  if (fallbackListStartTimer !== null) {
    window.clearTimeout(fallbackListStartTimer);
    fallbackListStartTimer = null;
  }
  clearDetailSelectionTimer();
  list.stopPolling();
  window.removeEventListener("keydown", handleKeydown);
});

watch(
  selectedId,
  (nextId) => {
    scheduleDetailSelection(nextId);
  },
  { immediate: true },
);
</script>

<style scoped>
.image-task-view {
  --workspace-canvas: var(--bg-canvas);
  --workspace-surface: var(--bg-surface);
  --workspace-surface-subtle: var(--bg-soft);
  --workspace-border: #e4e7ec;
  --workspace-radius: 12px;
  --workspace-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  height: 100%;
  min-height: 0;
  background: var(--workspace-canvas);
  color: var(--text-strong);
  padding: 16px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(320px, 348px) minmax(0, 1fr);
  align-content: stretch;
  gap: 16px;
  position: relative;
}

.image-task-detail-area {
  min-height: 0;
  min-width: 0;
  overflow: auto;
  border: 1px solid var(--workspace-border);
  border-radius: var(--workspace-radius);
  background: var(--workspace-surface);
  box-shadow: var(--workspace-shadow);
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.image-task-detail-area::-webkit-scrollbar {
  display: none;
}

.image-task-detail-area :deep(.task-detail-panel) {
  min-height: 100%;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.image-task-detail-area :deep(.task-detail-panel::-webkit-scrollbar) {
  display: none;
}

.image-task-detail-empty {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 200px;
  padding: 32px;
}

.image-task-detail-empty__content {
  display: grid;
  justify-items: center;
  gap: 8px;
  max-width: 360px;
  text-align: center;
  color: var(--text-muted);
}

.image-task-detail-empty__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: 4px;
  border-radius: 14px;
  background: var(--workspace-surface-subtle);
  color: var(--accent-indigo);
}

.image-task-detail-empty__content h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 0.95rem;
  font-weight: 700;
}

.image-task-detail-empty__content p {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.82rem;
  line-height: 1.65;
}

.image-task-view :deep(.image-task-list-item) {
  border-color: var(--workspace-border);
  border-radius: 12px;
  background: var(--workspace-surface);
  box-shadow: none;
}

.image-task-view :deep(.image-task-list-item:hover),
.image-task-view :deep(.image-task-list-item:focus-within) {
  border-color: rgba(99, 102, 241, 0.26);
  background: var(--workspace-surface);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

.image-task-view :deep(.image-task-list-item-active) {
  border-color: rgba(99, 102, 241, 0.5);
  background: #f5f6ff;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.08);
}

/* ── Responsive ── */

@media (max-width: 900px) {
  .image-task-view {
    grid-template-columns: 1fr;
    padding: 12px;
    gap: 12px;
  }

  .image-task-view-detail-active .image-task-list-panel {
    display: none;
  }

  .image-task-view:not(.image-task-view-detail-active) .image-task-detail-area {
    display: none;
  }
}

@media (max-width: 640px) {
  .image-task-view {
    padding: 10px;
    gap: 10px;
  }

  .image-task-detail-empty {
    min-height: 280px;
    padding: 24px;
  }
}
</style>

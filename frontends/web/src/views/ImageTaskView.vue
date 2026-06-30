<template>
  <section class="image-task-view" :class="{ 'image-task-view-detail-active': selectedId }">
    <ImageTaskListPanel
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

    <section class="image-task-detail-area">
      <div v-if="!detailSelectedId" class="image-task-detail-empty">
        <div class="image-task-detail-empty__content">
          <h3>选择项目查看详情</h3>
          <p>图片任务会在这里显示</p>
        </div>
      </div>

      <TaskDetailPanel
        v-else
        :key="`task-${detailSelectedId}`"
        :selected-task-id="detailSelectedId"
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
import { useImageTaskList } from "@/composables/image-tasks/useImageTaskList";
import { useImageTaskSelection } from "@/composables/image-tasks/useImageTaskSelection";
import ImageTaskListPanel from "./image-tasks/components/ImageTaskListPanel.vue";
import TaskDetailPanel from "./unified/components/TaskDetailPanel.vue";
import type { ImageTaskListItem } from "@/types/image-task-list";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { messageApi } from "@/composables/useMessage";
import { deleteTask } from "@/api/tasks";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";

const list = useImageTaskList();
const selection = useImageTaskSelection();
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const selectedId = selection.selectedId;
const detailSelectedId = ref("");
const managingId = ref("");
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

watch(selectedId, (nextId) => {
  scheduleDetailSelection(nextId);
}, { immediate: true });
</script>

<style scoped>
.image-task-view {
  height: 100%;
  min-height: 0;
  background: var(--bg-base);
  color: var(--text-strong);
  padding: 18px 22px 18px 18px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
  align-content: stretch;
  gap: 22px;
  position: relative;
}

.image-task-detail-area {
  min-height: 0;
  min-width: 0;
  overflow: auto;
}

.image-task-detail-empty {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 200px;
}

.image-task-detail-empty__content {
  text-align: center;
  color: var(--text-muted);
}

.image-task-detail-empty__content h3 {
  margin: 0 0 6px;
  font-size: 1rem;
  color: var(--text-body);
}

.image-task-detail-empty__content p {
  margin: 0;
  font-size: 0.85rem;
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
}
</style>

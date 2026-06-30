/**
 * 图片任务选择状态组合式逻辑。
 * 管理右侧详情面板当前选中的任务，与 URL query 参数同步。
 */
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { ImageTaskListItem } from "@/types/image-task-list";

export function useImageTaskSelection() {
  const route = useRoute();
  const router = useRouter();

  const selectedId = ref("");

  /**
   * 从路由 query 参数读取选中状态。
   */
  function routeSelectedId() {
    const rawSelected = route.query.selected;

    const nextId = Array.isArray(rawSelected)
      ? rawSelected[0] ?? ""
      : rawSelected ?? "";

    return String(nextId).trim();
  }

  function applyRouteQuery() {
    const nextId = routeSelectedId();
    if (selectedId.value !== nextId) {
      selectedId.value = nextId;
    }
  }

  /**
   * 将选中状态写入 URL query 参数。
   */
  function syncToRoute(nextId: string) {
    if (routeSelectedId() === nextId) {
      return;
    }
    const query = { ...route.query };
    if (nextId) {
      query.selected = nextId;
    } else {
      delete query.selected;
    }
    router.replace({ query }).catch(() => {});
  }

  /**
   * 选中一个图片任务。
   */
  function selectItem(item: ImageTaskListItem) {
    selectedId.value = item.id;
    syncToRoute(item.id);
  }

  /**
   * 通过 ID 选中。
   */
  function selectById(id: string) {
    selectedId.value = id;
    syncToRoute(id);
  }

  /**
   * 清除选中状态。
   */
  function clearSelection() {
    selectedId.value = "";
    syncToRoute("");
  }

  // 路由变化时重新应用 query
  watch(
    () => route.query.selected,
    () => applyRouteQuery(),
    { immediate: true }
  );

  return {
    selectedId,
    selectItem,
    selectById,
    clearSelection,
  };
}

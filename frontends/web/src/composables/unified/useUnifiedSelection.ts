/**
 * 统一选择状态组合式逻辑。
 * 管理右侧面板当前选中的项，与 URL query 参数同步。
 */
import { ref, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { UnifiedListItem } from "@/types/unified-task";

const QUERY_SYNC_DELAY_MS = 160;

export function useUnifiedSelection() {
  const route = useRoute();
  const router = useRouter();

  const selectedId = ref("");

  let querySyncTimer: number | null = null;

  /**
   * 从路由 query 参数读取选中状态。
   */
  function applyRouteQuery() {
    const rawSelected = route.query.selected;

    const nextId = Array.isArray(rawSelected)
      ? rawSelected[0] ?? ""
      : rawSelected ?? "";

    selectedId.value = String(nextId).trim();
  }

  /**
   * 将选中状态写入 URL query 参数（防抖）。
   */
  function syncToRoute() {
    if (querySyncTimer !== null) {
      window.clearTimeout(querySyncTimer);
    }
    querySyncTimer = window.setTimeout(() => {
      querySyncTimer = null;
      const query: Record<string, string> = {};
      if (selectedId.value) {
        query.selected = selectedId.value;
      }
      router.replace({ query }).catch(() => {});
    }, QUERY_SYNC_DELAY_MS);
  }

  /**
   * 选中一个列表项。
   */
  function selectItem(item: UnifiedListItem) {
    selectedId.value = item.id;
    syncToRoute();
  }

  /**
   * 通过 ID 选中（用于路由恢复）。
   */
  function selectById(id: string) {
    selectedId.value = id;
  }

  /**
   * 清除选中状态。
   */
  function clearSelection() {
    selectedId.value = "";
    syncToRoute();
  }

  /**
   * 根据已加载的列表项解析选中状态（当 ID 存在时确认项存在）。
   */
  function resolveKind(findItem: (id: string) => UnifiedListItem | undefined) {
    if (!selectedId.value) return;
    findItem(selectedId.value);
  }

  // 路由变化时重新应用 query
  watch(
    () => route.query.selected,
    () => applyRouteQuery(),
    { immediate: true }
  );

  onUnmounted(() => {
    if (querySyncTimer !== null) {
      window.clearTimeout(querySyncTimer);
      querySyncTimer = null;
    }
  });

  return {
    selectedId,
    selectItem,
    selectById,
    clearSelection,
    resolveKind,
  };
}

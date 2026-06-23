/**
 * 统一选择状态组合式逻辑。
 * 管理右侧面板当前选中的项，与 URL query 参数同步。
 */
import { ref, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { UnifiedItemKind, UnifiedListItem } from "@/types/unified-task";

const QUERY_SYNC_DELAY_MS = 160;

export function useUnifiedSelection() {
  const route = useRoute();
  const router = useRouter();

  const selectedId = ref("");
  const selectedKind = ref<UnifiedItemKind | "">("");

  let querySyncTimer: number | null = null;

  /**
   * 从路由 query 参数读取选中状态。
   */
  function applyRouteQuery() {
    const rawSelected = route.query.selected;
    const rawKind = route.query.kind;

    const nextId = Array.isArray(rawSelected)
      ? rawSelected[0] ?? ""
      : rawSelected ?? "";

    const nextKind = Array.isArray(rawKind)
      ? rawKind[0] ?? ""
      : rawKind ?? "";

    selectedId.value = String(nextId).trim();

    if (nextKind === "task" || nextKind === "workflow") {
      selectedKind.value = nextKind;
    } else {
      // kind 缺失时留空，由 useUnifiedList.findItem 自动查找
      selectedKind.value = "";
    }
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
      if (selectedKind.value) {
        query.kind = selectedKind.value;
      }
      router.replace({ query }).catch(() => {});
    }, QUERY_SYNC_DELAY_MS);
  }

  /**
   * 选中一个列表项。
   */
  function selectItem(item: UnifiedListItem) {
    selectedId.value = item.id;
    selectedKind.value = item.kind;
    syncToRoute();
  }

  /**
   * 通过 ID 和 kind 选中（用于路由恢复）。
   */
  function selectById(id: string, kind?: UnifiedItemKind | "") {
    selectedId.value = id;
    selectedKind.value = kind ?? "";
  }

  /**
   * 清除选中状态。
   */
  function clearSelection() {
    selectedId.value = "";
    selectedKind.value = "";
    syncToRoute();
  }

  /**
   * 根据已加载的列表项解析 kind（当 kind 为空时使用）。
   */
  function resolveKind(findItem: (id: string, kind?: UnifiedItemKind) => UnifiedListItem | undefined) {
    if (!selectedId.value) return;
    if (selectedKind.value) return; // 已经有 kind，无需解析
    const found = findItem(selectedId.value);
    if (found) {
      selectedKind.value = found.kind;
    }
  }

  // 路由变化时重新应用 query
  watch(
    () => [route.query.selected, route.query.kind],
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
    selectedKind,
    selectItem,
    selectById,
    clearSelection,
    resolveKind,
  };
}

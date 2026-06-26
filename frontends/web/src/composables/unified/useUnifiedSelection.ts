/**
 * 统一选择状态组合式逻辑。
 * 管理右侧面板当前选中的项，与 URL query 参数同步。
 */
import { ref, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { UnifiedListItem, UnifiedListItemKind } from "@/types/unified-task";

const QUERY_SYNC_DELAY_MS = 160;

export function useUnifiedSelection() {
  const route = useRoute();
  const router = useRouter();

  const selectedId = ref("");
  const selectedKind = ref<UnifiedListItemKind | "">("");

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
    selectedKind.value = nextKind === "workflow" || nextKind === "task" ? nextKind : "";
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
      // Preserve existing stage param so stage selection survives navigation
      if (route.query.stage) {
        query.stage = String(route.query.stage);
      }
      if (selectedId.value) {
        query.selected = selectedId.value;
        if (selectedKind.value) {
          query.kind = selectedKind.value;
        }
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
   * 通过 ID 选中（用于路由恢复）。
   */
  function selectById(id: string, kind?: UnifiedListItemKind) {
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
   * 根据已加载的列表项解析选中状态（当 ID 存在时确认项存在）。
   */
  function resolveKind(findItem: (id: string) => UnifiedListItem | undefined) {
    if (!selectedId.value) return;
    const item = findItem(selectedId.value);
    if (item) {
      selectedKind.value = item.kind;
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

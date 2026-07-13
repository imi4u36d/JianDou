import { ref } from "vue";
import type { MaterialAssetLibraryItem, MaterialAssetPage, MaterialAssetQuery } from "@/types";

interface MaterialPaginationOptions {
  fetchPage: (query: MaterialAssetQuery) => Promise<MaterialAssetPage>;
  buildQuery: (offset: number) => MaterialAssetQuery;
  cacheAssets: (items: MaterialAssetLibraryItem[]) => void;
  onError: (error: unknown, mode: "replace" | "append") => void;
}

export function useMaterialPagination(options: MaterialPaginationOptions) {
  const loading = ref(false);
  const loadingMore = ref(false);
  const assets = ref<MaterialAssetLibraryItem[]>([]);
  const nextAssetOffset = ref(0);
  const hasMoreAssets = ref(false);
  let requestId = 0;

  function clearAssets() {
    requestId += 1;
    assets.value = [];
    nextAssetOffset.value = 0;
    hasMoreAssets.value = false;
    loading.value = false;
    loadingMore.value = false;
  }

  async function loadAssets() {
    const currentRequestId = ++requestId;
    loading.value = true;
    loadingMore.value = false;
    try {
      const page = await options.fetchPage(options.buildQuery(0));
      if (currentRequestId !== requestId) return false;
      assets.value = page?.items ?? [];
      options.cacheAssets(assets.value);
      nextAssetOffset.value = page?.nextOffset ?? assets.value.length;
      hasMoreAssets.value = page?.hasMore ?? false;
      return true;
    } catch (error) {
      if (currentRequestId === requestId) options.onError(error, "replace");
      return false;
    } finally {
      if (currentRequestId === requestId) loading.value = false;
    }
  }

  async function loadMoreAssets() {
    if (loading.value || loadingMore.value || !hasMoreAssets.value) return false;
    const currentRequestId = requestId;
    loadingMore.value = true;
    try {
      const page = await options.fetchPage(options.buildQuery(nextAssetOffset.value));
      if (currentRequestId !== requestId) return false;
      const existingIds = new Set(assets.value.map((asset) => asset.id));
      const appended = (page?.items ?? []).filter((asset) => !existingIds.has(asset.id));
      assets.value = [...assets.value, ...appended];
      options.cacheAssets(page?.items ?? []);
      nextAssetOffset.value = page?.nextOffset ?? assets.value.length;
      hasMoreAssets.value = page?.hasMore ?? false;
      return true;
    } catch (error) {
      if (currentRequestId === requestId) options.onError(error, "append");
      return false;
    } finally {
      if (currentRequestId === requestId) loadingMore.value = false;
    }
  }

  return {
    loading,
    loadingMore,
    assets,
    hasMoreAssets,
    clearAssets,
    loadAssets,
    loadMoreAssets,
  };
}

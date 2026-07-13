import { onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import type { AppSelectOption } from "@/components/common/app-select";
import type { MaterialAssetLibraryItem } from "@/types";

interface MaterialLibraryFilters {
  assetType: string;
}

interface MaterialLibraryTab {
  key: string;
  assetType: string;
}

interface MaterialLibraryLifecycleOptions {
  activeLibraryTab: Ref<string>;
  batchMode: Ref<boolean>;
  selectedAssetIds: Ref<string[]>;
  canUseBatchMode: Readonly<Ref<boolean>>;
  filters: MaterialLibraryFilters;
  assets: Ref<MaterialAssetLibraryItem[]>;
  libraryTabs: readonly MaterialLibraryTab[];
  typeFilterOptions: readonly AppSelectOption[];
  routeAssetType: () => unknown;
  authorize: () => Promise<boolean>;
  notifyAuthenticationRequired: () => void;
  clearAssets: () => void;
  loadAssetPage: () => Promise<boolean>;
  loadMoreAssets: () => Promise<boolean>;
  loadFavoriteFolders: () => Promise<unknown>;
  resetLibraryFilters: () => boolean;
}

export function createMaterialLibraryLoadController(options: MaterialLibraryLifecycleOptions) {
  async function loadAssets() {
    if (!(await options.authorize())) {
      options.clearAssets();
      options.notifyAuthenticationRequired();
      return false;
    }
    if (!(await options.loadAssetPage())) return false;
    const visibleIds = new Set(options.assets.value.map((asset) => asset.id));
    options.selectedAssetIds.value = options.selectedAssetIds.value.filter((id) => visibleIds.has(id));
    return true;
  }

  function resetFilters() {
    if (!options.resetLibraryFilters()) void loadAssets();
  }

  function applyRouteAssetType() {
    const routeAssetType = options.routeAssetType();
    if (typeof routeAssetType !== "string") return;
    if (!options.typeFilterOptions.some((option) => option.value === routeAssetType)) return;
    options.filters.assetType = routeAssetType;
    options.activeLibraryTab.value =
      options.libraryTabs.find((tab) => tab.assetType === routeAssetType)?.key ?? "all";
  }

  return { applyRouteAssetType, loadAssets, resetFilters };
}

export function useMaterialLibraryLifecycle(options: MaterialLibraryLifecycleOptions) {
  const loadMoreTrigger = ref<HTMLElement | null>(null);
  const controller = createMaterialLibraryLoadController(options);
  let loadMoreObserver: IntersectionObserver | null = null;

  async function loadAssets() {
    await controller.loadAssets();
  }

  function setupLoadMoreObserver() {
    if (typeof IntersectionObserver === "undefined") return;
    loadMoreObserver?.disconnect();
    loadMoreObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) void options.loadMoreAssets();
      },
      { root: null, rootMargin: "360px 0px 520px", threshold: 0.01 },
    );
    if (loadMoreTrigger.value) loadMoreObserver.observe(loadMoreTrigger.value);
  }

  onMounted(async () => {
    await options.loadFavoriteFolders();
    controller.applyRouteAssetType();
    setupLoadMoreObserver();
    await controller.loadAssets();
  });

  onBeforeUnmount(() => {
    loadMoreObserver?.disconnect();
    loadMoreObserver = null;
  });

  watch(options.activeLibraryTab, (tab) => {
    const selectedTab = options.libraryTabs.find((item) => item.key === tab);
    options.filters.assetType = selectedTab?.assetType ?? "";
    options.selectedAssetIds.value = [];
    void controller.loadAssets();
  });

  watch(options.batchMode, (enabled) => {
    if (!enabled) options.selectedAssetIds.value = [];
  });

  watch(options.canUseBatchMode, (enabled) => {
    if (!enabled) options.batchMode.value = false;
  });

  watch(loadMoreTrigger, setupLoadMoreObserver);

  watch(
    () => options.filters.assetType,
    (assetType) => {
      if (!assetType && ["image", "video"].includes(options.activeLibraryTab.value)) return;
      const nextTab = options.libraryTabs.find((tab) => tab.assetType === assetType)?.key ?? "all";
      if (
        options.activeLibraryTab.value !== nextTab
        && !["image", "video"].includes(nextTab)
      ) {
        options.activeLibraryTab.value = nextTab;
      }
    },
  );

  return {
    loadMoreTrigger,
    loadAssets,
    resetFilters: controller.resetFilters,
  };
}

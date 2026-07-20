import { computed, reactive, ref } from "vue";
import { isWorkflowArtifactAsset } from "@/features/materials/material-library-presenters";
import type { AppSelectOption } from "@/components/common/app-select";
import type { MaterialAssetLibraryItem, MaterialAssetQuery, MaterialFavoriteFolder } from "@/types";

interface MaterialLibraryStateOptions {
  assets: () => MaterialAssetLibraryItem[];
  favoriteFolders: () => MaterialFavoriteFolder[];
  favoriteAssetCache: () => Record<string, MaterialAssetLibraryItem>;
  pageLimit?: number;
}

export const materialLibraryTabs = [
  { key: "all", label: "全部", assetType: "" },
  { key: "image", label: "图片", assetType: "" },
  { key: "video", label: "视频", assetType: "" },
  { key: "character_sheet", label: "角色三视图", assetType: "character_sheet" },
  { key: "scene", label: "场景", assetType: "scene" },
  { key: "prop", label: "道具", assetType: "prop" },
  { key: "building", label: "建筑", assetType: "building" },
  { key: "vehicle", label: "载具", assetType: "vehicle" },
  { key: "workflow", label: "工作流产物", assetType: "workflow" },
];

export const materialTypeFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "角色三视图", value: "character_sheet" },
  { label: "场景", value: "scene" },
  { label: "道具", value: "prop" },
  { label: "建筑", value: "building" },
  { label: "载具", value: "vehicle" },
  { label: "自由模式", value: "free" },
  { label: "工作流产物", value: "workflow" },
];

export const materialAspectRatioFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "16:9", value: "16:9" },
  { label: "9:16", value: "9:16" },
];

export function useMaterialLibraryState(options: MaterialLibraryStateOptions) {
  const activeLibraryTab = ref("all");
  const advancedFiltersOpen = ref(false);
  const batchMode = ref(false);
  const selectedAssetIds = ref<string[]>([]);
  const activeFavoriteFolderId = ref("");
  const filters = reactive({
    q: "",
    assetType: "",
    showWorkflowArtifacts: false,
    model: "",
    aspectRatio: "",
    clipIndex: "",
  });
  const displayedAssets = computed(() => {
    const assets = options.assets();
    if (activeFavoriteFolderId.value) {
      const folder = options.favoriteFolders().find((item) => item.id === activeFavoriteFolderId.value);
      if (!folder) return [];
      const cache = options.favoriteAssetCache();
      return folder.assetIds
        .map((assetId) => assets.find((asset) => asset.id === assetId) ?? cache[assetId])
        .filter((asset): asset is MaterialAssetLibraryItem => Boolean(asset));
    }
    if (activeLibraryTab.value === "image") return assets.filter((asset) => asset.mediaType === "image");
    if (activeLibraryTab.value === "video") return assets.filter((asset) => asset.mediaType === "video");
    if (activeLibraryTab.value === "workflow") return assets.filter(isWorkflowArtifactAsset);
    if (activeLibraryTab.value === "all") return assets;
    return assets.filter((asset) => asset.assetType === activeLibraryTab.value);
  });
  const canUseBatchMode = computed(() => displayedAssets.value.length > 0);
  const activeFilterCount = computed(
    () =>
      [filters.assetType, filters.showWorkflowArtifacts, filters.model.trim(), filters.aspectRatio, filters.clipIndex]
        .filter(Boolean).length,
  );
  const materialEmptyTitle = computed(() => {
    if (activeFavoriteFolderId.value) return "收藏夹暂无素材";
    return filters.q.trim() || activeFilterCount.value > 0 || activeLibraryTab.value !== "all"
      ? "没有匹配素材"
      : "暂无素材";
  });

  function selectLibraryTab(tabKey: string) {
    activeFavoriteFolderId.value = "";
    activeLibraryTab.value = tabKey;
  }

  function toggleBatchMode() {
    if (canUseBatchMode.value) batchMode.value = !batchMode.value;
  }

  function buildQuery(): MaterialAssetQuery {
    const workflowSelected = activeLibraryTab.value === "workflow" || filters.assetType === "workflow";
    return {
      q: filters.q.trim() || undefined,
      assetType: filters.assetType as MaterialAssetQuery["assetType"],
      includeWorkflowArtifacts: filters.showWorkflowArtifacts || workflowSelected,
      model: filters.model.trim() || undefined,
      aspectRatio: filters.aspectRatio || undefined,
      clipIndex: filters.clipIndex ? Number(filters.clipIndex) : null,
    };
  }

  function buildPageQuery(offset: number): MaterialAssetQuery {
    return { ...buildQuery(), offset, limit: options.pageLimit ?? 30 };
  }

  function toggleAssetSelection(assetId: string) {
    selectedAssetIds.value = selectedAssetIds.value.includes(assetId)
      ? selectedAssetIds.value.filter((id) => id !== assetId)
      : [...selectedAssetIds.value, assetId];
  }

  function resetFilters() {
    Object.assign(filters, {
      q: "",
      assetType: "",
      showWorkflowArtifacts: false,
      model: "",
      aspectRatio: "",
      clipIndex: "",
    });
    const tabChanged = activeLibraryTab.value !== "all";
    if (tabChanged) activeLibraryTab.value = "all";
    return tabChanged;
  }

  return {
    activeLibraryTab,
    advancedFiltersOpen,
    batchMode,
    selectedAssetIds,
    activeFavoriteFolderId,
    filters,
    libraryTabs: materialLibraryTabs,
    typeFilterOptions: materialTypeFilterOptions,
    aspectRatioFilterOptions: materialAspectRatioFilterOptions,
    displayedAssets,
    canUseBatchMode,
    activeFilterCount,
    materialEmptyTitle,
    selectLibraryTab,
    toggleBatchMode,
    buildPageQuery,
    isAssetChecked: (assetId: string) => selectedAssetIds.value.includes(assetId),
    toggleAssetSelection,
    resetFilters,
  };
}

import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { createMaterialLibraryLoadController } from "@/composables/materials/useMaterialLibraryLifecycle";
import type { MaterialAssetLibraryItem } from "@/types";

function setup(overrides: Record<string, unknown> = {}) {
  const activeLibraryTab = ref("all");
  const selectedAssetIds = ref(["kept", "removed"]);
  const assets = ref([{ id: "kept" }] as MaterialAssetLibraryItem[]);
  const filters = { assetType: "" };
  const options = {
    activeLibraryTab,
    batchMode: ref(false),
    selectedAssetIds,
    canUseBatchMode: ref(true),
    filters,
    assets,
    libraryTabs: [
      { key: "all", assetType: "" },
      { key: "scene", assetType: "scene" },
    ],
    typeFilterOptions: [
      { label: "全部", value: "" },
      { label: "场景", value: "scene" },
    ],
    routeAssetType: () => "scene",
    authorize: vi.fn(async () => true),
    notifyAuthenticationRequired: vi.fn(),
    clearAssets: vi.fn(),
    loadAssetPage: vi.fn(async () => true),
    loadMoreAssets: vi.fn(async () => true),
    loadFavoriteFolders: vi.fn(async () => undefined),
    resetLibraryFilters: vi.fn(() => false),
    ...overrides,
  };
  return { activeLibraryTab, selectedAssetIds, filters, options };
}

describe("material library load controller", () => {
  it("applies supported route filters and reconciles cross-page selection", async () => {
    const { activeLibraryTab, selectedAssetIds, filters, options } = setup();
    const controller = createMaterialLibraryLoadController(options);

    controller.applyRouteAssetType();
    expect(filters.assetType).toBe("scene");
    expect(activeLibraryTab.value).toBe("scene");

    await expect(controller.loadAssets()).resolves.toBe(true);
    expect(selectedAssetIds.value).toEqual(["kept"]);
    expect(options.loadAssetPage).toHaveBeenCalledOnce();
  });

  it("clears private assets when authorization is rejected", async () => {
    const { options } = setup({ authorize: vi.fn(async () => false) });
    const controller = createMaterialLibraryLoadController(options);

    await expect(controller.loadAssets()).resolves.toBe(false);
    expect(options.clearAssets).toHaveBeenCalledOnce();
    expect(options.notifyAuthenticationRequired).toHaveBeenCalledOnce();
    expect(options.loadAssetPage).not.toHaveBeenCalled();
  });
});

import { computed, reactive, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useMaterialFavoriteCommands } from "@/composables/materials/useMaterialFavoriteCommands";
import type { MaterialAssetLibraryItem, MaterialFavoriteFolder } from "@/types";

function asset(id: string): MaterialAssetLibraryItem {
  return {
    id,
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: 1,
    selectedForNext: false,
    mediaType: "image",
    title: id,
    publicUrl: `/storage/${id}.png`,
    fileUrl: `/storage/${id}.png`,
    previewUrl: `/storage/${id}.png`,
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:00:00Z",
  };
}

function harness() {
  const asset1 = asset("asset-1");
  const favoriteFolders = ref<MaterialFavoriteFolder[]>([]);
  const activeFavoriteFolderId = ref("");
  const favoriteAssetCache = ref<Record<string, MaterialAssetLibraryItem>>({});
  const favoriteDialog = reactive({ open: false, asset: null as MaterialAssetLibraryItem | null, batchAssets: [] as MaterialAssetLibraryItem[] });
  const selectedAssetIds = ref<string[]>([]);
  const batchMode = ref(false);
  const assets = ref([asset1]);
  const dependencies = {
    requireAuthentication: vi.fn(async () => true),
    fetchFolders: vi.fn(async () => ({ folders: [{ id: "folder-1", name: "Fav", assetIds: [], createdAt: "now" }] })),
    fetchAsset: vi.fn(async (id: string) => asset(id)),
    createFolder: vi.fn(async () => ({ id: "folder-new", name: "New", assetIds: ["asset-1"], createdAt: "now" })),
    renameFolder: vi.fn(async (id: string) => ({ id, name: "Renamed", assetIds: [], createdAt: "now" })),
    deleteFolder: vi.fn(async () => ({ deleted: true, folderId: "folder-1" })),
    addAssets: vi.fn(async (id: string, request: { assetIds: string[] }) => ({ id, name: "Fav", assetIds: request.assetIds, createdAt: "now" })),
    removeAsset: vi.fn(async (id: string) => ({ id, name: "Fav", assetIds: [], createdAt: "now" })),
    message: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
  };
  const commands = useMaterialFavoriteCommands({
    favoriteFolders,
    activeFavoriteFolderId,
    favoriteAssetCache,
    favoriteDialog,
    selectedAssetIds,
    batchMode,
    assets,
    displayedAssets: computed(() => assets.value),
    requestConfirm: vi.fn(async () => true),
  }, dependencies);
  return { asset1, favoriteFolders, activeFavoriteFolderId, favoriteAssetCache, favoriteDialog, selectedAssetIds, dependencies, commands };
}

describe("material favorite commands", () => {
  it("loads account folders after authentication", async () => {
    const context = harness();

    await context.commands.loadFavoriteFolders();

    expect(context.dependencies.requireAuthentication).toHaveBeenCalledOnce();
    expect(context.favoriteFolders.value[0]?.id).toBe("folder-1");
  });

  it("creates a folder with the dialog asset and updates local state", async () => {
    const context = harness();
    context.commands.openFavoriteDialog(context.asset1);
    const complete = vi.fn();

    await context.commands.createFavoriteFolder({ name: "New", complete });

    expect(context.dependencies.createFolder).toHaveBeenCalledWith({ name: "New", assetIds: ["asset-1"] });
    expect(context.activeFavoriteFolderId.value).toBe("folder-new");
    expect(context.favoriteAssetCache.value["asset-1"]).toEqual(context.asset1);
    expect(complete).toHaveBeenCalledOnce();
  });

  it("adds selected assets to a folder from batch mode", async () => {
    const context = harness();
    context.favoriteFolders.value = [{ id: "folder-1", name: "Fav", assetIds: [], createdAt: "now" }];
    context.selectedAssetIds.value = ["asset-1"];
    context.commands.openBatchFavoriteDialog();

    context.commands.handleFavoriteDialogFolderClick("folder-1");
    await vi.waitFor(() => expect(context.dependencies.addAssets).toHaveBeenCalled());

    expect(context.dependencies.addAssets).toHaveBeenCalledWith("folder-1", { assetIds: ["asset-1"] });
    expect(context.commands.isAssetFavorited("asset-1")).toBe(true);
  });
});

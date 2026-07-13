import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MaterialAssetLibraryItem } from "@/types";

const mocks = vi.hoisted(() => ({
  deleteAsset: vi.fn(),
  renameAsset: vi.fn(),
  reuseAsset: vi.fn(),
  uploadAsset: vi.fn(),
  push: vi.fn(() => Promise.resolve()),
  requireAuth: vi.fn(() => Promise.resolve(true)),
}));

vi.mock("vue-router", () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock("@/auth/modal", () => ({ requireAuth: mocks.requireAuth }));
vi.mock("@/features/materials", () => ({
  deleteMaterialAsset: mocks.deleteAsset,
  renameMaterialAsset: mocks.renameAsset,
  reuseMaterialAsset: mocks.reuseAsset,
  uploadMaterialAsset: mocks.uploadAsset,
}));
vi.mock("@/composables/useMessage", () => ({
  messageApi: { error: vi.fn(), info: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));
vi.mock("@/utils/download", () => ({ downloadMedia: vi.fn() }));

import { useMaterialAssetCommands } from "@/composables/materials/useMaterialAssetCommands";

function asset(id: string, title = id): MaterialAssetLibraryItem {
  return {
    id,
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: 1,
    selectedForNext: false,
    mediaType: "image",
    title,
    publicUrl: `/${id}.png`,
    fileUrl: `/${id}.png`,
    previewUrl: `/${id}.png`,
    createdAt: "",
    updatedAt: "",
  };
}

function createCommands() {
  const assets = ref([asset("a", "Old"), asset("b")]);
  const selectedAssetIds = ref<string[]>([]);
  const loadAssets = vi.fn(async () => {});
  const loadFavoriteFolders = vi.fn(async () => {});
  const commands = useMaterialAssetCommands({
    assets,
    busyActionKey: ref(""),
    selectedAssetIds,
    previewAsset: ref(null),
    cacheMaterialAssets: vi.fn(),
    syncPreviewAsset: vi.fn(),
    loadAssets,
    loadFavoriteFolders,
    requestConfirm: vi.fn(async () => true),
  });
  return { ...commands, assets, loadAssets, loadFavoriteFolders, selectedAssetIds };
}

describe("useMaterialAssetCommands", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renames an asset and updates local state", async () => {
    const updated = asset("a", "New");
    mocks.renameAsset.mockResolvedValue(updated);
    const state = createCommands();

    await state.openRenameDialog(state.assets.value[0]);
    state.renameDialog.title = "New";
    await state.commitAssetRename();

    expect(mocks.renameAsset).toHaveBeenCalledWith("a", { title: "New" });
    expect(state.assets.value[0].title).toBe("New");
    expect(state.renameDialog.open).toBe(false);
  });

  it("deletes every selected asset then refreshes list and folders", async () => {
    const state = createCommands();
    state.selectedAssetIds.value = ["a", "b"];

    await state.handleBatchDelete();

    expect(mocks.deleteAsset.mock.calls).toEqual([["a"], ["b"]]);
    expect(state.selectedAssetIds.value).toEqual([]);
    expect(state.loadAssets).toHaveBeenCalledOnce();
    expect(state.loadFavoriteFolders).toHaveBeenCalledOnce();
  });
});

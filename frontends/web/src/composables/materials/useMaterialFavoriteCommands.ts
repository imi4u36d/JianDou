import type { ComputedRef, Ref } from "vue";
import { requireAuth } from "@/auth/modal";
import {
  addMaterialFavoriteAssets,
  createMaterialFavoriteFolder,
  deleteMaterialFavoriteFolder,
  fetchMaterialAsset,
  fetchMaterialFavoriteFolders,
  removeMaterialFavoriteAsset,
  renameMaterialFavoriteFolder,
} from "@/api/material-assets";
import { messageApi } from "@/composables/useMessage";
import type { MaterialAssetLibraryItem, MaterialFavoriteFolder } from "@/types";
import type {
  MaterialFavoriteCreateRequest,
  MaterialFavoriteRenameRequest,
} from "@/views/materials/components/material-favorite-dialog";

interface FavoriteDialogState {
  open: boolean;
  asset: MaterialAssetLibraryItem | null;
  batchAssets: MaterialAssetLibraryItem[];
}

interface MaterialFavoriteCommandOptions {
  favoriteFolders: Ref<MaterialFavoriteFolder[]>;
  activeFavoriteFolderId: Ref<string>;
  favoriteAssetCache: Ref<Record<string, MaterialAssetLibraryItem>>;
  favoriteDialog: FavoriteDialogState;
  selectedAssetIds: Ref<string[]>;
  batchMode: Ref<boolean>;
  assets: Ref<MaterialAssetLibraryItem[]>;
  displayedAssets: ComputedRef<MaterialAssetLibraryItem[]>;
  requestConfirm: (options: { title: string; message: string; confirmText: string }) => Promise<boolean>;
}

export interface MaterialFavoriteCommandDependencies {
  requireAuthentication: typeof requireAuth;
  fetchFolders: typeof fetchMaterialFavoriteFolders;
  fetchAsset: typeof fetchMaterialAsset;
  createFolder: typeof createMaterialFavoriteFolder;
  renameFolder: typeof renameMaterialFavoriteFolder;
  deleteFolder: typeof deleteMaterialFavoriteFolder;
  addAssets: typeof addMaterialFavoriteAssets;
  removeAsset: typeof removeMaterialFavoriteAsset;
  message: Pick<typeof messageApi, "success" | "warning" | "error">;
}

const defaultDependencies: MaterialFavoriteCommandDependencies = {
  requireAuthentication: requireAuth,
  fetchFolders: fetchMaterialFavoriteFolders,
  fetchAsset: fetchMaterialAsset,
  createFolder: createMaterialFavoriteFolder,
  renameFolder: renameMaterialFavoriteFolder,
  deleteFolder: deleteMaterialFavoriteFolder,
  addAssets: addMaterialFavoriteAssets,
  removeAsset: removeMaterialFavoriteAsset,
  message: messageApi,
};

export function useMaterialFavoriteCommands(
  options: MaterialFavoriteCommandOptions,
  overrides: Partial<MaterialFavoriteCommandDependencies> = {},
) {
  const dependencies = { ...defaultDependencies, ...overrides };

  async function loadFavoriteFolders() {
    const authenticated = await dependencies.requireAuthentication({
      title: "登录后查看收藏夹",
      message: "收藏夹保存在你的账号下，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      options.favoriteFolders.value = [];
      return;
    }
    try {
      const result = await dependencies.fetchFolders();
      options.favoriteFolders.value = result.folders ?? [];
    } catch (error) {
      options.favoriteFolders.value = [];
      dependencies.message.error(error instanceof Error ? error.message : "收藏夹加载失败");
    }
  }

  function cacheMaterialAssets(items: MaterialAssetLibraryItem[]) {
    if (!items.length) return;
    const next = { ...options.favoriteAssetCache.value };
    for (const item of items) next[item.id] = item;
    options.favoriteAssetCache.value = next;
  }

  function folderContainsAsset(folderId: string, assetId: string) {
    return Boolean(options.favoriteFolders.value.find((folder) => folder.id === folderId)?.assetIds.includes(assetId));
  }

  function isAssetFavorited(assetId: string) {
    return options.favoriteFolders.value.some((folder) => folder.assetIds.includes(assetId));
  }

  function openFavoriteDialog(asset?: MaterialAssetLibraryItem) {
    options.favoriteDialog.asset = asset ?? null;
    options.favoriteDialog.batchAssets = [];
    options.favoriteDialog.open = true;
    if (asset) cacheMaterialAssets([asset]);
  }

  function openBatchFavoriteDialog() {
    const selectedIds = new Set(options.selectedAssetIds.value);
    const selectedAssets = options.displayedAssets.value.filter((asset) => selectedIds.has(asset.id));
    if (!selectedAssets.length) {
      dependencies.message.warning("请先选择素材");
      return;
    }
    options.favoriteDialog.asset = null;
    options.favoriteDialog.batchAssets = selectedAssets;
    options.favoriteDialog.open = true;
    cacheMaterialAssets(selectedAssets);
  }

  function closeFavoriteDialog() {
    options.favoriteDialog.open = false;
    options.favoriteDialog.asset = null;
    options.favoriteDialog.batchAssets = [];
  }

  function upsertFolder(folder: MaterialFavoriteFolder) {
    const exists = options.favoriteFolders.value.some((item) => item.id === folder.id);
    options.favoriteFolders.value = exists
      ? options.favoriteFolders.value.map((item) => (item.id === folder.id ? folder : item))
      : [...options.favoriteFolders.value, folder];
  }

  function dialogAssetIds() {
    return options.favoriteDialog.asset
      ? [options.favoriteDialog.asset.id]
      : options.favoriteDialog.batchAssets.map((asset) => asset.id);
  }

  async function createFavoriteFolder(request: MaterialFavoriteCreateRequest) {
    const assetIds = dialogAssetIds();
    try {
      const folder = await dependencies.createFolder({ name: request.name, assetIds });
      upsertFolder(folder);
      cacheMaterialAssets(options.favoriteDialog.asset ? [options.favoriteDialog.asset] : options.favoriteDialog.batchAssets);
      options.activeFavoriteFolderId.value = folder.id;
      request.complete();
      dependencies.message.success(assetIds.length ? "已加入收藏夹" : "已创建收藏夹");
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "收藏夹创建失败");
    }
  }

  async function commitFavoriteFolderRename(request: MaterialFavoriteRenameRequest) {
    try {
      upsertFolder(await dependencies.renameFolder(request.folderId, { name: request.name }));
      request.complete();
      dependencies.message.success("已重命名收藏夹");
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "收藏夹重命名失败");
    }
  }

  async function confirmDeleteFavoriteFolder(folder: MaterialFavoriteFolder) {
    const confirmed = await options.requestConfirm({
      title: "删除收藏夹",
      message: `删除后会移除收藏夹「${folder.name}」，素材本身不会被删除。`,
      confirmText: "删除",
    });
    if (!confirmed) return;
    try {
      await dependencies.deleteFolder(folder.id);
      options.favoriteFolders.value = options.favoriteFolders.value.filter((item) => item.id !== folder.id);
      if (options.activeFavoriteFolderId.value === folder.id) options.activeFavoriteFolderId.value = "";
      dependencies.message.success("已删除收藏夹");
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "收藏夹删除失败");
    }
  }

  async function updateMembership(folderId: string, asset: MaterialAssetLibraryItem) {
    cacheMaterialAssets([asset]);
    const removing = folderContainsAsset(folderId, asset.id);
    try {
      const folder = removing
        ? await dependencies.removeAsset(folderId, asset.id)
        : await dependencies.addAssets(folderId, { assetIds: [asset.id] });
      upsertFolder(folder);
      dependencies.message.success(removing ? "已移出收藏夹" : "已加入收藏夹");
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "收藏夹更新失败");
    }
  }

  async function addBatchAssets(folderId: string) {
    const assetIds = options.favoriteDialog.batchAssets.map((asset) => asset.id);
    if (!assetIds.length) return;
    try {
      upsertFolder(await dependencies.addAssets(folderId, { assetIds }));
      cacheMaterialAssets(options.favoriteDialog.batchAssets);
      dependencies.message.success(`已加入 ${assetIds.length} 个素材`);
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "批量收藏失败");
    }
  }

  function isFavoriteDialogFolderActive(folderId: string) {
    if (options.favoriteDialog.asset) return folderContainsAsset(folderId, options.favoriteDialog.asset.id);
    const assetIds = options.favoriteDialog.batchAssets.map((asset) => asset.id);
    return assetIds.length > 0 && assetIds.every((assetId) => folderContainsAsset(folderId, assetId));
  }

  function handleFavoriteDialogFolderClick(folderId: string) {
    if (options.favoriteDialog.asset) void updateMembership(folderId, options.favoriteDialog.asset);
    else if (options.favoriteDialog.batchAssets.length) void addBatchAssets(folderId);
  }

  async function selectFavoriteFolder(folderId: string) {
    options.activeFavoriteFolderId.value = folderId;
    options.selectedAssetIds.value = [];
    options.batchMode.value = false;
    const folder = options.favoriteFolders.value.find((item) => item.id === folderId);
    if (!folder) return;
    const missingIds = folder.assetIds.filter(
      (assetId) => !options.assets.value.some((asset) => asset.id === assetId) && !options.favoriteAssetCache.value[assetId],
    );
    if (!missingIds.length) return;
    const loaded = await Promise.all(missingIds.map((assetId) => dependencies.fetchAsset(assetId).catch(() => null)));
    cacheMaterialAssets(loaded.filter((asset): asset is MaterialAssetLibraryItem => Boolean(asset)));
  }

  return {
    loadFavoriteFolders,
    cacheMaterialAssets,
    isAssetFavorited,
    openFavoriteDialog,
    openBatchFavoriteDialog,
    closeFavoriteDialog,
    createFavoriteFolder,
    commitFavoriteFolderRename,
    confirmDeleteFavoriteFolder,
    isFavoriteDialogFolderActive,
    handleFavoriteDialogFolderClick,
    selectFavoriteFolder,
  };
}

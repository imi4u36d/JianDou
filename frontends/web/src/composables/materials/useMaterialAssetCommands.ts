import { nextTick, reactive, ref, type Ref } from "vue";
import { useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import {
  deleteMaterialAsset,
  renameMaterialAsset,
  reuseMaterialAsset,
  uploadMaterialAsset,
} from "@/features/materials";
import {
  assetDownloadKind,
  assetPublicUrl,
} from "@/features/materials/material-library-presenters";
import type { MaterialAssetLibraryItem } from "@/types";
import { downloadMedia } from "@/utils/download";

interface MaterialAssetCommandOptions {
  assets: Ref<MaterialAssetLibraryItem[]>;
  busyActionKey: Ref<string>;
  selectedAssetIds: Ref<string[]>;
  previewAsset: Ref<MaterialAssetLibraryItem | null>;
  cacheMaterialAssets: (assets: MaterialAssetLibraryItem[]) => void;
  syncPreviewAsset: (asset: MaterialAssetLibraryItem) => void;
  loadAssets: () => Promise<void>;
  loadFavoriteFolders: () => Promise<void>;
  requestConfirm: (options: {
    title: string;
    message: string;
    confirmText?: string;
  }) => Promise<boolean>;
}

export function useMaterialAssetCommands(options: MaterialAssetCommandOptions) {
  const router = useRouter();
  const renameInputRef = ref<HTMLInputElement | null>(null);
  const renameDialog = reactive({
    open: false,
    asset: null as MaterialAssetLibraryItem | null,
    title: "",
  });

  function upsertMaterialAssetState(asset: MaterialAssetLibraryItem) {
    if (options.assets.value.some((item) => item.id === asset.id)) {
      options.assets.value = options.assets.value.map((item) =>
        item.id === asset.id ? asset : item,
      );
    }
    options.cacheMaterialAssets([asset]);
    if (options.previewAsset.value?.id === asset.id) options.syncPreviewAsset(asset);
  }

  async function openRenameDialog(asset: MaterialAssetLibraryItem) {
    Object.assign(renameDialog, { asset, title: asset.title, open: true });
    await nextTick();
    renameInputRef.value?.focus({ preventScroll: true });
    renameInputRef.value?.select();
  }

  function closeRenameDialog() {
    if (renameDialog.asset && options.busyActionKey.value === `rename-${renameDialog.asset.id}`) return;
    Object.assign(renameDialog, { open: false, asset: null, title: "" });
  }

  async function commitAssetRename() {
    const asset = renameDialog.asset;
    const title = renameDialog.title.trim();
    if (!asset || !title) return;
    if (title === asset.title) {
      closeRenameDialog();
      return;
    }
    if (!(await authenticate("登录后修改素材名称", "修改素材名称会更新你的素材库，请先登录或使用邀请码注册。", "登录后可继续修改素材名称。"))) return;
    options.busyActionKey.value = `rename-${asset.id}`;
    try {
      upsertMaterialAssetState(await renameMaterialAsset(asset.id, { title }));
      messageApi.success("已修改素材名称");
      Object.assign(renameDialog, { open: false, asset: null, title: "" });
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "素材名称修改失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleBatchDelete() {
    if (!options.selectedAssetIds.value.length) return;
    const confirmed = await options.requestConfirm({
      title: "删除素材",
      message: `删除后无法恢复，将移除选中的 ${options.selectedAssetIds.value.length} 个素材。`,
      confirmText: "删除",
    });
    if (!confirmed) return;
    if (!(await authenticate("登录后批量删除素材", "批量删除会修改你的素材库，请先登录或使用邀请码注册。", "登录后可继续批量删除。"))) return;
    const ids = [...options.selectedAssetIds.value];
    options.busyActionKey.value = "batch-delete";
    try {
      for (const assetId of ids) await deleteMaterialAsset(assetId);
      options.selectedAssetIds.value = [];
      await options.loadAssets();
      await options.loadFavoriteFolders();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "批量删除失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function refreshAfterMutation(mutator: () => Promise<unknown>, actionKey: string) {
    if (!(await authenticate("登录后操作素材", "素材操作会修改你的素材库，请先登录或使用邀请码注册。", "登录后可继续操作素材。"))) return;
    options.busyActionKey.value = actionKey;
    try {
      await mutator();
      await options.loadAssets();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "素材操作失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleUploadAsset(assetId: string) {
    await refreshAfterMutation(() => uploadMaterialAsset(assetId), `upload-${assetId}`);
  }

  async function handleDeleteAsset(asset: MaterialAssetLibraryItem) {
    const confirmed = await options.requestConfirm({
      title: "删除素材",
      message: `删除后无法恢复：${asset.title}`,
      confirmText: "删除",
    });
    if (!confirmed) return;
    await refreshAfterMutation(async () => {
      await deleteMaterialAsset(asset.id);
      await options.loadFavoriteFolders();
    }, `delete-${asset.id}`);
  }

  async function handleReuseAsset(assetId: string) {
    if (!(await authenticate("登录后复用素材", "复用素材会创建你的阶段工作流，请先登录或使用邀请码注册。", "登录后可继续复用素材。"))) return;
    options.busyActionKey.value = `reuse-${assetId}`;
    try {
      const workflow = await reuseMaterialAsset(assetId, { mode: "clone" });
      await options.loadAssets();
      await router.push(`/video-tasks/${workflow.id}`);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "素材操作失败");
    } finally {
      options.busyActionKey.value = "";
    }
  }

  async function handleDownloadAsset(asset: MaterialAssetLibraryItem) {
    try {
      const result = await downloadMedia({
        url: assetPublicUrl(asset),
        title: asset.title || asset.id,
        mediaType: assetDownloadKind(asset),
      });
      if (result.target === "album") messageApi.success("已保存到相册");
      else if (result.target === "share") messageApi.info("已打开系统分享，可保存到相册");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  return {
    closeRenameDialog,
    commitAssetRename,
    handleBatchDelete,
    handleDeleteAsset,
    handleDownloadAsset,
    handleReuseAsset,
    handleUploadAsset,
    openRenameDialog,
    renameDialog,
    renameInputRef,
    upsertMaterialAssetState,
  };
}

async function authenticate(title: string, message: string, warning: string): Promise<boolean> {
  const authenticated = await requireAuth({ title, message });
  if (!authenticated) messageApi.warning(warning);
  return authenticated;
}

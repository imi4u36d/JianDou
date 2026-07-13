import { reactive, ref } from "vue";
import { createPublicShare, deletePublicShare } from "@/api/public-shares";
import { isAssetShareable, materialShareSource } from "@/features/materials/material-library-presenters";
import { messageApi } from "@/composables/useMessage";
import type { MaterialAssetLibraryItem } from "@/types";

export interface MaterialSharingDependencies {
  createShare: typeof createPublicShare;
  deleteShare: typeof deletePublicShare;
  message: Pick<typeof messageApi, "success" | "error">;
}

const defaultDependencies: MaterialSharingDependencies = {
  createShare: createPublicShare,
  deleteShare: deletePublicShare,
  message: messageApi,
};

export function useMaterialSharing(overrides: Partial<MaterialSharingDependencies> = {}) {
  const dependencies = { ...defaultDependencies, ...overrides };
  const sharingAssetId = ref("");
  const pendingShareAsset = ref<MaterialAssetLibraryItem | null>(null);
  const sharedAssetRecords = ref<Record<string, string>>({});
  const shareConfirmDialog = reactive({
    open: false,
    title: "分享素材",
    message: "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
    confirmText: "确认分享",
    cancelText: "取消",
    tone: "primary" as "primary" | "danger",
  });

  function openMaterialShareConfirm(asset: MaterialAssetLibraryItem) {
    if (!isAssetShareable(asset)) return;
    const shared = Boolean(sharedAssetRecords.value[asset.id]);
    pendingShareAsset.value = asset;
    shareConfirmDialog.title = shared ? "取消分享" : "分享素材";
    shareConfirmDialog.message = shared
      ? "取消分享后，这个素材将不再展示在首页分享区。"
      : "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。";
    shareConfirmDialog.confirmText = shared ? "取消分享" : "确认分享";
    shareConfirmDialog.tone = shared ? "danger" : "primary";
    shareConfirmDialog.open = true;
  }

  function cancelMaterialShareConfirm() {
    shareConfirmDialog.open = false;
    pendingShareAsset.value = null;
  }

  async function acceptMaterialShareConfirm() {
    const asset = pendingShareAsset.value;
    if (!asset || sharingAssetId.value) return;
    sharingAssetId.value = asset.id;
    try {
      const existingShareId = sharedAssetRecords.value[asset.id];
      if (existingShareId) {
        await dependencies.deleteShare(existingShareId);
        const next = { ...sharedAssetRecords.value };
        delete next[asset.id];
        sharedAssetRecords.value = next;
        dependencies.message.success("已取消分享");
      } else {
        const source = materialShareSource(asset);
        const share = await dependencies.createShare({
          materialAssetId: asset.id,
          sourceType: source.sourceType,
          sourceId: source.sourceId,
        });
        sharedAssetRecords.value = { ...sharedAssetRecords.value, [asset.id]: share.shareId };
        dependencies.message.success("已分享到首页");
      }
    } catch (error) {
      dependencies.message.error(error instanceof Error ? error.message : "分享失败");
    } finally {
      sharingAssetId.value = "";
      cancelMaterialShareConfirm();
    }
  }

  return {
    sharingAssetId,
    sharedAssetRecords,
    shareConfirmDialog,
    openMaterialShareConfirm,
    cancelMaterialShareConfirm,
    acceptMaterialShareConfirm,
  };
}

import { reactive } from "vue";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import { fetchMaterialAssets } from "@/features/workflows";
import type { MaterialAssetLibraryItem, WorkflowCharacterSheet } from "@/types";
import { characterSheetKey, characterSheetTitle } from "./useCharacterSheetUtils";

export function materialAssetPreviewUrl(asset: MaterialAssetLibraryItem): string {
  return asset.thumbnailUrl || asset.previewUrl || asset.publicUrl || asset.fileUrl || "";
}

export function materialAssetModelLabel(asset: MaterialAssetLibraryItem): string {
  return asset.originModel || asset.originProvider || "未记录模型";
}

export function useCharacterAssetPicker() {
  const characterAssetPicker = reactive({
    openKey: "",
    keyword: "",
    model: "",
    loading: false,
    error: "",
    assets: [] as MaterialAssetLibraryItem[],
  });

  function isCharacterSheetSelectableAsset(asset: MaterialAssetLibraryItem, sheet?: WorkflowCharacterSheet): boolean {
    const assetType = typeof asset.assetType === "string" ? asset.assetType.trim().toLowerCase() : "";
    const expectedType = !sheet || !sheet.assetType || sheet.assetType === "character" ? "character_sheet" : sheet.assetType;
    const isSupportedAssetType = assetType === expectedType || assetType === "free";
    const hasPreview = Boolean(asset.publicUrl || asset.fileUrl);
    return isSupportedAssetType && hasPreview;
  }

  function isCharacterAssetPickerOpen(sheet: WorkflowCharacterSheet): boolean {
    return characterAssetPicker.openKey === characterSheetKey(sheet);
  }

  async function openCharacterAssetPicker(sheet: WorkflowCharacterSheet) {
    const authenticated = await requireAuth({
      title: "登录后选择素材",
      message: "素材库只展示你的个人素材，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      messageApi.warning("登录后可继续选择素材。");
      return;
    }
    characterAssetPicker.openKey = characterSheetKey(sheet);
    characterAssetPicker.keyword = characterSheetTitle(sheet);
    characterAssetPicker.model = "";
    await loadCharacterAssetCandidates(sheet);
  }

  function closeCharacterAssetPicker() {
    characterAssetPicker.openKey = "";
    characterAssetPicker.error = "";
    characterAssetPicker.assets = [];
  }

  async function loadCharacterAssetCandidates(sheet: WorkflowCharacterSheet) {
    const authenticated = await requireAuth({
      title: "登录后搜索素材",
      message: "素材库只展示你的个人素材，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      characterAssetPicker.error = "登录后可搜索素材库。";
      return;
    }
    const expectedKey = characterSheetKey(sheet);
    characterAssetPicker.openKey = expectedKey;
    characterAssetPicker.loading = true;
    characterAssetPicker.error = "";
    try {
      const assets = await fetchMaterialAssets({
        q: characterAssetPicker.keyword.trim() || characterSheetTitle(sheet),
        model: characterAssetPicker.model.trim() || undefined,
      });
      if (characterAssetPicker.openKey !== expectedKey) return;
      characterAssetPicker.assets = assets.filter((asset) => isCharacterSheetSelectableAsset(asset, sheet));
    } catch (error) {
      characterAssetPicker.error = error instanceof Error ? error.message : "公共素材加载失败";
      characterAssetPicker.assets = [];
    } finally {
      if (characterAssetPicker.openKey === expectedKey) {
        characterAssetPicker.loading = false;
      }
    }
  }

  return {
    characterAssetPicker,
    materialAssetPreviewUrl,
    materialAssetModelLabel,
    isCharacterSheetSelectableAsset,
    isCharacterAssetPickerOpen,
    openCharacterAssetPicker,
    closeCharacterAssetPicker,
    loadCharacterAssetCandidates,
  };
}

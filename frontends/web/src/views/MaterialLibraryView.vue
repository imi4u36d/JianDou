<template>
  <section class="material-view">
    <header class="material-topbar">
      <nav class="material-tabs" aria-label="素材分类">
        <button
          v-for="tab in libraryTabs"
          :key="tab.key"
          type="button"
          class="material-tab"
          :class="{ 'material-tab-active': activeLibraryTab === tab.key }"
          @click="selectLibraryTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div class="material-topbar__tools liquid-glass">
        <label class="material-search">
          <span class="material-search__icon" aria-hidden="true"><IconSearch size="sm" /></span>
          <input v-model="filters.q" type="search" placeholder="搜索素材" @keyup.enter="loadAssets" />
          <button
            v-if="filters.q"
            class="material-search__clear"
            type="button"
            aria-label="清除搜索"
            @click="filters.q = ''; loadAssets()"
          >
            <IconClose size="xs" />
          </button>
        </label>
        <label class="material-workflow-toggle" :class="{ 'material-workflow-toggle-active': filters.showWorkflowArtifacts }">
          <input v-model="filters.showWorkflowArtifacts" type="checkbox" @change="loadAssets" />
          <span class="material-workflow-toggle__track" aria-hidden="true"></span>
          <span class="material-workflow-toggle__text">工作流产物</span>
        </label>
        <span class="material-toolbar-divider"></span>
        <button
          class="material-toolbar-link"
          type="button"
          :class="{ 'material-toolbar-link-active': advancedFiltersOpen || activeFilterCount > 0 }"
          aria-label="筛选素材"
          title="筛选"
          @click="advancedFiltersOpen = !advancedFiltersOpen"
        >
          <IconSettings size="sm" />
          <span v-if="activeFilterCount > 0" class="material-toolbar-badge">{{ activeFilterCount }}</span>
        </button>
        <RouterLink class="material-toolbar-primary" to="/image-tasks">
          <IconPlus size="sm" />
          新建
        </RouterLink>
      </div>
    </header>

    <section class="material-favorite-folders" aria-label="收藏夹">
      <div class="material-favorite-folders__head">
        <button class="jd-button jd-button--primary jd-button--xs material-favorite-folders__add" type="button" @click="openFavoriteDialog()">
          <IconPlus size="xs" />
          新建收藏夹
        </button>
      </div>
      <div class="material-favorite-folders__list">
        <button
          v-for="folder in favoriteFolders"
          :key="folder.id"
          type="button"
          class="material-favorite-folder"
          :class="{ 'material-favorite-folder-active': activeFavoriteFolderId === folder.id }"
          @click="selectFavoriteFolder(folder.id)"
        >
          <IconHeart size="xs" :filled="activeFavoriteFolderId === folder.id" />
          <span>{{ folder.name }}</span>
          <small>{{ folder.assetIds.length }}</small>
        </button>
      </div>
      <div class="material-favorite-folders__actions">
        <button
          class="jd-button jd-button--ghost jd-button--xs material-favorite-folders__batch"
          type="button"
          :class="{ 'material-favorite-folders__batch-active': batchMode }"
          :disabled="!canUseBatchMode"
          @click="toggleBatchMode"
        >
          <IconCheck size="xs" />
          批量操作
        </button>
        <template v-if="batchMode">
          <button class="jd-button jd-button--secondary jd-button--xs" type="button" :disabled="!selectedAssetIds.length" @click="openBatchFavoriteDialog">
            <IconHeart size="xs" />
            添加到收藏
          </button>
          <button class="jd-button jd-button--danger jd-button--xs" type="button" :disabled="!selectedAssetIds.length || Boolean(busyActionKey)" @click="handleBatchDelete">
            <IconLoading v-if="busyActionKey === 'batch-delete'" size="xs" />
            <IconDelete v-else size="xs" />
            删除
          </button>
          <small class="material-favorite-folders__selected">已选 {{ selectedAssetIds.length }}</small>
        </template>
      </div>
    </section>

    <section v-if="advancedFiltersOpen" class="material-filter-drawer">
      <label class="material-field">
        <span>素材类型</span>
        <AppSelect v-model="filters.assetType" :options="typeFilterOptions" />
      </label>
      <label class="material-field">
        <span>模型</span>
        <input v-model="filters.model" class="field-input" placeholder="模型" @keyup.enter="loadAssets" />
      </label>
      <label class="material-field">
        <span>画幅</span>
        <AppSelect v-model="filters.aspectRatio" :options="aspectRatioFilterOptions" />
      </label>
      <label class="material-field">
        <span>镜头号</span>
        <input v-model="filters.clipIndex" class="field-input" type="number" min="0" step="1" placeholder="全部" @keyup.enter="loadAssets" />
      </label>
      <div class="material-filter-drawer__actions">
        <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="loading" @click="loadAssets">应用</button>
        <button class="jd-button jd-button--ghost jd-button--sm" type="button" :disabled="loading" @click="resetFilters">清空</button>
      </div>
    </section>

    <section v-if="loading && !assets.length" class="material-empty">
      <IconLoading size="lg" />
    </section>

    <section v-else class="material-asset-grid">
      <article
        v-for="asset in displayedAssets"
        :key="asset.id"
        class="material-card"
        :class="{ 'material-card-selected': isAssetChecked(asset.id), 'material-card-batchable': batchMode }"
        :aria-selected="batchMode ? isAssetChecked(asset.id) : undefined"
        @click="handleMaterialCardClick(asset)"
      >
        <label v-if="batchMode" class="material-card__check" @click.stop>
          <input type="checkbox" :checked="isAssetChecked(asset.id)" @change="toggleAssetSelection(asset.id)" />
          <span></span>
        </label>

        <div class="material-card__preview">
          <button
            v-if="asset.mediaType === 'video' && assetVideoPosterUrl(asset)"
            class="material-preview-trigger material-preview-trigger-video"
            type="button"
            @click.stop="handleAssetPreviewClick(asset, openVideoPreview)"
          >
            <img
              v-if="!isAssetPreviewImageFailed(assetVideoPosterUrl(asset))"
              :src="assetVideoPosterUrl(asset)"
              :alt="asset.title"
              loading="lazy"
              decoding="async"
              fetchpriority="low"
              @error="markAssetPreviewImageFailed(assetVideoPosterUrl(asset))"
            />
            <span v-else class="material-preview-fallback"><IconImage size="sm" /></span>
            <span class="material-video-play" aria-hidden="true"><IconVideo size="xs" /></span>
          </button>
          <button
            v-else-if="asset.mediaType === 'video'"
            class="material-preview-trigger material-preview-trigger-placeholder"
            type="button"
            @click.stop="handleAssetPreviewClick(asset, openVideoPreview)"
          >
            <span><IconVideo size="sm" /></span>
          </button>
          <button
            v-else-if="asset.mediaType === 'image' && assetListImageUrl(asset)"
            class="material-preview-trigger material-preview-trigger-image"
            type="button"
            @click.stop="handleAssetPreviewClick(asset, openImagePreview)"
          >
            <img
              v-if="!isAssetPreviewImageFailed(assetListImageUrl(asset))"
              :src="assetListImageUrl(asset)"
              :alt="asset.title"
              loading="lazy"
              decoding="async"
              fetchpriority="low"
              @error="markAssetPreviewImageFailed(assetListImageUrl(asset))"
            />
            <span v-else class="material-preview-fallback"><IconImage size="sm" /></span>
          </button>
          <button
            v-else-if="asset.mediaType === 'image'"
            class="material-preview-trigger material-preview-trigger-placeholder"
            type="button"
            @click.stop="handleAssetPreviewClick(asset, openImagePreview)"
          >
            <span><IconImage size="sm" /></span>
          </button>
          <button
            v-else
            class="material-preview-trigger material-preview-trigger-text"
            type="button"
            @click.stop="handleAssetPreviewClick(asset, openStoryboardPreview)"
          >
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="material-card__text" v-html="storyboardPreviewHtml(asset)"></div>
          </button>
        </div>

        <button
          type="button"
          class="material-card__favorite"
          :class="{ 'material-card__favorite-active': isAssetFavorited(asset.id) }"
          :aria-label="isAssetFavorited(asset.id) ? '已收藏，管理收藏夹' : '收藏素材'"
          :title="isAssetFavorited(asset.id) ? '已收藏' : '收藏'"
          @click.stop="batchMode ? toggleAssetSelection(asset.id) : openFavoriteDialog(asset)"
        >
          <IconHeart size="sm" :filled="isAssetFavorited(asset.id)" />
        </button>

        <div class="material-card__body">
          <div class="material-card__head">
            <div class="material-card__title">
              <strong>{{ asset.title }}</strong>
              <span>{{ assetSubtitle(asset) }}</span>
            </div>
            <div class="material-more-menu">
              <button
                type="button"
                class="material-more-menu__trigger"
                aria-label="更多操作"
                :popovertarget="`material-menu-${asset.id}`"
                @click.stop
              >
                <IconMore size="sm" />
              </button>
              <div :id="`material-menu-${asset.id}`" popover class="material-more-menu__panel" @beforetoggle="positionMaterialMenu">
                <button type="button" :disabled="busyActionKey === `upload-${asset.id}` || Boolean(asset.remoteUrl)" @click="handleUploadAsset(asset.id)">
                  <IconLoading v-if="busyActionKey === `upload-${asset.id}`" size="xs" />
                  <IconUpload v-else size="xs" />
                  <span>{{ busyActionKey === `upload-${asset.id}` ? "上传中" : (asset.remoteUrl ? "已上传" : "上传") }}</span>
                </button>
                <button type="button" :disabled="busyActionKey === `reuse-${asset.id}`" @click="handleReuseAsset(asset.id)">
                  <IconLoading v-if="busyActionKey === `reuse-${asset.id}`" size="xs" />
                  <IconPlus v-else size="xs" />
                  <span>{{ busyActionKey === `reuse-${asset.id}` ? "复用中" : "复用" }}</span>
                </button>
                <button type="button" :disabled="busyActionKey === `rename-${asset.id}`" @click="openRenameDialog(asset)">
                  <IconEdit size="xs" />
                  <span>修改名称</span>
                </button>
                <RouterLink v-if="asset.workflowId" :to="`/video-tasks/${asset.workflowId}`">
                  <IconWorkflow size="xs" />
                  <span>视频</span>
                </RouterLink>
                <button type="button" @click="handleDownloadAsset(asset)">
                  <IconDownload size="xs" />
                  <span>下载</span>
                </button>
                <button v-if="isAssetShareable(asset)" type="button" :disabled="sharingAssetId === asset.id" @click="openMaterialShareConfirm(asset)">
                  <IconShare size="xs" />
                  <span>{{ sharedAssetRecords[asset.id] ? "已分享" : "分享" }}</span>
                </button>
                <button type="button" class="material-menu-danger" :disabled="busyActionKey === `delete-${asset.id}`" @click="handleDeleteAsset(asset)">
                  <IconLoading v-if="busyActionKey === `delete-${asset.id}`" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === `delete-${asset.id}` ? "删除中" : "删除" }}</span>
                </button>
              </div>
            </div>
          </div>
          <div class="material-card__chips">
            <span>{{ assetDisplayTypeLabel(asset) }}</span>
            <button v-if="asset.remoteUrl" type="button" :title="`复制远程地址：${asset.remoteUrl}`" aria-label="复制远程地址" @click.stop="copyRemoteUrl(asset.remoteUrl)">
              <IconUpload size="xs" />
            </button>
            <span v-else>本地</span>
          </div>
        </div>
      </article>

      <div v-if="!displayedAssets.length && (activeFavoriteFolderId || !hasMoreAssets)" class="material-empty material-empty-inline">
        <strong>{{ materialEmptyTitle }}</strong>
      </div>

      <div v-else-if="!activeFavoriteFolderId && (displayedAssets.length || hasMoreAssets)" ref="loadMoreTrigger" class="material-load-more">
        <IconLoading v-if="loadingMore" size="sm" />
        <span v-else-if="hasMoreAssets" aria-hidden="true"></span>
      </div>
    </section>

    <AppPreviewDialog
      :open="previewDialog.open"
      :kind="previewDialog.kind"
      :title="previewDialog.title"
      :html="previewDialog.html"
      :url="previewDialog.url"
      :image-load-failed="previewImageLoadFailed"
      show-navigation
      :can-previous="canPreviewPrevious"
      :can-next="canPreviewNext"
      @close="closePreviewDialog"
      @image-error="previewImageLoadFailed = true"
      @previous="navigatePreview(-1)"
      @next="navigatePreview(1)"
    >
      <template v-if="previewAsset" #actions>
        <button
          type="button"
          class="jd-button jd-button--sm material-preview-favorite-action"
          :class="{ 'material-preview-favorite-action-active': isAssetFavorited(previewAsset.id) }"
          :aria-label="isAssetFavorited(previewAsset.id) ? '已收藏，管理收藏夹' : '收藏预览素材'"
          @click="openFavoriteDialog(previewAsset)"
        >
          <IconHeart size="xs" :filled="isAssetFavorited(previewAsset.id)" />
          <span>{{ isAssetFavorited(previewAsset.id) ? "已收藏" : "收藏" }}</span>
        </button>
        <button
          v-if="isAssetShareable(previewAsset)"
          type="button"
          class="jd-button jd-button--sm"
          :disabled="sharingAssetId === previewAsset.id"
          aria-label="分享预览素材"
          @click="openMaterialShareConfirm(previewAsset)"
        >
          <IconShare size="xs" />
          <span>{{ sharedAssetRecords[previewAsset.id] ? "已分享" : "分享" }}</span>
        </button>
      </template>
    </AppPreviewDialog>

    <Teleport to="body">
      <Transition name="material-favorite-dialog-fade">
        <div
          v-if="favoriteDialog.open"
          class="material-favorite-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="material-favorite-dialog-title"
          @click.self="closeFavoriteDialog"
          @keydown.esc.stop.prevent="closeFavoriteDialog"
        >
          <div class="material-favorite-dialog__panel">
            <div class="material-favorite-dialog__head">
              <div>
                <h3 id="material-favorite-dialog-title">{{ favoriteDialog.batchAssets.length ? "批量添加到收藏夹" : (favoriteDialog.asset ? "添加到收藏夹" : "管理收藏夹") }}</h3>
                <p v-if="favoriteDialog.asset">{{ favoriteDialog.asset.title }}</p>
                <p v-else-if="favoriteDialog.batchAssets.length">已选择 {{ favoriteDialog.batchAssets.length }} 个素材</p>
              </div>
              <button type="button" aria-label="关闭收藏夹弹窗" @click="closeFavoriteDialog">
                <IconClose size="sm" />
              </button>
            </div>

            <div class="material-favorite-dialog__folders">
              <div
                v-for="folder in favoriteFolders"
                :key="folder.id"
                class="material-favorite-dialog__folder"
                :class="{ 'material-favorite-dialog__folder-active': isFavoriteDialogFolderActive(folder.id) }"
              >
                <form
                  v-if="favoriteDialog.editingFolderId === folder.id"
                  class="material-favorite-dialog__rename"
                  @submit.prevent="commitFavoriteFolderRename(folder.id)"
                >
                  <input
                    v-model="favoriteDialog.editingFolderName"
                    type="text"
                    maxlength="28"
                    aria-label="收藏夹名称"
                    @keydown.stop
                  />
                  <button type="submit" :disabled="!favoriteDialog.editingFolderName.trim()">保存</button>
                  <button type="button" @click="cancelFavoriteFolderRename">取消</button>
                </form>
                <template v-else>
                  <button
                    type="button"
                    class="material-favorite-dialog__folder-main"
                    :disabled="!favoriteDialog.asset && !favoriteDialog.batchAssets.length"
                    @click="handleFavoriteDialogFolderClick(folder.id)"
                  >
                    <IconHeart size="sm" :filled="isFavoriteDialogFolderActive(folder.id)" />
                    <span>{{ folder.name }}</span>
                    <small>{{ folder.assetIds.length }}</small>
                  </button>
                  <div v-if="!favoriteDialog.asset && !favoriteDialog.batchAssets.length" class="material-favorite-dialog__folder-actions">
                    <button type="button" @click="beginFavoriteFolderRename(folder)">
                      <IconEdit size="xs" />
                      修改
                    </button>
                    <button type="button" class="material-favorite-dialog__folder-delete" @click="confirmDeleteFavoriteFolder(folder)">
                      <IconDelete size="xs" />
                      删除
                    </button>
                  </div>
                </template>
              </div>
              <span v-if="!favoriteFolders.length" class="material-favorite-dialog__empty">还没有收藏夹</span>
            </div>

            <form class="material-favorite-dialog__create" @submit.prevent="createFavoriteFolder">
              <input v-model="favoriteDialog.newFolderName" type="text" maxlength="28" placeholder="输入收藏夹名称" />
              <button type="submit" :disabled="!favoriteDialog.newFolderName.trim()">
                <IconPlus size="xs" />
                添加
              </button>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="material-favorite-dialog-fade">
        <div
          v-if="renameDialog.open"
          class="material-rename-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="material-rename-dialog-title"
          @click.self="closeRenameDialog"
          @keydown.esc.stop.prevent="closeRenameDialog"
        >
          <form class="material-rename-dialog__panel" @submit.prevent="commitAssetRename">
            <div class="material-rename-dialog__head">
              <div>
                <h3 id="material-rename-dialog-title">修改素材名称</h3>
                <p>{{ renameDialog.asset?.title }}</p>
              </div>
              <button type="button" aria-label="关闭修改名称弹窗" @click="closeRenameDialog">
                <IconClose size="sm" />
              </button>
            </div>
            <label class="material-rename-dialog__field">
              <span>名称</span>
              <input
                ref="renameInputRef"
                v-model="renameDialog.title"
                type="text"
                maxlength="80"
                placeholder="输入素材名称"
                @keydown.stop
              />
            </label>
            <div class="material-rename-dialog__actions">
              <button type="button" class="jd-button jd-button--ghost jd-button--sm" :disabled="Boolean(busyActionKey)" @click="closeRenameDialog">取消</button>
              <button type="submit" class="jd-button jd-button--primary jd-button--sm" :disabled="!renameDialog.title.trim() || Boolean(busyActionKey)">
                <IconLoading v-if="busyActionKey === `rename-${renameDialog.asset?.id}`" size="xs" />
                保存
              </button>
            </div>
          </form>
        </div>
      </Transition>
    </Teleport>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
    <AppConfirmDialog v-bind="shareConfirmDialog" @confirm="acceptMaterialShareConfirm" @cancel="cancelMaterialShareConfirm" />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteMaterialAsset, fetchMaterialAssetPage, renameMaterialAsset, reuseMaterialAsset, uploadMaterialAsset } from "@/features/materials";
import {
  addMaterialFavoriteAssets,
  createMaterialFavoriteFolder,
  deleteMaterialFavoriteFolder,
  fetchMaterialAsset,
  fetchMaterialFavoriteFolders,
  removeMaterialFavoriteAsset,
  renameMaterialFavoriteFolder,
} from "@/api/material-assets";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { createPublicShare, deletePublicShare } from "@/api/public-shares";
import AppSelect from "@/components/common/AppSelect.vue";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import type { MaterialAssetLibraryItem, MaterialAssetQuery, MaterialAssetType, MaterialFavoriteFolder } from "@/types";
import { renderMarkdownToHtml } from "@/utils/markdown";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, inferMediaDownloadKind, type DownloadMediaKind } from "@/utils/download";
import { IconCheck, IconClose, IconDelete, IconDownload, IconEdit, IconHeart, IconImage, IconLoading, IconMore, IconPlus, IconSearch, IconSettings, IconShare, IconUpload, IconVideo, IconWorkflow } from "@/components/icons";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const loadingMore = ref(false);
const busyActionKey = ref("");
const activeLibraryTab = ref("all");
const advancedFiltersOpen = ref(false);
const batchMode = ref(false);
const selectedAssetIds = ref<string[]>([]);
const failedAssetPreviewUrls = ref(new Set<string>());
const sharingAssetId = ref("");
const pendingShareAsset = ref<MaterialAssetLibraryItem | null>(null);
const previewAsset = ref<MaterialAssetLibraryItem | null>(null);
const sharedAssetRecords = ref<Record<string, string>>({});
const favoriteFolders = ref<MaterialFavoriteFolder[]>([]);
const activeFavoriteFolderId = ref("");
const favoriteAssetCache = ref<Record<string, MaterialAssetLibraryItem>>({});
const favoriteDialog = reactive({
  open: false,
  asset: null as MaterialAssetLibraryItem | null,
  batchAssets: [] as MaterialAssetLibraryItem[],
  newFolderName: "",
  editingFolderId: "",
  editingFolderName: "",
});
const renameDialog = reactive({
  open: false,
  asset: null as MaterialAssetLibraryItem | null,
  title: "",
});

const assets = ref<MaterialAssetLibraryItem[]>([]);
const loadMoreTrigger = ref<HTMLElement | null>(null);
const renameInputRef = ref<HTMLInputElement | null>(null);
const assetPageLimit = 30;
const nextAssetOffset = ref(0);
const hasMoreAssets = ref(false);
let loadMoreObserver: IntersectionObserver | null = null;
let assetLoadRequestId = 0;
const libraryTabs = [
  { key: "all", label: "全部", assetType: "" },
  { key: "image", label: "图片", assetType: "" },
  { key: "video", label: "视频", assetType: "" },
  { key: "character_sheet", label: "角色三视图", assetType: "character_sheet" },
  { key: "scene", label: "场景", assetType: "scene" },
  { key: "prop", label: "道具", assetType: "prop" },
  { key: "workflow", label: "工作流产物", assetType: "workflow" },
];

function isAssetPreviewImageFailed(url?: string | null) {
  return Boolean(url && failedAssetPreviewUrls.value.has(url));
}

function markAssetPreviewImageFailed(url?: string | null) {
  if (!url) return;
  const next = new Set(failedAssetPreviewUrls.value);
  next.add(url);
  failedAssetPreviewUrls.value = next;
}
const typeFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "角色三视图", value: "character_sheet" },
  { label: "场景", value: "scene" },
  { label: "道具", value: "prop" },
  { label: "自由模式", value: "free" },
  { label: "工作流产物", value: "workflow" },
];
const aspectRatioFilterOptions: AppSelectOption[] = [
  { label: "全部", value: "" },
  { label: "16:9", value: "16:9" },
  { label: "9:16", value: "9:16" },
];

const filters = reactive({
  q: "",
  assetType: "",
  showWorkflowArtifacts: false,
  model: "",
  aspectRatio: "",
  clipIndex: "",
});
const previewDialog = reactive({
  open: false,
  kind: "storyboard" as "storyboard" | "image" | "video",
  title: "",
  html: "",
  url: "",
});
const previewImageLoadFailed = ref(false);
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const shareConfirmDialog = reactive({
  open: false,
  title: "分享素材",
  message: "确认分享后，你的生成结果会展示在首页，供其他用户浏览、点赞，帮助你成为人气用户。",
  confirmText: "确认分享",
  cancelText: "取消",
  tone: "primary" as "primary" | "danger",
});

const displayedAssets = computed(() => {
  if (activeFavoriteFolderId.value) {
    const folder = favoriteFolders.value.find((item) => item.id === activeFavoriteFolderId.value);
    if (!folder) return [];
    return folder.assetIds
      .map((assetId) => assets.value.find((asset) => asset.id === assetId) ?? favoriteAssetCache.value[assetId])
      .filter((asset): asset is MaterialAssetLibraryItem => Boolean(asset));
  }
  const tab = activeLibraryTab.value;
  if (tab === "image") {
    return assets.value.filter((asset) => asset.mediaType === "image");
  }
  if (tab === "video") {
    return assets.value.filter((asset) => asset.mediaType === "video");
  }
  if (tab === "all") {
    return assets.value;
  }
  if (tab === "workflow") {
    return assets.value.filter(isWorkflowArtifactAsset);
  }
  return assets.value.filter((asset) => asset.assetType === tab);
});

const canUseBatchMode = computed(() => displayedAssets.value.length > 0);
const previewAssetIndex = computed(() => {
  const asset = previewAsset.value;
  if (!asset) return -1;
  return displayedAssets.value.findIndex((item) => item.id === asset.id);
});
const canPreviewPrevious = computed(() => previewAssetIndex.value > 0);
const canPreviewNext = computed(() => {
  const index = previewAssetIndex.value;
  return index >= 0 && (index < displayedAssets.value.length - 1 || (!activeFavoriteFolderId.value && hasMoreAssets.value));
});
const activeFilterCount = computed(() => {
  return [filters.assetType, filters.showWorkflowArtifacts, filters.model.trim(), filters.aspectRatio, filters.clipIndex].filter(Boolean).length;
});
const materialEmptyTitle = computed(() => {
  if (activeFavoriteFolderId.value) {
    return "收藏夹暂无素材";
  }
  return filters.q.trim() || activeFilterCount.value > 0 || activeLibraryTab.value !== "all" ? "没有匹配素材" : "暂无素材";
});

function selectLibraryTab(tabKey: string) {
  activeFavoriteFolderId.value = "";
  activeLibraryTab.value = tabKey;
}

async function loadFavoriteFolders() {
  const authenticated = await requireAuth({
    title: "登录后查看收藏夹",
    message: "收藏夹保存在你的账号下，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    favoriteFolders.value = [];
    return;
  }
  try {
    const result = await fetchMaterialFavoriteFolders();
    favoriteFolders.value = result.folders ?? [];
  } catch (error) {
    favoriteFolders.value = [];
    messageApi.error(error instanceof Error ? error.message : "收藏夹加载失败");
  }
}

function cacheMaterialAssets(items: MaterialAssetLibraryItem[]) {
  if (!items.length) return;
  const next = { ...favoriteAssetCache.value };
  for (const item of items) {
    next[item.id] = item;
  }
  favoriteAssetCache.value = next;
}

function upsertMaterialAssetState(asset: MaterialAssetLibraryItem) {
  const exists = assets.value.some((item) => item.id === asset.id);
  if (exists) {
    assets.value = assets.value.map((item) => item.id === asset.id ? asset : item);
  }
  cacheMaterialAssets([asset]);
  if (previewAsset.value?.id === asset.id) {
    previewAsset.value = asset;
    previewDialog.title = asset.title;
  }
}

function isAssetFavorited(assetId: string) {
  return favoriteFolders.value.some((folder) => folder.assetIds.includes(assetId));
}

async function openRenameDialog(asset: MaterialAssetLibraryItem) {
  renameDialog.asset = asset;
  renameDialog.title = asset.title;
  renameDialog.open = true;
  await nextTick();
  renameInputRef.value?.focus({ preventScroll: true });
  renameInputRef.value?.select();
}

function closeRenameDialog() {
  if (renameDialog.asset && busyActionKey.value === `rename-${renameDialog.asset.id}`) {
    return;
  }
  renameDialog.open = false;
  renameDialog.asset = null;
  renameDialog.title = "";
}

async function commitAssetRename() {
  const asset = renameDialog.asset;
  const title = renameDialog.title.trim();
  if (!asset || !title) {
    return;
  }
  if (title === asset.title) {
    closeRenameDialog();
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后修改素材名称",
    message: "修改素材名称会更新你的素材库，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续修改素材名称。");
    return;
  }
  busyActionKey.value = `rename-${asset.id}`;
  try {
    const updated = await renameMaterialAsset(asset.id, { title });
    upsertMaterialAssetState(updated);
    messageApi.success("已修改素材名称");
    renameDialog.open = false;
    renameDialog.asset = null;
    renameDialog.title = "";
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "素材名称修改失败");
  } finally {
    busyActionKey.value = "";
  }
}

function folderContainsAsset(folderId: string, assetId: string) {
  return Boolean(favoriteFolders.value.find((folder) => folder.id === folderId)?.assetIds.includes(assetId));
}

function openFavoriteDialog(asset?: MaterialAssetLibraryItem) {
  favoriteDialog.asset = asset ?? null;
  favoriteDialog.batchAssets = [];
  favoriteDialog.newFolderName = "";
  favoriteDialog.editingFolderId = "";
  favoriteDialog.editingFolderName = "";
  favoriteDialog.open = true;
  if (asset) {
    cacheMaterialAssets([asset]);
  }
}

function openBatchFavoriteDialog() {
  const selectedIds = new Set(selectedAssetIds.value);
  const selectedAssets = displayedAssets.value.filter((asset) => selectedIds.has(asset.id));
  if (!selectedAssets.length) {
    messageApi.warning("请先选择素材");
    return;
  }
  favoriteDialog.asset = null;
  favoriteDialog.batchAssets = selectedAssets;
  favoriteDialog.newFolderName = "";
  favoriteDialog.editingFolderId = "";
  favoriteDialog.editingFolderName = "";
  favoriteDialog.open = true;
  cacheMaterialAssets(selectedAssets);
}

function closeFavoriteDialog() {
  favoriteDialog.open = false;
  favoriteDialog.asset = null;
  favoriteDialog.batchAssets = [];
  favoriteDialog.newFolderName = "";
  favoriteDialog.editingFolderId = "";
  favoriteDialog.editingFolderName = "";
}

function upsertFavoriteFolderState(folder: MaterialFavoriteFolder) {
  const exists = favoriteFolders.value.some((item) => item.id === folder.id);
  favoriteFolders.value = exists
    ? favoriteFolders.value.map((item) => item.id === folder.id ? folder : item)
    : [...favoriteFolders.value, folder];
}

function favoriteDialogAssetIds() {
  if (favoriteDialog.asset) {
    return [favoriteDialog.asset.id];
  }
  return favoriteDialog.batchAssets.map((asset) => asset.id);
}

async function createFavoriteFolder() {
  const name = favoriteDialog.newFolderName.trim();
  if (!name) return;
  const assetIds = favoriteDialogAssetIds();
  try {
    const folder = await createMaterialFavoriteFolder({ name, assetIds });
    upsertFavoriteFolderState(folder);
    if (favoriteDialog.asset) {
      cacheMaterialAssets([favoriteDialog.asset]);
    } else {
      cacheMaterialAssets(favoriteDialog.batchAssets);
    }
    activeFavoriteFolderId.value = folder.id;
    favoriteDialog.newFolderName = "";
    messageApi.success(assetIds.length ? "已加入收藏夹" : "已创建收藏夹");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "收藏夹创建失败");
  }
}

function beginFavoriteFolderRename(folder: MaterialFavoriteFolder) {
  favoriteDialog.editingFolderId = folder.id;
  favoriteDialog.editingFolderName = folder.name;
}

function cancelFavoriteFolderRename() {
  favoriteDialog.editingFolderId = "";
  favoriteDialog.editingFolderName = "";
}

async function commitFavoriteFolderRename(folderId: string) {
  const name = favoriteDialog.editingFolderName.trim();
  if (!name) return;
  try {
    const folder = await renameMaterialFavoriteFolder(folderId, { name });
    upsertFavoriteFolderState(folder);
    cancelFavoriteFolderRename();
    messageApi.success("已重命名收藏夹");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "收藏夹重命名失败");
  }
}

async function confirmDeleteFavoriteFolder(folder: MaterialFavoriteFolder) {
  const confirmed = await requestConfirm({
    title: "删除收藏夹",
    message: `删除后会移除收藏夹「${folder.name}」，素材本身不会被删除。`,
    confirmText: "删除",
  });
  if (!confirmed) return;
  try {
    await deleteMaterialFavoriteFolder(folder.id);
    favoriteFolders.value = favoriteFolders.value.filter((item) => item.id !== folder.id);
    if (activeFavoriteFolderId.value === folder.id) {
      activeFavoriteFolderId.value = "";
    }
    if (favoriteDialog.editingFolderId === folder.id) {
      cancelFavoriteFolderRename();
    }
    messageApi.success("已删除收藏夹");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "收藏夹删除失败");
  }
}

async function toggleFavoriteFolderMembership(folderId: string, asset: MaterialAssetLibraryItem) {
  cacheMaterialAssets([asset]);
  const removing = folderContainsAsset(folderId, asset.id);
  try {
    const folder = removing
      ? await removeMaterialFavoriteAsset(folderId, asset.id)
      : await addMaterialFavoriteAssets(folderId, { assetIds: [asset.id] });
    upsertFavoriteFolderState(folder);
    messageApi.success(removing ? "已移出收藏夹" : "已加入收藏夹");
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "收藏夹更新失败");
  }
}

async function addBatchAssetsToFavoriteFolder(folderId: string) {
  const assetIds = favoriteDialog.batchAssets.map((asset) => asset.id);
  if (!assetIds.length) return;
  try {
    const folder = await addMaterialFavoriteAssets(folderId, { assetIds });
    upsertFavoriteFolderState(folder);
    cacheMaterialAssets(favoriteDialog.batchAssets);
    messageApi.success(`已加入 ${assetIds.length} 个素材`);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "批量收藏失败");
  }
}

function isFavoriteDialogFolderActive(folderId: string) {
  if (favoriteDialog.asset) {
    return folderContainsAsset(folderId, favoriteDialog.asset.id);
  }
  const assetIds = favoriteDialog.batchAssets.map((asset) => asset.id);
  return assetIds.length > 0 && assetIds.every((assetId) => folderContainsAsset(folderId, assetId));
}

function handleFavoriteDialogFolderClick(folderId: string) {
  if (favoriteDialog.asset) {
    void toggleFavoriteFolderMembership(folderId, favoriteDialog.asset);
    return;
  }
  if (favoriteDialog.batchAssets.length) {
    void addBatchAssetsToFavoriteFolder(folderId);
  }
}

async function selectFavoriteFolder(folderId: string) {
  activeFavoriteFolderId.value = folderId;
  selectedAssetIds.value = [];
  batchMode.value = false;
  const folder = favoriteFolders.value.find((item) => item.id === folderId);
  if (!folder) return;
  const missingAssetIds = folder.assetIds.filter((assetId) => !assets.value.some((asset) => asset.id === assetId) && !favoriteAssetCache.value[assetId]);
  if (!missingAssetIds.length) return;
  try {
    const loadedAssets = await Promise.all(missingAssetIds.map((assetId) => fetchMaterialAsset(assetId).catch(() => null)));
    cacheMaterialAssets(loadedAssets.filter((asset): asset is MaterialAssetLibraryItem => Boolean(asset)));
  } catch {
    messageApi.warning("部分收藏素材加载失败");
  }
}

function toggleBatchMode() {
  if (!canUseBatchMode.value) {
    return;
  }
  batchMode.value = !batchMode.value;
}

function normalizedAssetValue(value?: string | null) {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

function isWorkflowArtifactAsset(asset: MaterialAssetLibraryItem) {
  return Boolean(normalizedAssetValue(asset.workflowId))
    || normalizedAssetValue(asset.assetType) === "workflow"
    || normalizedAssetValue(asset.assetRole) === "workflow";
}

function buildQuery(): MaterialAssetQuery {
  const workflowArtifactsSelected = activeLibraryTab.value === "workflow" || filters.assetType === "workflow";
  return {
    q: filters.q.trim() || undefined,
    assetType: filters.assetType as MaterialAssetQuery["assetType"],
    includeWorkflowArtifacts: filters.showWorkflowArtifacts || workflowArtifactsSelected,
    model: filters.model.trim() || undefined,
    aspectRatio: filters.aspectRatio || undefined,
    clipIndex: filters.clipIndex ? Number(filters.clipIndex) : null,
  };
}

function buildPageQuery(offset: number): MaterialAssetQuery {
  return {
    ...buildQuery(),
    offset,
    limit: assetPageLimit,
  };
}

function assetTypeLabel(value?: MaterialAssetType | string | null) {
  const normalized = normalizedAssetValue(value);
  if (normalized === "character_sheet") {
    return "角色三视图";
  }
  if (normalized === "scene") {
    return "场景";
  }
  if (normalized === "prop") {
    return "道具";
  }
  if (normalized === "free" || normalized === "image_generation" || normalized === "image_to_image") {
    return "自由模式";
  }
  if (normalized === "workflow") {
    return "工作流产物";
  }
  return "素材";
}

function assetDisplayTypeLabel(asset: MaterialAssetLibraryItem) {
  if (isWorkflowArtifactAsset(asset)) {
    return "工作流产物";
  }
  return assetTypeLabel(asset.assetType);
}

function mediaTypeLabel(value?: string | null) {
  if (value === "image") {
    return "图片";
  }
  if (value === "video") {
    return "视频";
  }
  if (value === "text") {
    return "文本";
  }
  return "素材";
}

function assetPublicUrl(asset: MaterialAssetLibraryItem) {
  return asset.publicUrl || asset.fileUrl || "";
}

function assetDownloadKind(asset: MaterialAssetLibraryItem): DownloadMediaKind {
  if (asset.mediaType === "image" || asset.mediaType === "video") return asset.mediaType;
  return inferMediaDownloadKind(assetPublicUrl(asset));
}

function assetSubtitle(asset: MaterialAssetLibraryItem) {
  const size = asset.width && asset.height ? `${asset.width} x ${asset.height}` : "";
  const clip = asset.clipIndex ? `镜头 ${asset.clipIndex}` : "";
  const parts = [mediaTypeLabel(asset.mediaType), asset.originModel || asset.originProvider || "", size, clip].filter(Boolean);
  return parts.join(" · ") || "素材";
}

function storyboardText(asset: MaterialAssetLibraryItem) {
  const scriptMarkdown = typeof asset.metadata?.scriptMarkdown === "string" ? asset.metadata.scriptMarkdown : "";
  return scriptMarkdown || asset.title;
}

function storyboardPreviewHtml(asset: MaterialAssetLibraryItem) {
  return renderMarkdownToHtml(storyboardText(asset));
}

function assetListImageUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || "";
}

function assetVideoPosterUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || undefined;
}

function assetOriginalImageUrl(asset: MaterialAssetLibraryItem) {
  return assetPublicUrl(asset);
}

function assetVideoPreviewUrl(asset: MaterialAssetLibraryItem) {
  return assetPublicUrl(asset);
}

function isAssetShareable(asset: MaterialAssetLibraryItem) {
  return (asset.mediaType === "image" || asset.mediaType === "video") && Boolean(assetPublicUrl(asset));
}

function materialShareSource(asset: MaterialAssetLibraryItem): { sourceType: "task" | "workflow" | "material"; sourceId: string } {
  if (asset.workflowId) {
    return { sourceType: "workflow", sourceId: asset.workflowId };
  }
  if (asset.taskId) {
    return { sourceType: "task", sourceId: asset.taskId };
  }
  return { sourceType: "material", sourceId: asset.id };
}

function openAssetPreview(asset: MaterialAssetLibraryItem) {
  previewAsset.value = asset;
  previewImageLoadFailed.value = false;
  previewDialog.title = asset.title;
  if (asset.mediaType === "video") {
    previewDialog.kind = "video";
    previewDialog.html = "";
    previewDialog.url = assetVideoPreviewUrl(asset);
  } else if (asset.mediaType === "image") {
    previewDialog.kind = "image";
    previewDialog.html = "";
    previewDialog.url = assetOriginalImageUrl(asset);
  } else {
    previewDialog.kind = "storyboard";
    previewDialog.html = storyboardPreviewHtml(asset);
    previewDialog.url = "";
  }
  previewDialog.open = true;
}

function openVideoPreview(asset: MaterialAssetLibraryItem) {
  openAssetPreview(asset);
}

function closePreviewDialog() {
  previewDialog.open = false;
  previewDialog.html = "";
  previewDialog.url = "";
  previewAsset.value = null;
  previewImageLoadFailed.value = false;
}

function openStoryboardPreview(asset: MaterialAssetLibraryItem) {
  openAssetPreview(asset);
}

function openImagePreview(asset: MaterialAssetLibraryItem) {
  openAssetPreview(asset);
}

async function navigatePreview(direction: -1 | 1) {
  if (!previewDialog.open || !previewAsset.value) {
    return;
  }
  const currentIndex = previewAssetIndex.value;
  if (currentIndex < 0) {
    return;
  }
  let nextIndex = currentIndex + direction;
  let nextAsset = displayedAssets.value[nextIndex];
  let loadAttempts = 0;
  while (!nextAsset && direction > 0 && !activeFavoriteFolderId.value && hasMoreAssets.value && loadAttempts < 5) {
    loadAttempts += 1;
    await loadMoreAssets();
    nextAsset = displayedAssets.value[nextIndex];
  }
  if (!nextAsset) {
    return;
  }
  openAssetPreview(nextAsset);
}

function isAssetChecked(assetId: string) {
  return selectedAssetIds.value.includes(assetId);
}

function toggleAssetSelection(assetId: string) {
  selectedAssetIds.value = isAssetChecked(assetId)
    ? selectedAssetIds.value.filter((id) => id !== assetId)
    : [...selectedAssetIds.value, assetId];
}

function handleMaterialCardClick(asset: MaterialAssetLibraryItem) {
  if (!batchMode.value) {
    return;
  }
  toggleAssetSelection(asset.id);
}

function handleAssetPreviewClick(asset: MaterialAssetLibraryItem, preview: (asset: MaterialAssetLibraryItem) => void) {
  if (batchMode.value) {
    toggleAssetSelection(asset.id);
    return;
  }
  preview(asset);
}

async function loadAssets() {
  const authenticated = await requireAuth({
    title: "登录后查看素材库",
    message: "素材库只展示你的个人素材，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    assets.value = [];
    hasMoreAssets.value = false;
    messageApi.error("登录后可查看素材库");
    return;
  }
  const requestId = ++assetLoadRequestId;
  loading.value = true;
  loadingMore.value = false;
  try {
    const page = await fetchMaterialAssetPage(buildPageQuery(0));
    if (requestId !== assetLoadRequestId) {
      return;
    }
    assets.value = page?.items ?? [];
    cacheMaterialAssets(assets.value);
    nextAssetOffset.value = page?.nextOffset ?? assets.value.length;
    hasMoreAssets.value = page?.hasMore ?? false;
    selectedAssetIds.value = selectedAssetIds.value.filter((id) => assets.value.some((asset) => asset.id === id));
  } catch (error) {
    if (requestId === assetLoadRequestId) {
      messageApi.error(error instanceof Error ? error.message : "素材列表加载失败");
    }
  } finally {
    if (requestId === assetLoadRequestId) {
      loading.value = false;
    }
  }
}

async function loadMoreAssets() {
  if (loading.value || loadingMore.value || !hasMoreAssets.value) {
    return;
  }
  const requestId = assetLoadRequestId;
  loadingMore.value = true;
  try {
    const page = await fetchMaterialAssetPage(buildPageQuery(nextAssetOffset.value));
    if (requestId !== assetLoadRequestId) {
      return;
    }
    const existingIds = new Set(assets.value.map((asset) => asset.id));
    assets.value = [
      ...assets.value,
      ...(page?.items ?? []).filter((asset) => !existingIds.has(asset.id)),
    ];
    cacheMaterialAssets(page?.items ?? []);
    nextAssetOffset.value = page?.nextOffset ?? assets.value.length;
    hasMoreAssets.value = page?.hasMore ?? false;
  } catch (error) {
    if (requestId === assetLoadRequestId) {
      messageApi.error(error instanceof Error ? error.message : "更多素材加载失败");
    }
  } finally {
    if (requestId === assetLoadRequestId) {
      loadingMore.value = false;
    }
  }
}

function resetFilters() {
  filters.q = "";
  filters.assetType = "";
  filters.showWorkflowArtifacts = false;
  filters.model = "";
  filters.aspectRatio = "";
  filters.clipIndex = "";
  if (activeLibraryTab.value !== "all") {
    activeLibraryTab.value = "all";
    return;
  }
  void loadAssets();
}

async function handleBatchDelete() {
  if (!selectedAssetIds.value.length) {
    return;
  }
  const confirmed = await requestConfirm({
    title: "删除素材",
    message: `删除后无法恢复，将移除选中的 ${selectedAssetIds.value.length} 个素材。`,
    confirmText: "删除",
  });
  if (!confirmed) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后批量删除素材",
    message: "批量删除会修改你的素材库，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续批量删除。");
    return;
  }
  const ids = [...selectedAssetIds.value];
  busyActionKey.value = "batch-delete";
  try {
    for (const assetId of ids) {
      await deleteMaterialAsset(assetId);
    }
    selectedAssetIds.value = [];
    await loadAssets();
    await loadFavoriteFolders();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "批量删除失败");
  } finally {
    busyActionKey.value = "";
  }
}

async function refreshAfterMutation(mutator: () => Promise<unknown>, actionKey: string) {
  const authenticated = await requireAuth({
    title: "登录后操作素材",
    message: "素材操作会修改你的素材库，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续操作素材。");
    return;
  }
  busyActionKey.value = actionKey;
  try {
    await mutator();
    await loadAssets();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "素材操作失败");
  } finally {
    busyActionKey.value = "";
  }
}

function setupLoadMoreObserver() {
  if (typeof IntersectionObserver === "undefined") {
    return;
  }
  loadMoreObserver?.disconnect();
  loadMoreObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        void loadMoreAssets();
      }
    },
    { root: null, rootMargin: "360px 0px 520px", threshold: 0.01 }
  );
  if (loadMoreTrigger.value) {
    loadMoreObserver.observe(loadMoreTrigger.value);
  }
}

async function copyRemoteUrl(remoteUrl?: string | null) {
  const value = remoteUrl?.trim();
  if (!value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
  } catch {
    messageApi.error("远程路径复制失败，请手动复制");
  }
}

async function handleUploadAsset(assetId: string) {
  await refreshAfterMutation(() => uploadMaterialAsset(assetId), `upload-${assetId}`);
}

async function handleDeleteAsset(asset: MaterialAssetLibraryItem) {
  const confirmed = await requestConfirm({
    title: "删除素材",
    message: `删除后无法恢复：${asset.title}`,
    confirmText: "删除",
  });
  if (!confirmed) {
    return;
  }
  await refreshAfterMutation(async () => {
    await deleteMaterialAsset(asset.id);
    await loadFavoriteFolders();
  }, `delete-${asset.id}`);
}

async function handleReuseAsset(assetId: string) {
  const authenticated = await requireAuth({
    title: "登录后复用素材",
    message: "复用素材会创建你的阶段工作流，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续复用素材。");
    return;
  }
  busyActionKey.value = `reuse-${assetId}`;
  try {
    const workflow = await reuseMaterialAsset(assetId, { mode: "clone" });
    await loadAssets();
    await router.push(`/video-tasks/${workflow.id}`);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "素材操作失败");
  } finally {
    busyActionKey.value = "";
  }
}

async function handleDownloadAsset(asset: MaterialAssetLibraryItem) {
  try {
    const result = await downloadMedia({ url: assetPublicUrl(asset), title: asset.title || asset.id, mediaType: assetDownloadKind(asset) });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

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
      await deletePublicShare(existingShareId);
      const next = { ...sharedAssetRecords.value };
      delete next[asset.id];
      sharedAssetRecords.value = next;
      messageApi.success("已取消分享");
    } else {
      const source = materialShareSource(asset);
      const share = await createPublicShare({
        materialAssetId: asset.id,
        sourceType: source.sourceType,
        sourceId: source.sourceId,
      });
      sharedAssetRecords.value = { ...sharedAssetRecords.value, [asset.id]: share.shareId };
      messageApi.success("已分享到首页");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "分享失败");
  } finally {
    sharingAssetId.value = "";
    cancelMaterialShareConfirm();
  }
}

function positionMaterialMenu(event: ToggleEvent) {
  if (event.newState !== "open") return;
  const popover = event.target as HTMLElement;
  const trigger = popover.parentElement?.querySelector<HTMLElement>(".material-more-menu__trigger");
  if (!trigger) return;
  const rect = trigger.getBoundingClientRect();
  const popoverWidth = 170;
  const popoverHeight = Math.max(popover.scrollHeight, popover.offsetHeight, 126);
  let left = rect.right - popoverWidth;
  if (left < 8) left = 8;
  if (left + popoverWidth > window.innerWidth - 8) left = window.innerWidth - popoverWidth - 8;
  let top = rect.bottom + 4;
  if (top + popoverHeight > window.innerHeight - 8) {
    top = Math.max(8, rect.top - popoverHeight - 4);
  }
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

onMounted(async () => {
  await loadFavoriteFolders();
  const queryAssetType = typeof route.query.assetType === "string" ? route.query.assetType : "";
  if (typeFilterOptions.some((option) => option.value === queryAssetType)) {
    filters.assetType = queryAssetType;
    activeLibraryTab.value = libraryTabs.find((tab) => tab.assetType === queryAssetType)?.key ?? "all";
  }
  setupLoadMoreObserver();
  await loadAssets();
});

onBeforeUnmount(() => {
  loadMoreObserver?.disconnect();
  loadMoreObserver = null;
});

watch(activeLibraryTab, (tab) => {
  const option = libraryTabs.find((item) => item.key === tab);
  filters.assetType = option?.assetType ?? "";
  selectedAssetIds.value = [];
  void loadAssets();
});

watch(batchMode, (enabled) => {
  if (!enabled) {
    selectedAssetIds.value = [];
  }
});

watch(canUseBatchMode, (enabled) => {
  if (!enabled) {
    batchMode.value = false;
  }
});

watch(
  loadMoreTrigger,
  () => {
    setupLoadMoreObserver();
  }
);

watch(
  () => filters.assetType,
  (assetType) => {
    if (!assetType && (activeLibraryTab.value === "image" || activeLibraryTab.value === "video")) {
      return;
    }
    const nextTab = libraryTabs.find((tab) => tab.assetType === assetType)?.key ?? "all";
    if (activeLibraryTab.value !== nextTab && nextTab !== "image" && nextTab !== "video") {
      activeLibraryTab.value = nextTab;
    }
  }
);
</script>

<style scoped>
.material-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
  padding: 22px 36px 36px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-base);
  color: var(--text-strong);
}

.material-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 52px;
}

.material-tabs {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  align-items: center;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.material-tabs::-webkit-scrollbar {
  display: none;
}

.material-tab {
  flex: 0 0 auto;
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}

.material-tab:hover,
.material-tab-active {
  background: #eef2ff;
  color: var(--accent-blue);
}

.material-favorite-folders {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-width: 0;
  margin-top: -8px;
}

.material-favorite-folders__head {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 850;
}

.material-favorite-folders__actions {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  min-width: 0;
}

.material-favorite-folders__add {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 10px;
  font-size: 0.76rem;
}

.material-favorite-folders__batch-active {
  color: var(--accent-blue);
}

.material-favorite-folders__selected {
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 850;
  white-space: nowrap;
}

.material-favorite-folders__list {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.material-favorite-folders__list::-webkit-scrollbar {
  display: none;
}

.material-favorite-folder {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  max-width: 180px;
  padding: 0 9px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-body);
  font-size: 0.76rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}

.material-favorite-folder span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.material-favorite-folder small {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-blue);
  font-size: 0.64rem;
  font-weight: 850;
}

.material-favorite-folder:hover,
.material-favorite-folder-active {
  border-color: rgba(99, 102, 241, 0.28);
  background: #eef2ff;
  color: var(--accent-blue);
}

.material-favorite-folders__empty {
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.material-topbar__tools {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: min(100%, 620px);
  padding: 5px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.06);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 180px;
  min-height: 34px;
  padding: 0 10px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: transparent;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.material-search:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(255, 255, 255, 0.6);
}

.material-search__icon {
  display: inline-grid;
  place-items: center;
  color: var(--text-muted);
  transition: color 180ms ease;
}

.material-search:focus-within .material-search__icon {
  color: var(--accent-indigo);
}

.material-search input {
  width: 100%;
  min-height: 30px;
  border: 0;
  outline: 0;
  box-shadow: none;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.86rem;
}

.material-search input:focus-visible {
  box-shadow: none;
}

.material-search input::placeholder {
  color: var(--text-muted);
}

.material-search__clear {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.material-search__clear:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.material-workflow-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.material-workflow-toggle:hover,
.material-workflow-toggle-active {
  background: #eef2ff;
  color: var(--accent-blue);
}

.material-workflow-toggle input {
  position: absolute;
  inline-size: 1px;
  block-size: 1px;
  opacity: 0;
  pointer-events: none;
}

.material-workflow-toggle__track {
  position: relative;
  width: 38px;
  height: 22px;
  flex: 0 0 auto;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.material-workflow-toggle__track::after {
  content: "";
  position: absolute;
  left: 3px;
  top: 3px;
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 3px 8px rgba(20, 28, 36, 0.14);
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.material-workflow-toggle input:checked + .material-workflow-toggle__track {
  border-color: rgba(59, 130, 246, 0.22);
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-blue));
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.12);
}

.material-workflow-toggle input:checked + .material-workflow-toggle__track::after {
  transform: translateX(16px);
}

.material-workflow-toggle input:focus-visible + .material-workflow-toggle__track {
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
}

.material-toolbar-link,
.material-toolbar-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  font-size: 0.84rem;
  font-weight: 800;
  white-space: nowrap;
}

.material-toolbar-link :deep(svg),
.material-toolbar-primary :deep(svg),
.material-card__chips button :deep(svg) {
  width: 15px;
  height: 15px;
}

.material-toolbar-link {
  position: relative;
  width: 34px;
  padding: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.material-toolbar-link:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.material-toolbar-link-active,
.material-toolbar-link:hover:not(:disabled) {
  background: #eef2ff;
  color: var(--accent-blue);
}

.material-toolbar-badge {
  position: absolute;
  right: -3px;
  top: -3px;
  display: grid;
  place-items: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: var(--accent-coral);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 850;
  line-height: 1;
}

.material-toolbar-primary {
  gap: 6px;
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-blue));
  color: #fff;
  box-shadow: 0 10px 22px rgba(99, 102, 241, 0.16);
}

.material-toolbar-divider {
  width: 1px;
  height: 18px;
  background: rgba(0, 0, 0, 0.06);
}

.material-filter-drawer,
.material-batch-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(138px, 1fr)) auto;
  gap: 8px;
  align-items: end;
  padding: 10px 0 0;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.material-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.material-field span {
  margin: 0 4px;
  color: #74838d;
  font-size: 0.7rem;
  font-weight: 820;
}

.material-filter-drawer__actions,
.material-batch-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.material-filter-drawer__actions .jd-button--sm {
  min-height: 38px;
  border-radius: 11px;
}

.material-filter-drawer :deep(.app-select__trigger),
.material-filter-drawer .field-input {
  min-height: 40px;
  border-radius: 12px;
  border-color: rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: none;
}

.material-batch-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  justify-content: space-between;
  grid-template-columns: none;
  margin: -2px 0 2px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 10px 26px rgba(99, 102, 241, 0.06);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-batch-bar span {
  color: var(--text-body);
  font-weight: 800;
}

.material-batch-bar .jd-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.material-error {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff4f6;
  color: var(--accent-danger);
}

.material-empty {
  display: grid;
  place-items: center;
  min-height: 260px;
  padding: 28px;
  border: 1px solid rgba(79, 70, 229, 0.1);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-muted);
}

.material-empty :deep(svg) {
  width: 24px;
  height: 24px;
}

.material-empty-inline {
  grid-column: 1 / -1;
  align-content: center;
  justify-items: center;
  gap: 10px;
  min-height: 220px;
  padding: 42px 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.material-empty-inline strong {
  color: var(--text-strong);
}

.material-asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
  gap: 14px;
  align-content: start;
}

.material-load-more {
  display: grid;
  place-items: center;
  min-height: 34px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text-muted);
}

.material-load-more > span {
  width: 26px;
  height: 4px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.08);
}

.material-load-more :deep(svg) {
  width: 18px;
  height: 18px;
}

.material-card {
  position: relative;
  display: grid;
  gap: 10px;
  min-height: 258px;
  padding: 9px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: var(--text-strong);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.045);
  backdrop-filter: blur(40px) saturate(2.0);
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.material-card:hover,
.material-card-selected {
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: 0 14px 32px rgba(99, 102, 241, 0.085);
  transform: translateY(-1px);
}

.material-card-batchable {
  cursor: pointer;
  transform: scale(0.96);
}

.material-card-batchable:hover {
  transform: translateY(-1px) scale(0.96);
}

.material-card-batchable.material-card-selected {
  border-color: rgba(99, 102, 241, 0.44);
  background: rgba(238, 242, 255, 0.86);
  box-shadow: 0 14px 34px rgba(99, 102, 241, 0.14);
  transform: translateY(-1px) scale(0.98);
}

.material-card__check {
  position: absolute;
  left: 20px;
  top: 20px;
  z-index: 2;
}

.material-card__check input {
  position: absolute;
  opacity: 0;
}

.material-card__check span {
  display: block;
  width: 24px;
  height: 24px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.12);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

.material-card__check input:checked + span {
  background: var(--accent-indigo);
}

.material-card__preview {
  height: 166px;
  border-radius: 11px;
  overflow: hidden;
  background: #eef2ff;
}

.material-card__favorite {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  color: var(--text-muted);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
  cursor: pointer;
  backdrop-filter: blur(18px) saturate(1.4);
}

.material-card__favorite:hover,
.material-card__favorite-active {
  background: rgba(255, 255, 255, 0.92);
  color: #e54865;
}

.material-card__preview video,
.material-card__preview img,
.material-card__text {
  width: 100%;
  height: 100%;
}

.material-card__preview video,
.material-card__preview img {
  display: block;
  object-fit: cover;
  background: #eef2ff;
}

.material-preview-trigger {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
  text-align: left;
}

.material-preview-fallback {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  background:
    linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(99, 102, 241, 0.08)),
    #eef2ff;
  color: var(--text-muted);
}

.material-preview-fallback :deep(svg) {
  width: 24px;
  height: 24px;
}

.material-preview-trigger-video {
  position: relative;
}

.material-video-play,
.material-preview-trigger-placeholder span {
  position: absolute;
  left: 12px;
  bottom: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.6);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
}

.material-video-play :deep(svg) {
  width: 15px;
  height: 15px;
}

.material-preview-trigger-placeholder {
  position: relative;
  display: grid;
  place-items: center;
  background: #eef2f4;
  cursor: pointer;
}

.material-preview-trigger-placeholder span {
  position: static;
  width: auto;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-muted);
}

.material-card__text {
  padding: 14px;
  background: #eef2ff;
  color: var(--text-body);
  line-height: 1.55;
  overflow: hidden;
}

.material-card__text :deep(h1),
.material-card__text :deep(h2),
.material-card__text :deep(h3),
.material-card__text :deep(p) {
  margin: 0 0 8px;
}

.material-card__text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.material-card__text :deep(th),
.material-card__text :deep(td) {
  padding: 5px 6px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  vertical-align: top;
}

.material-card__body {
  display: grid;
  gap: 7px;
}

.material-card__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  align-items: start;
  gap: 6px;
  min-width: 0;
}

.material-card__title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.material-card__title strong {
  overflow: hidden;
  color: var(--text-strong);
  font-size: 0.92rem;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-card__title span {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.material-card__chips span,
.material-card__chips button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 25px;
  padding: 0 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 999px;
  background: #eef2ff;
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.material-card__chips button {
  width: 30px;
  padding: 0;
  color: var(--accent-indigo);
  cursor: copy;
}

.material-more-menu {
  position: relative;
  justify-self: end;
  margin-top: -6px;
}

.material-more-menu__trigger {
  display: inline-grid;
  place-items: center;
  width: 38px;
  min-height: 38px;
  padding: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}

.material-more-menu__trigger:hover,
.material-more-menu__trigger:focus-visible {
  background: #eef2ff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.08);
}

.material-more-menu__panel {
  position: fixed;
  inset: unset;
  z-index: 80;
  width: 168px;
  gap: 0;
  padding: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(250, 253, 254, 0.98));
  box-shadow:
    0 18px 42px rgba(0, 0, 0, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-more-menu__panel:popover-open {
  display: grid;
}

.material-more-menu__panel button,
.material-more-menu__panel a {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 11px;
  border: 0;
  border-radius: 11px;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
  text-decoration: none;
}

.material-more-menu__panel button :deep(svg),
.material-more-menu__panel a :deep(svg) {
  width: 15px;
  height: 15px;
}

.material-more-menu__panel button span,
.material-more-menu__panel a span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-more-menu__panel button:hover,
.material-more-menu__panel a:hover {
  background: rgba(224, 231, 255, 0.76);
  color: var(--accent-blue);
}

.material-menu-danger {
  color: var(--accent-danger) !important;
}

.material-preview-favorite-action {
  color: #e54865 !important;
}

.material-preview-favorite-action-active {
  background: rgba(251, 113, 133, 0.14) !important;
}

.material-favorite-dialog {
  position: fixed;
  inset: 0;
  z-index: 1480;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 10, 20, 0.25);
  backdrop-filter: blur(40px) saturate(2);
}

.material-rename-dialog {
  position: fixed;
  inset: 0;
  z-index: 1480;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 10, 20, 0.25);
  backdrop-filter: blur(40px) saturate(2);
}

.material-favorite-dialog__panel {
  display: grid;
  gap: 14px;
  width: min(440px, 100%);
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(40px) saturate(1.8);
}

.material-rename-dialog__panel {
  display: grid;
  gap: 14px;
  width: min(420px, 100%);
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(40px) saturate(1.8);
}

.material-favorite-dialog__head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.material-rename-dialog__head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.material-favorite-dialog__head h3,
.material-favorite-dialog__head p,
.material-rename-dialog__head h3,
.material-rename-dialog__head p {
  margin: 0;
}

.material-favorite-dialog__head h3,
.material-rename-dialog__head h3 {
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.35;
}

.material-favorite-dialog__head p,
.material-rename-dialog__head p {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.78rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.material-favorite-dialog__head button,
.material-rename-dialog__head button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
}

.material-favorite-dialog__head button:hover,
.material-rename-dialog__head button:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.material-rename-dialog__field {
  display: grid;
  gap: 8px;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 850;
}

.material-rename-dialog__field input {
  min-width: 0;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid rgba(79, 70, 229, 0.14);
  border-radius: 12px;
  outline: 0;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-strong);
  font-size: 0.88rem;
  font-weight: 800;
}

.material-rename-dialog__field input:focus-visible {
  border-color: rgba(99, 102, 241, 0.42);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.material-rename-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.material-favorite-dialog__folders {
  display: grid;
  gap: 8px;
  max-height: min(320px, calc(100vh - 260px));
  overflow: auto;
}

.material-favorite-dialog__folder {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 4px;
  border: 1px solid rgba(79, 70, 229, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-body);
  font-size: 0.84rem;
  font-weight: 800;
}

.material-favorite-dialog__folder-main {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 38px;
  padding: 0 8px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.material-favorite-dialog__folder-main:disabled {
  cursor: default;
}

.material-favorite-dialog__folder-main span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-favorite-dialog__folder-main small {
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 800;
}

.material-favorite-dialog__folder:hover,
.material-favorite-dialog__folder-active {
  border-color: rgba(99, 102, 241, 0.26);
  background: #eef2ff;
  color: var(--accent-blue);
}

.material-favorite-dialog__folder-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}

.material-favorite-dialog__folder-actions button,
.material-favorite-dialog__rename button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 30px;
  padding: 0 9px;
  border: 0;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-blue);
  font-size: 0.74rem;
  font-weight: 850;
  cursor: pointer;
  white-space: nowrap;
}

.material-favorite-dialog__folder-actions button:hover,
.material-favorite-dialog__rename button:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.16);
}

.material-favorite-dialog__folder-actions .material-favorite-dialog__folder-delete {
  background: rgba(251, 113, 133, 0.12);
  color: var(--accent-danger);
}

.material-favorite-dialog__folder-actions .material-favorite-dialog__folder-delete:hover {
  background: rgba(251, 113, 133, 0.18);
}

.material-favorite-dialog__rename {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
}

.material-favorite-dialog__rename input {
  min-width: 0;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 10px;
  outline: 0;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-strong);
  font-size: 0.84rem;
  font-weight: 800;
}

.material-favorite-dialog__rename input:focus-visible {
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.material-favorite-dialog__rename button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.material-favorite-dialog__empty {
  display: grid;
  place-items: center;
  min-height: 86px;
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 750;
}

.material-favorite-dialog__create {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.material-favorite-dialog__create input {
  min-width: 0;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 12px;
  outline: 0;
  background: rgba(255, 255, 255, 0.76);
  color: var(--text-strong);
  font-size: 0.86rem;
}

.material-favorite-dialog__create input:focus-visible {
  border-color: rgba(99, 102, 241, 0.42);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.material-favorite-dialog__create button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 13px;
  border: 0;
  border-radius: 12px;
  background: var(--bg-accent);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 850;
  cursor: pointer;
}

.material-favorite-dialog__create button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.material-favorite-dialog-fade-enter-active,
.material-favorite-dialog-fade-leave-active {
  transition: opacity 160ms ease;
}

.material-favorite-dialog-fade-enter-active .material-favorite-dialog__panel,
.material-favorite-dialog-fade-enter-active .material-rename-dialog__panel,
.material-favorite-dialog-fade-leave-active .material-favorite-dialog__panel,
.material-favorite-dialog-fade-leave-active .material-rename-dialog__panel {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.material-favorite-dialog-fade-enter-from,
.material-favorite-dialog-fade-leave-to {
  opacity: 0;
}

.material-favorite-dialog-fade-enter-from .material-favorite-dialog__panel,
.material-favorite-dialog-fade-enter-from .material-rename-dialog__panel,
.material-favorite-dialog-fade-leave-to .material-favorite-dialog__panel,
.material-favorite-dialog-fade-leave-to .material-rename-dialog__panel {
  transform: translateY(8px) scale(0.985);
}

@media (max-width: 1180px) {
  .material-topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .material-topbar__tools {
    min-width: 0;
    width: 100%;
  }

}

@media (max-width: 900px) {
  .material-filter-drawer {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .material-view {
    padding: 14px;
  }

  .material-topbar {
    gap: 12px;
  }

  .material-topbar__tools {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto auto;
    gap: 6px;
    align-items: center;
    min-width: 0;
    width: 100%;
    padding: 5px;
  }

  .material-batch-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .material-toolbar-divider {
    display: none;
  }

  .material-search {
    width: auto;
    min-width: 0;
    padding: 0 8px;
  }

  .material-workflow-toggle {
    width: 34px;
    min-height: 34px;
    justify-content: center;
    padding: 0;
  }

  .material-workflow-toggle__text {
    display: none;
  }

  .material-workflow-toggle__track {
    width: 30px;
    height: 18px;
  }

  .material-workflow-toggle__track::after {
    left: 3px;
    top: 3px;
    width: 10px;
    height: 10px;
  }

  .material-workflow-toggle input:checked + .material-workflow-toggle__track::after {
    transform: translateX(12px);
  }

  .material-toolbar-link,
  .material-toolbar-primary {
    min-height: 34px;
    padding: 0 10px;
  }

  .material-toolbar-link {
    width: 34px;
    padding: 0;
  }

  .material-toolbar-primary {
    gap: 4px;
    width: 34px;
    padding: 0;
    font-size: 0;
  }

  .material-toolbar-primary :deep(svg) {
    width: 16px;
    height: 16px;
  }

  .material-empty-inline {
    min-height: 170px;
    padding: 28px 0;
  }

  .material-filter-drawer {
    position: fixed;
    left: 14px;
    right: 14px;
    bottom: 14px;
    z-index: 90;
    grid-template-columns: 1fr;
    max-height: min(520px, calc(100vh - 92px));
    overflow: auto;
    padding: 20px 10px 10px;
    border-radius: 22px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(250, 253, 254, 0.98));
    box-shadow:
      0 -18px 46px rgba(0, 0, 0, 0.08),
      0 0 0 1px rgba(255, 255, 255, 0.82) inset;
  }

  .material-filter-drawer::before {
    content: "";
    justify-self: center;
    width: 38px;
    height: 4px;
    margin: -9px 0 2px;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.08);
  }

  .material-asset-grid {
    grid-template-columns: 1fr;
  }

  .material-card__preview {
    height: 204px;
  }

  .material-card__favorite {
    top: 16px;
    right: 16px;
  }

  .material-favorite-dialog {
    align-items: end;
    padding: 14px;
  }

  .material-favorite-dialog__panel {
    border-radius: 20px;
  }

}
</style>

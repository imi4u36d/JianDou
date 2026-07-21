<template>
  <section class="material-view">
    <Teleport defer to="#workspace-page-actions">
      <div class="material-topbar">
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
          <label class="material-tab-select">
            <span>素材分类</span>
            <select :value="activeLibraryTab" aria-label="素材分类" @change="handleLibraryTabSelect">
              <option v-for="tab in libraryTabs" :key="tab.key" :value="tab.key">{{ tab.label }}</option>
            </select>
          </label>
          <label class="material-search">
            <span class="material-search__icon" aria-hidden="true"><IconSearch size="sm" /></span>
            <input v-model="filters.q" type="search" placeholder="搜索素材" @keyup.enter="loadAssets" />
            <button
              v-if="filters.q"
              class="material-search__clear"
              type="button"
              aria-label="清除搜索"
              @click="
                filters.q = '';
                loadAssets();
              "
            >
              <IconClose size="xs" />
            </button>
          </label>
          <label
            class="material-workflow-toggle"
            :class="{ 'material-workflow-toggle-active': filters.showWorkflowArtifacts }"
          >
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
          <button class="material-toolbar-primary" type="button" :disabled="loading" @click="loadAssets">
            <IconLoading v-if="loading" size="sm" />
            <IconSearch v-else size="sm" />
            搜索
          </button>
        </div>
      </div>
    </Teleport>

    <section class="material-favorite-folders" aria-label="收藏夹">
      <div class="material-favorite-folders__head">
        <button
          class="jd-button jd-button--ghost jd-button--xs material-favorite-folders__add"
          type="button"
          @click="openFavoriteDialog()"
        >
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
          <button
            class="jd-button jd-button--secondary jd-button--xs"
            type="button"
            :disabled="!selectedAssetIds.length"
            @click="openBatchFavoriteDialog"
          >
            <IconHeart size="xs" />
            添加到收藏
          </button>
          <button
            class="jd-button jd-button--danger jd-button--xs"
            type="button"
            :disabled="!selectedAssetIds.length || Boolean(busyActionKey)"
            @click="handleBatchDelete"
          >
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
        <input
          v-model="filters.clipIndex"
          class="field-input"
          type="number"
          min="0"
          step="1"
          placeholder="全部"
          @keyup.enter="loadAssets"
        />
      </label>
      <div class="material-filter-drawer__actions">
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="loading"
          @click="loadAssets"
        >
          应用
        </button>
        <button
          class="jd-button jd-button--ghost jd-button--sm"
          type="button"
          :disabled="loading"
          @click="resetFilters"
        >
          清空
        </button>
      </div>
    </section>

    <section v-if="loading && !assets.length" class="material-empty">
      <IconLoading size="lg" />
    </section>

    <section v-else class="material-asset-grid">
      <MaterialAssetCard
        v-for="asset in displayedAssets"
        :key="asset.id"
        :asset="asset"
        :batch-mode="batchMode"
        :selected="isAssetChecked(asset.id)"
        :favorite="isAssetFavorited(asset.id)"
        :busy-action-key="busyActionKey"
        @toggle-selection="toggleAssetSelection"
        @preview="openAssetPreview"
        @favorite="openFavoriteDialog"
        @upload="handleUploadAsset"
        @reuse="handleReuseAsset"
        @rename="openRenameDialog"
        @download="handleDownloadAsset"
        @delete="handleDeleteAsset"
      />

      <div
        v-if="!displayedAssets.length && (activeFavoriteFolderId || !hasMoreAssets)"
        class="material-empty material-empty-inline"
      >
        <strong>{{ materialEmptyTitle }}</strong>
      </div>

      <div
        v-else-if="!activeFavoriteFolderId && (displayedAssets.length || hasMoreAssets)"
        ref="loadMoreTrigger"
        class="material-load-more"
      >
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
      </template>
      <template v-if="previewAsset" #details>
        <div class="material-preview-details">
          <div class="material-preview-details__tags">
            <span>{{ previewAsset.mediaType }}</span>
            <span v-if="previewAsset.mimeType">{{ previewAsset.mimeType }}</span>
          </div>
          <section>
            <h4>生成信息</h4>
            <dl>
              <div>
                <dt>模型</dt>
                <dd>{{ previewAsset.originModel || "未记录" }}</dd>
              </div>
              <div>
                <dt>提供方</dt>
                <dd>{{ previewAsset.originProvider || "未记录" }}</dd>
              </div>
              <div>
                <dt>尺寸</dt>
                <dd>
                  {{
                    previewAsset.width && previewAsset.height
                      ? `${previewAsset.width} × ${previewAsset.height}`
                      : "未知"
                  }}
                </dd>
              </div>
              <div v-if="previewAsset.durationSeconds">
                <dt>时长</dt>
                <dd>{{ previewAsset.durationSeconds }} 秒</dd>
              </div>
              <div>
                <dt>创建时间</dt>
                <dd>{{ formatMaterialDate(previewAsset.createdAt) }}</dd>
              </div>
              <div>
                <dt>来源</dt>
                <dd>{{ previewAsset.workflowId ? "工作流产物" : previewAsset.taskId ? "任务产物" : "素材库" }}</dd>
              </div>
            </dl>
          </section>
          <section v-if="previewAsset.ratingNote">
            <h4>备注</h4>
            <p>{{ previewAsset.ratingNote }}</p>
          </section>
        </div>
      </template>
    </AppPreviewDialog>

    <MaterialFavoriteDialog
      :open="favoriteDialog.open"
      :folders="favoriteFolders"
      :asset="favoriteDialog.asset"
      :batch-assets="favoriteDialog.batchAssets"
      :active-folder-ids="favoriteDialogActiveFolderIds"
      @close="closeFavoriteDialog"
      @folder-click="handleFavoriteDialogFolderClick"
      @create="createFavoriteFolder"
      @rename="commitFavoriteFolderRename"
      @delete="confirmDeleteFavoriteFolder"
    />
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
              <button
                type="button"
                class="jd-button jd-button--ghost jd-button--sm"
                :disabled="Boolean(busyActionKey)"
                @click="closeRenameDialog"
              >
                取消
              </button>
              <button
                type="submit"
                class="jd-button jd-button--primary jd-button--sm"
                :disabled="!renameDialog.title.trim() || Boolean(busyActionKey)"
              >
                <IconLoading v-if="busyActionKey === `rename-${renameDialog.asset?.id}`" size="xs" />
                保存
              </button>
            </div>
          </form>
        </div>
      </Transition>
    </Teleport>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { fetchMaterialAssetPage } from "@/features/materials";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { useMaterialPreview } from "@/composables/materials/useMaterialPreview";
import { useMaterialPagination } from "@/composables/materials/useMaterialPagination";
import { useMaterialFavoriteCommands } from "@/composables/materials/useMaterialFavoriteCommands";
import { useMaterialAssetCommands } from "@/composables/materials/useMaterialAssetCommands";
import { useMaterialLibraryState } from "@/composables/materials/useMaterialLibraryState";
import { useMaterialLibraryLifecycle } from "@/composables/materials/useMaterialLibraryLifecycle";
import AppSelect from "@/components/common/AppSelect.vue";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import MaterialAssetCard from "@/views/materials/components/MaterialAssetCard.vue";
import MaterialFavoriteDialog from "@/views/materials/components/MaterialFavoriteDialog.vue";
import type { MaterialAssetLibraryItem, MaterialFavoriteFolder } from "@/types";
import { messageApi } from "@/composables/useMessage";
import {
  IconCheck,
  IconClose,
  IconDelete,
  IconHeart,
  IconLoading,
  IconPlus,
  IconSearch,
  IconSettings,
} from "@/components/icons";

const route = useRoute();

function handleLibraryTabSelect(event: Event) {
  selectLibraryTab((event.target as HTMLSelectElement).value);
}

function formatMaterialDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}
const busyActionKey = ref("");
const favoriteFolders = ref<MaterialFavoriteFolder[]>([]);
const favoriteAssetCache = ref<Record<string, MaterialAssetLibraryItem>>({});
const favoriteDialog = reactive({
  open: false,
  asset: null as MaterialAssetLibraryItem | null,
  batchAssets: [] as MaterialAssetLibraryItem[],
});
const {
  activeLibraryTab,
  advancedFiltersOpen,
  batchMode,
  selectedAssetIds,
  activeFavoriteFolderId,
  filters,
  libraryTabs,
  typeFilterOptions,
  aspectRatioFilterOptions,
  displayedAssets,
  canUseBatchMode,
  activeFilterCount,
  materialEmptyTitle,
  selectLibraryTab,
  toggleBatchMode,
  buildPageQuery,
  isAssetChecked,
  toggleAssetSelection,
  resetFilters: resetLibraryFilters,
} = useMaterialLibraryState({
  assets: () => assets.value,
  favoriteFolders: () => favoriteFolders.value,
  favoriteAssetCache: () => favoriteAssetCache.value,
});
const {
  loading,
  loadingMore,
  assets,
  hasMoreAssets,
  clearAssets,
  loadAssets: loadAssetPage,
  loadMoreAssets,
} = useMaterialPagination({
  fetchPage: fetchMaterialAssetPage,
  buildQuery: buildPageQuery,
  cacheAssets: (items) => cacheMaterialAssets(items),
  onError: (error, mode) => {
    const fallback = mode === "append" ? "更多素材加载失败" : "素材列表加载失败";
    messageApi.error(error instanceof Error ? error.message : fallback);
  },
});
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();
const {
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
} = useMaterialFavoriteCommands({
  favoriteFolders,
  activeFavoriteFolderId,
  favoriteAssetCache,
  favoriteDialog,
  selectedAssetIds,
  batchMode,
  assets,
  displayedAssets,
  requestConfirm,
});

const { loadMoreTrigger, loadAssets, resetFilters } = useMaterialLibraryLifecycle({
  activeLibraryTab,
  batchMode,
  selectedAssetIds,
  canUseBatchMode,
  filters,
  assets,
  libraryTabs,
  typeFilterOptions,
  routeAssetType: () => route.query.assetType,
  authorize: () =>
    requireAuth({
      title: "登录后查看素材库",
      message: "素材库只展示你的个人素材，请先登录或使用邀请码注册。",
    }),
  notifyAuthenticationRequired: () => messageApi.error("登录后可查看素材库"),
  clearAssets,
  loadAssetPage,
  loadMoreAssets,
  loadFavoriteFolders,
  resetLibraryFilters,
});

const {
  previewAsset,
  previewImageLoadFailed,
  previewDialog,
  canPreviewPrevious,
  canPreviewNext,
  openAssetPreview,
  closePreviewDialog,
  syncPreviewAsset,
  navigatePreview,
} = useMaterialPreview({
  displayedAssets,
  activeFavoriteFolderId,
  hasMoreAssets,
  loadMoreAssets,
});

const {
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
} = useMaterialAssetCommands({
  assets,
  busyActionKey,
  selectedAssetIds,
  previewAsset,
  cacheMaterialAssets,
  syncPreviewAsset,
  loadAssets,
  loadFavoriteFolders,
  requestConfirm,
});

const favoriteDialogActiveFolderIds = computed(() =>
  favoriteFolders.value.filter((folder) => isFavoriteDialogFolderActive(folder.id)).map((folder) => folder.id),
);
</script>

<style scoped src="./material-library-view.css"></style>

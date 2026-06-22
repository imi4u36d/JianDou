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
          @click="activeLibraryTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div class="material-topbar__tools">
        <label class="material-search">
          <span aria-hidden="true"><IconSearch size="sm" /></span>
          <input v-model="filters.q" type="search" placeholder="搜索" @keyup.enter="loadAssets" />
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
        <button
          class="material-toolbar-link"
          type="button"
          :class="{ 'material-toolbar-link-active': batchMode }"
          :disabled="!canUseBatchMode"
          aria-label="批量选择"
          title="批量"
          @click="toggleBatchMode"
        >
          <IconCheck size="sm" />
        </button>
        <RouterLink class="material-toolbar-primary" to="/workspace">
          <IconPlus size="sm" />
          新建
        </RouterLink>
      </div>
    </header>

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
        <button class="btn-primary btn-sm" type="button" :disabled="loading" @click="loadAssets">应用</button>
        <button class="btn-ghost btn-sm" type="button" :disabled="loading" @click="resetFilters">清空</button>
      </div>
    </section>

    <section v-if="batchMode && displayedAssets.length" class="material-batch-bar">
      <span>已选 {{ selectedAssetIds.length }}</span>
      <button class="btn-secondary btn-sm" type="button" :disabled="!selectedAssetIds.length || Boolean(busyActionKey)" @click="handleBatchUpload">
        <IconLoading v-if="busyActionKey === 'batch-upload'" size="xs" />
        <IconUpload v-else size="xs" />
        {{ busyActionKey === "batch-upload" ? "上传中" : "上传" }}
      </button>
      <button class="btn-danger btn-sm" type="button" :disabled="!selectedAssetIds.length || Boolean(busyActionKey)" @click="handleBatchDelete">
        <IconLoading v-if="busyActionKey === 'batch-delete'" size="xs" />
        <IconDelete v-else size="xs" />
        {{ busyActionKey === "batch-delete" ? "删除中" : "删除" }}
      </button>
    </section>

    <section v-if="loading && !assets.length" class="material-empty">
      <IconLoading size="lg" />
    </section>

    <section v-else class="material-asset-grid">
      <article v-for="asset in displayedAssets" :key="asset.id" class="material-card" :class="{ 'material-card-selected': isAssetChecked(asset.id) }">
        <label v-if="batchMode" class="material-card__check">
          <input type="checkbox" :checked="isAssetChecked(asset.id)" @change="toggleAssetSelection(asset.id)" />
          <span></span>
        </label>

        <div class="material-card__preview">
          <button
            v-if="asset.mediaType === 'video' && assetVideoPosterUrl(asset)"
            class="material-preview-trigger material-preview-trigger-video"
            type="button"
            @click="openVideoAsset(asset)"
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
            @click="openVideoAsset(asset)"
          >
            <span><IconVideo size="sm" /></span>
          </button>
          <button
            v-else-if="asset.mediaType === 'image' && assetListImageUrl(asset)"
            class="material-preview-trigger material-preview-trigger-image"
            type="button"
            @click="openImagePreview(asset)"
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
            @click="openImagePreview(asset)"
          >
            <span><IconImage size="sm" /></span>
          </button>
          <button
            v-else
            class="material-preview-trigger material-preview-trigger-text"
            type="button"
            @click="openStoryboardPreview(asset)"
          >
            <div class="material-card__text" v-html="storyboardPreviewHtml(asset)"></div>
          </button>
        </div>

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
                <RouterLink v-if="asset.workflowId" :to="`/workflows/${asset.workflowId}`">
                  <IconWorkflow size="xs" />
                  <span>工作流</span>
                </RouterLink>
                <a :href="asset.fileUrl" download target="_blank" rel="noopener noreferrer">
                  <IconDownload size="xs" />
                  <span>下载</span>
                </a>
                <button type="button" class="material-menu-danger" :disabled="busyActionKey === `delete-${asset.id}`" @click="handleDeleteAsset(asset)">
                  <IconLoading v-if="busyActionKey === `delete-${asset.id}`" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === `delete-${asset.id}` ? "删除中" : "删除" }}</span>
                </button>
              </div>
            </div>
          </div>
          <div class="material-card__chips">
            <span>{{ assetTypeLabel(asset.assetType) }}</span>
            <button v-if="asset.remoteUrl" type="button" :title="`复制远程地址：${asset.remoteUrl}`" aria-label="复制远程地址" @click="copyRemoteUrl(asset.remoteUrl)">
              <IconUpload size="xs" />
            </button>
            <span v-else>本地</span>
          </div>
        </div>
      </article>

      <div v-if="!displayedAssets.length && !hasMoreAssets" class="material-empty material-empty-inline">
        <strong>{{ materialEmptyTitle }}</strong>
      </div>

      <div v-else-if="displayedAssets.length || hasMoreAssets" ref="loadMoreTrigger" class="material-load-more">
        <IconLoading v-if="loadingMore" size="sm" />
        <span v-else-if="hasMoreAssets" aria-hidden="true"></span>
      </div>
    </section>

    <div v-if="previewDialog.open" class="material-preview-overlay" role="dialog" aria-modal="true" @click.self="closePreviewDialog">
      <div class="material-preview-dialog" :class="{ 'material-preview-dialog-image': previewDialog.kind === 'image' }">
        <div v-if="previewDialog.kind !== 'image'" class="material-preview-dialog__head">
          <div>
            <h3>{{ previewDialog.title }}</h3>
          </div>
          <button type="button" class="material-preview-dialog__close" aria-label="关闭预览" @click="closePreviewDialog">
            <IconClose size="sm" />
          </button>
        </div>
        <button v-else type="button" class="material-preview-dialog__close material-preview-dialog__close-floating" aria-label="关闭预览" @click="closePreviewDialog">
          <IconClose size="sm" />
        </button>
        <strong v-if="previewDialog.kind === 'image'" class="material-preview-dialog__caption">{{ previewDialog.title }}</strong>
        <img
          v-if="previewDialog.kind === 'image' && !previewImageLoadFailed"
          class="material-preview-dialog__image"
          :src="previewDialog.url"
          :alt="previewDialog.title"
          @error="previewImageLoadFailed = true"
        />
        <div v-else-if="previewDialog.kind === 'image'" class="material-preview-dialog__fallback">
          <IconImage size="lg" />
          <span>{{ previewDialog.title }}</span>
        </div>
        <div v-else class="material-preview-dialog__markdown" v-html="previewDialog.html"></div>
      </div>
    </div>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteMaterialAsset, fetchMaterialAssetPage, reuseMaterialAsset, uploadMaterialAsset } from "@/features/materials";
import { requireAuth } from "@/auth/modal";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import AppSelect from "@/components/common/AppSelect.vue";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import type { MaterialAssetLibraryItem, MaterialAssetQuery, MaterialAssetType } from "@/types";
import { renderMarkdownToHtml } from "@/utils/markdown";
import { messageApi } from "@/composables/useMessage";
import { IconCheck, IconClose, IconDelete, IconDownload, IconImage, IconLoading, IconMore, IconPlus, IconSearch, IconSettings, IconUpload, IconVideo, IconWorkflow } from "@/components/icons";

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

const assets = ref<MaterialAssetLibraryItem[]>([]);
const loadMoreTrigger = ref<HTMLElement | null>(null);
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
  { label: "9:16", value: "9:16" },
  { label: "16:9", value: "16:9" },
];

const filters = reactive({
  q: "",
  assetType: "",
  model: "",
  aspectRatio: "",
  clipIndex: "",
});
const previewDialog = reactive({
  open: false,
  kind: "storyboard" as "storyboard" | "image",
  title: "",
  html: "",
  url: "",
});
const previewImageLoadFailed = ref(false);
const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

const displayedAssets = computed(() => {
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
  return assets.value.filter((asset) => asset.assetType === tab);
});

const canUseBatchMode = computed(() => displayedAssets.value.length > 0);
const activeFilterCount = computed(() => {
  return [filters.assetType, filters.model.trim(), filters.aspectRatio, filters.clipIndex].filter(Boolean).length;
});
const materialEmptyTitle = computed(() => (filters.q.trim() || activeFilterCount.value > 0 || activeLibraryTab.value !== "all" ? "没有匹配素材" : "暂无素材"));

function toggleBatchMode() {
  if (!canUseBatchMode.value) {
    return;
  }
  batchMode.value = !batchMode.value;
}
function buildQuery(): MaterialAssetQuery {
  return {
    q: filters.q.trim() || undefined,
    assetType: filters.assetType as MaterialAssetQuery["assetType"],
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
  if (value === "character_sheet") {
    return "角色三视图";
  }
  if (value === "scene") {
    return "场景";
  }
  if (value === "prop") {
    return "道具";
  }
  if (value === "free") {
    return "自由模式";
  }
  if (value === "workflow") {
    return "工作流产物";
  }
  return "工作流产物";
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

function assetSubtitle(asset: MaterialAssetLibraryItem) {
  const size = asset.width && asset.height ? `${asset.width} x ${asset.height}` : "";
  const clip = asset.clipIndex ? `镜头 ${asset.clipIndex}` : "";
  const parts = [mediaTypeLabel(asset.mediaType), asset.originModel || asset.originProvider || "", size, clip].filter(Boolean);
  return parts.join(" · ") || "素材";
}

function compactUrl(url: string) {
  if (url.length <= 42) {
    return url;
  }
  return `${url.slice(0, 24)}...${url.slice(-14)}`;
}

function storyboardText(asset: MaterialAssetLibraryItem) {
  const scriptMarkdown = typeof asset.metadata?.scriptMarkdown === "string" ? asset.metadata.scriptMarkdown : "";
  return scriptMarkdown || asset.title;
}

function storyboardPreviewHtml(asset: MaterialAssetLibraryItem) {
  return renderMarkdownToHtml(storyboardText(asset));
}

function assetPreviewUrl(asset: MaterialAssetLibraryItem) {
  return asset.previewUrl || asset.fileUrl || asset.remoteUrl || "";
}

function assetListImageUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || "";
}

function assetVideoPosterUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || undefined;
}

function assetOriginalImageUrl(asset: MaterialAssetLibraryItem) {
  return asset.fileUrl || asset.remoteUrl || asset.previewUrl || asset.thumbnailUrl || "";
}

function openVideoAsset(asset: MaterialAssetLibraryItem) {
  const url = assetOriginalImageUrl(asset);
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

function closePreviewDialog() {
  previewDialog.open = false;
  previewDialog.html = "";
  previewDialog.url = "";
  previewImageLoadFailed.value = false;
}

function openStoryboardPreview(asset: MaterialAssetLibraryItem) {
  previewImageLoadFailed.value = false;
  previewDialog.kind = "storyboard";
  previewDialog.title = asset.title;
  previewDialog.html = storyboardPreviewHtml(asset);
  previewDialog.url = "";
  previewDialog.open = true;
}

function openImagePreview(asset: MaterialAssetLibraryItem) {
  previewImageLoadFailed.value = false;
  previewDialog.kind = "image";
  previewDialog.title = asset.title;
  previewDialog.html = "";
  previewDialog.url = assetOriginalImageUrl(asset);
  previewDialog.open = true;
}

function isAssetChecked(assetId: string) {
  return selectedAssetIds.value.includes(assetId);
}

function toggleAssetSelection(assetId: string) {
  selectedAssetIds.value = isAssetChecked(assetId)
    ? selectedAssetIds.value.filter((id) => id !== assetId)
    : [...selectedAssetIds.value, assetId];
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
  filters.model = "";
  filters.aspectRatio = "";
  filters.clipIndex = "";
  if (activeLibraryTab.value !== "all") {
    activeLibraryTab.value = "all";
    return;
  }
  void loadAssets();
}

async function handleBatchUpload() {
  if (!selectedAssetIds.value.length) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后批量上传素材",
    message: "批量上传会更新你的素材记录，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续批量上传。");
    return;
  }
  const ids = [...selectedAssetIds.value];
  busyActionKey.value = "batch-upload";
  try {
    for (const assetId of ids) {
      const asset = assets.value.find((item) => item.id === assetId);
      if (!asset?.remoteUrl) {
        await uploadMaterialAsset(assetId);
      }
    }
    selectedAssetIds.value = [];
    await loadAssets();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "批量上传失败");
  } finally {
    busyActionKey.value = "";
  }
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
  await refreshAfterMutation(() => deleteMaterialAsset(asset.id), `delete-${asset.id}`);
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
    await router.push(`/workflows/${workflow.id}`);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "素材操作失败");
  } finally {
    busyActionKey.value = "";
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
  gap: 16px;
  min-height: 100%;
  padding: 20px 24px 32px;
  overflow-y: auto;
  background: var(--bg-base);
}

.material-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 44px;
}

.material-tabs {
  display: flex;
  gap: 2px;
  align-items: center;
  padding: 3px;
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.material-tab {
  min-height: 32px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 120ms ease;
}

.material-tab:hover { color: var(--text-primary); }
.material-tab-active {
  background: var(--bg-surface);
  color: var(--text-primary);
  box-shadow: var(--shadow-xs);
}

.material-topbar__tools {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
}

.material-search {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 160px;
  padding: 0 10px;
  color: var(--text-muted);
}

.material-search input {
  width: 100%;
  min-height: 28px;
  font-size: 12px;
  color: var(--text-primary);
}

.material-search input::placeholder { color: var(--text-muted); }

.material-toolbar-link,
.material-toolbar-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.material-toolbar-link {
  width: 32px;
  padding: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.material-toolbar-link:hover { background: var(--bg-muted); color: var(--text-primary); }
.material-toolbar-link-active { background: var(--bg-accent-soft); color: var(--accent-indigo); }
.material-toolbar-primary {
  background: var(--accent-indigo);
  color: #fff;
  text-decoration: none;
}

.material-toolbar-divider {
  width: 1px;
  height: 16px;
  background: var(--border-subtle);
}

.material-filter-drawer,
.material-batch-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr)) auto;
  gap: 8px;
  align-items: end;
  padding: 10px 0 0;
  border-top: 1px solid var(--border-subtle);
}

.material-field {
  display: grid;
  gap: 4px;
}

.material-field span {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.material-batch-bar {
  justify-content: space-between;
  grid-template-columns: none;
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}

.material-asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.material-card {
  display: grid;
  gap: 8px;
  min-height: 240px;
  padding: 8px;
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-xs);
  transition: all 160ms ease;
}

.material-card:hover {
  border-color: var(--border-default);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.material-card-selected {
  border-color: var(--accent-indigo);
}

.material-card__preview {
  height: 150px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-muted);
}

.material-card__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.material-card__body {
  display: grid;
  gap: 4px;
  padding: 0 4px;
}

.material-card__title {
  display: grid;
  gap: 2px;
}

.material-card__title strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-card__title span {
  font-size: 11px;
  color: var(--text-muted);
}

.material-card__chips {
  display: flex;
  gap: 4px;
}

.material-card__chips span {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
}

.material-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  padding: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  color: var(--text-muted);
}

.material-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
}

.material-preview-dialog {
  display: flex;
  flex-direction: column;
  width: min(900px, calc(100vw - 48px));
  max-height: min(86vh, 800px);
  border-radius: var(--radius-xl);
  background: var(--bg-surface);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.material-preview-dialog-image {
  width: min(1200px, calc(100vw - 48px));
  background: transparent;
  border: 0;
  box-shadow: none;
}

.material-preview-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.material-preview-dialog__head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.material-preview-dialog__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  color: var(--text-secondary);
  cursor: pointer;
}

.material-preview-dialog__image {
  display: block;
  max-width: 100%;
  max-height: calc(100dvh - 128px);
  border-radius: var(--radius-lg);
  object-fit: contain;
}

.material-preview-dialog__markdown {
  padding: 20px;
  overflow: auto;
  color: var(--text-secondary);
  line-height: 1.7;
}

@media (max-width: 720px) {
  .material-view { padding: 14px; }
  .material-topbar { flex-direction: column; align-items: stretch; }
  .material-filter-drawer { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .material-asset-grid { grid-template-columns: 1fr; }
}
</style>

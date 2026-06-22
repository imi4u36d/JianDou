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

      <div class="material-topbar__tools liquid-glass">
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
  gap: 20px;
  min-height: 100%;
  padding: 22px 36px 36px;
  overflow-y: auto;
  overflow-x: hidden;
  background: linear-gradient(180deg, #f6fbff 0%, #ffffff 48%, #f4f5f7 100%);
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

.material-topbar__tools {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: min(100%, 620px);
  padding: 5px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 30px rgba(27, 124, 255, 0.06);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 180px;
  padding: 0 10px;
  color: var(--text-muted);
}

.material-search > span,
.material-toolbar-link,
.material-toolbar-primary {
  display: inline-grid;
  place-items: center;
}

.material-search input {
  width: 100%;
  min-height: 32px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-strong);
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
  box-shadow: 0 10px 22px rgba(27, 124, 255, 0.16);
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

.material-filter-drawer__actions .btn-sm {
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
  box-shadow: 0 10px 26px rgba(27, 124, 255, 0.06);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-batch-bar span {
  color: var(--text-body);
  font-weight: 800;
}

.material-batch-bar .btn-secondary,
.material-batch-bar .btn-danger {
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
  box-shadow: 0 8px 20px rgba(27, 124, 255, 0.045);
  backdrop-filter: blur(40px) saturate(2.0);
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.material-card:hover,
.material-card-selected {
  border-color: rgba(27, 124, 255, 0.2);
  box-shadow: 0 14px 32px rgba(27, 124, 255, 0.085);
  transform: translateY(-1px);
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
    linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(27, 124, 255, 0.08)),
    #f3fbff;
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
  background: #f7fbff;
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
  background: #f7fbff;
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
  box-shadow: 0 8px 18px rgba(27, 124, 255, 0.08);
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
  background: rgba(237, 245, 255, 0.76);
  color: var(--accent-blue);
}

.material-menu-danger {
  color: var(--accent-danger) !important;
}

.material-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-preview-dialog {
  display: flex;
  flex-direction: column;
  width: min(980px, calc(100vw - 48px));
  max-height: min(86vh, 960px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 252, 253, 0.98));
  box-shadow:
    0 22px 56px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.material-preview-dialog-image {
  width: min(1280px, calc(100vw - 48px));
  position: relative;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.material-preview-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.material-preview-dialog__head h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 0.94rem;
  font-weight: 820;
  line-height: 1.35;
}

.material-preview-dialog__close {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 34px;
  min-height: 34px;
  padding: 0;
  border: 0;
  border-radius: 11px;
  background: #f3f8fa;
  color: var(--text-body);
  line-height: 1;
  cursor: pointer;
}

.material-preview-dialog__close :deep(svg) {
  width: 16px;
  height: 16px;
}

.material-preview-dialog__close:hover,
.material-preview-dialog__close:focus-visible {
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.material-preview-dialog__close-floating {
  position: fixed;
  right: 28px;
  top: 24px;
  z-index: 2;
  background: rgba(255, 255, 255, 0.5);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-preview-dialog__caption {
  position: fixed;
  left: 28px;
  top: 24px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  max-width: calc(100vw - 116px);
  min-height: 38px;
  overflow: hidden;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 0.88rem;
  text-overflow: ellipsis;
  white-space: nowrap;
  backdrop-filter: blur(40px) saturate(2.0);
}

.material-preview-dialog__image {
  display: block;
  max-width: 100%;
  max-height: calc(100dvh - 128px);
  border-radius: 16px;
  object-fit: contain;
  background: #eef2f4;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
}

.material-preview-dialog__fallback {
  display: grid;
  place-items: center;
  gap: 8px;
  width: min(520px, calc(100vw - 56px));
  min-height: 220px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  text-align: center;
}

.material-preview-dialog__fallback :deep(svg) {
  width: 28px;
  height: 28px;
  color: rgba(255, 255, 255, 0.84);
}

.material-preview-dialog__fallback span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.82rem;
  overflow-wrap: anywhere;
}

.material-preview-dialog__markdown {
  padding: 20px 22px 22px;
  overflow: auto;
  color: var(--text-body);
  line-height: 1.75;
}

.material-preview-dialog__markdown :deep(h1),
.material-preview-dialog__markdown :deep(h2),
.material-preview-dialog__markdown :deep(h3),
.material-preview-dialog__markdown :deep(h4) {
  margin: 0 0 12px;
  color: var(--text-strong);
  line-height: 1.35;
}

.material-preview-dialog__markdown :deep(p) {
  margin: 0 0 12px;
}

.material-preview-dialog__markdown :deep(table) {
  width: 100%;
  margin: 12px 0 22px;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.material-preview-dialog__markdown :deep(th),
.material-preview-dialog__markdown :deep(td) {
  padding: 8px 9px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  vertical-align: top;
}

.material-preview-dialog__markdown :deep(th) {
  background: #f3f6f8;
  color: var(--text-strong);
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

  .material-preview-overlay {
    padding: 16px;
  }

  .material-preview-dialog {
    width: calc(100vw - 32px);
    max-height: calc(100vh - 32px);
    border-radius: 18px;
  }

  .material-preview-dialog__head {
    padding: 16px;
  }

  .material-preview-dialog__close-floating {
    right: 16px;
    top: 16px;
    width: 38px;
    min-height: 38px;
  }

  .material-preview-dialog__caption {
    left: 16px;
    top: 18px;
    max-width: calc(100vw - 82px);
    padding: 7px 10px;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(40px) saturate(2.0);
    font-size: 0.78rem;
  }

  .material-preview-dialog__markdown {
    padding: 18px;
  }
}
</style>

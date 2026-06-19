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
        <button class="material-search-button" type="button" :disabled="loading" aria-label="搜索素材" @click="loadAssets">
          <IconSearch size="sm" />
        </button>
        <span class="material-toolbar-divider"></span>
        <button
          class="material-toolbar-link"
          type="button"
          :class="{ 'material-toolbar-link-active': advancedFiltersOpen }"
          @click="advancedFiltersOpen = !advancedFiltersOpen"
        >
          筛选
        </button>
        <button
          class="material-toolbar-link"
          type="button"
          :class="{ 'material-toolbar-link-active': batchMode }"
          @click="batchMode = !batchMode"
        >
          批量
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
        <button class="btn-primary btn-sm" type="button" :disabled="loading" @click="loadAssets">应用筛选</button>
        <button class="btn-ghost btn-sm" type="button" :disabled="loading" @click="resetFilters">清空</button>
      </div>
    </section>

    <section v-if="batchMode" class="material-batch-bar">
      <span>已选 {{ selectedAssetIds.length }}</span>
      <button class="btn-secondary btn-sm" type="button" :disabled="!selectedAssetIds.length || Boolean(busyActionKey)" @click="handleBatchUpload">
        {{ busyActionKey === "batch-upload" ? "..." : "上传" }}
      </button>
      <button class="btn-danger btn-sm" type="button" :disabled="!selectedAssetIds.length || Boolean(busyActionKey)" @click="handleBatchDelete">
        {{ busyActionKey === "batch-delete" ? "..." : "删除" }}
      </button>
    </section>

    <section v-if="loading && !assets.length" class="material-empty">
      加载中
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
            <img :src="assetVideoPosterUrl(asset)" :alt="asset.title" loading="lazy" decoding="async" fetchpriority="low" />
            <span class="material-video-play" aria-hidden="true">▶</span>
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
            <img :src="assetListImageUrl(asset)" :alt="asset.title" loading="lazy" decoding="async" fetchpriority="low" />
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
          <div class="material-card__title">
            <strong>{{ asset.title }}</strong>
            <span>{{ assetSubtitle(asset) }}</span>
          </div>
          <div class="material-card__chips">
            <span>{{ assetTypeLabel(asset.assetType) }}</span>
            <button v-if="asset.remoteUrl" type="button" :title="asset.remoteUrl" @click="copyRemoteUrl(asset.remoteUrl)">
              已上传
            </button>
            <span v-else>本地</span>
          </div>

          <div class="material-card__footer">
            <details class="material-more-menu">
              <summary aria-label="更多操作"><IconMore size="sm" /></summary>
              <div class="material-more-menu__panel">
                <button type="button" :disabled="busyActionKey === `upload-${asset.id}` || Boolean(asset.remoteUrl)" @click="handleUploadAsset(asset.id)">
                  {{ busyActionKey === `upload-${asset.id}` ? "上传中..." : (asset.remoteUrl ? "已上传" : "上传") }}
                </button>
                <button type="button" :disabled="busyActionKey === `reuse-${asset.id}`" @click="handleReuseAsset(asset.id)">
                  {{ busyActionKey === `reuse-${asset.id}` ? "复制中..." : "复用" }}
                </button>
                <RouterLink v-if="asset.workflowId" :to="`/workflows/${asset.workflowId}`">打开工作流</RouterLink>
                <a :href="asset.fileUrl" download target="_blank" rel="noopener noreferrer">下载</a>
                <button type="button" class="material-menu-danger" :disabled="busyActionKey === `delete-${asset.id}`" @click="handleDeleteAsset(asset)">
                  {{ busyActionKey === `delete-${asset.id}` ? "删除中..." : "删除" }}
                </button>
              </div>
            </details>
          </div>
        </div>
      </article>

      <div v-if="!displayedAssets.length && !hasMoreAssets" class="material-empty material-empty-inline">
        <strong>没有匹配素材</strong>
        <RouterLink to="/workspace" class="material-empty-inline__action">新建</RouterLink>
      </div>

      <div v-else-if="displayedAssets.length || hasMoreAssets" ref="loadMoreTrigger" class="material-load-more">
        <span v-if="loadingMore">加载中</span>
        <span v-else-if="hasMoreAssets">继续下滑</span>
        <span v-else>已到底</span>
      </div>
    </section>

    <div v-if="previewDialog.open" class="material-preview-overlay" role="dialog" aria-modal="true" @click.self="closePreviewDialog">
      <div class="material-preview-dialog" :class="{ 'material-preview-dialog-image': previewDialog.kind === 'image' }">
        <div v-if="previewDialog.kind !== 'image'" class="material-preview-dialog__head">
          <div>
            <h3>{{ previewDialog.title }}</h3>
          </div>
          <button type="button" class="material-preview-dialog__close" aria-label="关闭预览" @click="closePreviewDialog">×</button>
        </div>
        <button v-else type="button" class="material-preview-dialog__close material-preview-dialog__close-floating" aria-label="关闭预览" @click="closePreviewDialog">×</button>
        <strong v-if="previewDialog.kind === 'image'" class="material-preview-dialog__caption">{{ previewDialog.title }}</strong>
        <img
          v-if="previewDialog.kind === 'image'"
          class="material-preview-dialog__image"
          :src="previewDialog.url"
          :alt="previewDialog.title"
        />
        <div v-else class="material-preview-dialog__markdown" v-html="previewDialog.html"></div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteMaterialAsset, fetchMaterialAssetPage, reuseMaterialAsset, uploadMaterialAsset } from "@/features/materials";
import { requireAuth } from "@/auth/modal";
import AppSelect from "@/components/common/AppSelect.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import type { MaterialAssetLibraryItem, MaterialAssetQuery, MaterialAssetType } from "@/types";
import { renderMarkdownToHtml } from "@/utils/markdown";
import { messageApi } from "@/composables/useMessage";
import { IconImage, IconMore, IconPlus, IconSearch, IconVideo } from "@/components/icons";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const loadingMore = ref(false);
const busyActionKey = ref("");
const activeLibraryTab = ref("all");
const advancedFiltersOpen = ref(false);
const batchMode = ref(false);
const selectedAssetIds = ref<string[]>([]);

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

function assetSubtitle(asset: MaterialAssetLibraryItem) {
  const parts = [
    asset.mediaType,
    asset.originModel || asset.originProvider || "",
    asset.workflowId ? `工作流 ${asset.workflowId}` : "",
  ].filter(Boolean);
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
}

function openStoryboardPreview(asset: MaterialAssetLibraryItem) {
  previewDialog.kind = "storyboard";
  previewDialog.title = asset.title;
  previewDialog.html = storyboardPreviewHtml(asset);
  previewDialog.url = "";
  previewDialog.open = true;
}

function openImagePreview(asset: MaterialAssetLibraryItem) {
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
  if (!selectedAssetIds.value.length || !window.confirm(`确认删除选中的 ${selectedAssetIds.value.length} 个素材吗？`)) {
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
  if (!window.confirm(`确认删除素材「${asset.title}」吗？`)) {
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
  background:
    radial-gradient(circle at 88% 0%, rgba(255, 107, 95, 0.1), transparent 28%),
    radial-gradient(circle at 14% 6%, rgba(139, 212, 80, 0.16), transparent 28%),
    linear-gradient(180deg, #f6fbff 0%, #ffffff 48%, #f4fbf7 100%);
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
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.material-tab {
  min-height: 42px;
  padding: 0 22px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-body);
  font-size: 0.92rem;
  font-weight: 800;
  cursor: pointer;
}

.material-tab:hover,
.material-tab-active {
  background: #effcff;
  color: var(--accent-blue);
}

.material-topbar__tools {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: min(100%, 620px);
  padding: 5px;
  border: 1px solid rgba(0, 169, 187, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 30px rgba(27, 124, 255, 0.06);
  backdrop-filter: blur(16px);
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
.material-search-button {
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

.material-search-button,
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

.material-search-button {
  width: 36px;
  padding: 0;
  background: #effcff;
  color: var(--accent-blue);
  cursor: pointer;
}

.material-toolbar-link {
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.material-toolbar-link-active,
.material-toolbar-link:hover {
  color: var(--text-strong);
}

.material-toolbar-primary {
  gap: 6px;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
  color: #fff;
  box-shadow: 0 10px 22px rgba(27, 124, 255, 0.16);
}

.material-toolbar-divider {
  width: 1px;
  height: 18px;
  background: rgba(15, 20, 25, 0.06);
}

.material-filter-drawer,
.material-batch-bar {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  align-items: end;
  padding: 16px;
  border: 1px solid rgba(0, 169, 187, 0.1);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-soft);
}

.material-field {
  display: grid;
  gap: 8px;
}

.material-field span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.material-filter-drawer__actions,
.material-batch-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.material-batch-bar {
  justify-content: space-between;
  grid-template-columns: none;
}

.material-batch-bar span {
  color: var(--text-body);
  font-weight: 800;
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
  border: 1px solid rgba(0, 169, 187, 0.1);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-muted);
}

.material-empty-inline {
  align-content: center;
  justify-items: start;
  gap: 8px;
}

.material-empty-inline strong {
  color: var(--text-strong);
}

.material-empty-inline__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: #effcff;
  color: var(--accent-blue);
  font-size: 0.82rem;
  font-weight: 800;
  text-decoration: none;
}

.material-asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(244px, 1fr));
  gap: 18px;
  align-content: start;
}

.material-load-more {
  display: grid;
  place-items: center;
  min-height: 58px;
  border: 1px dashed rgba(15, 20, 25, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-muted);
  font-size: 0.84rem;
  font-weight: 700;
}

.material-card {
  position: relative;
  display: grid;
  gap: 12px;
  min-height: 292px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-strong);
}

.material-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(0, 169, 187, 0.08);
  box-shadow: 0 12px 28px rgba(27, 124, 255, 0.06);
  backdrop-filter: blur(12px);
}

.material-card:hover,
.material-card-selected {
  border-color: rgba(27, 124, 255, 0.26);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
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
  background: rgba(15, 20, 25, 0.18);
  box-shadow: 0 4px 14px rgba(15, 20, 25, 0.18);
}

.material-card__check input:checked + span {
  background: var(--accent-cyan);
}

.material-card__preview {
  height: 184px;
  border-radius: 14px;
  overflow: hidden;
  background: #effcff;
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
  background: #effcff;
}

.material-preview-trigger {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
  text-align: left;
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
  background: rgba(15, 20, 25, 0.72);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
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
  background: rgba(15, 20, 25, 0.08);
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
  border: 1px solid rgba(15, 20, 25, 0.08);
  vertical-align: top;
}

.material-card__body {
  display: grid;
  gap: 10px;
}

.material-card__title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.material-card__title strong {
  overflow: hidden;
  color: var(--text-strong);
  font-size: 0.96rem;
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
  min-height: 24px;
  padding: 0 8px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 999px;
  background: #f7fbff;
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.material-card__chips button {
  color: var(--accent-cyan);
  cursor: copy;
}

.material-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.material-more-menu {
  position: relative;
}

.material-more-menu summary {
  display: inline-grid;
  place-items: center;
  width: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 999px;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
  list-style: none;
}

.material-more-menu summary::-webkit-details-marker {
  display: none;
}

.material-more-menu[open] summary,
.material-more-menu summary:hover {
  background: #effcff;
  color: var(--accent-blue);
}

.material-more-menu__panel {
  position: absolute;
  right: 0;
  bottom: 38px;
  z-index: 20;
  display: grid;
  gap: 10px;
  width: 236px;
  padding: 12px;
  border: 1px solid rgba(0, 169, 187, 0.1);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.material-more-menu__panel {
  width: 170px;
  gap: 0;
  padding: 6px;
}

.material-more-menu__panel button,
.material-more-menu__panel a {
  display: flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
}

.material-more-menu__panel button:hover,
.material-more-menu__panel a:hover {
  background: #f3f6f8;
}

.material-menu-danger {
  color: var(--accent-danger) !important;
}

.material-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: rgba(15, 20, 25, 0.28);
  backdrop-filter: blur(10px);
}

.material-preview-dialog {
  display: flex;
  flex-direction: column;
  width: min(980px, calc(100vw - 48px));
  max-height: min(86vh, 960px);
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 28px 72px rgba(15, 20, 25, 0.18);
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
  padding: 20px 22px;
  border-bottom: 1px solid rgba(15, 20, 25, 0.08);
}

.material-preview-dialog__head h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.35;
}

.material-preview-dialog__close {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 36px;
  min-height: 36px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: #f3f6f8;
  color: var(--text-body);
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}

.material-preview-dialog__close-floating {
  position: fixed;
  right: 28px;
  top: 24px;
  z-index: 2;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(10px);
}

.material-preview-dialog__caption {
  position: fixed;
  left: 28px;
  top: 28px;
  z-index: 2;
  max-width: min(560px, calc(100vw - 96px));
  overflow: hidden;
  color: #fff;
  font-size: 0.9rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-preview-dialog__image {
  display: block;
  max-width: 100%;
  max-height: 86vh;
  border-radius: 18px;
  object-fit: contain;
  background: #eef2f4;
  box-shadow: 0 28px 72px rgba(15, 20, 25, 0.24);
}

.material-preview-dialog__markdown {
  padding: 24px;
  overflow: auto;
  color: var(--text-body);
  line-height: 1.75;
}

.material-preview-dialog__markdown :deep(h1),
.material-preview-dialog__markdown :deep(h2),
.material-preview-dialog__markdown :deep(h3),
.material-preview-dialog__markdown :deep(h4) {
  margin: 0 0 14px;
  color: var(--text-strong);
  line-height: 1.35;
}

.material-preview-dialog__markdown :deep(p) {
  margin: 0 0 14px;
}

.material-preview-dialog__markdown :deep(table) {
  width: 100%;
  margin: 12px 0 22px;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.material-preview-dialog__markdown :deep(th),
.material-preview-dialog__markdown :deep(td) {
  padding: 9px 10px;
  border: 1px solid rgba(15, 20, 25, 0.08);
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

  .material-filter-drawer {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .material-view {
    padding: 14px;
  }

  .material-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .material-tab {
    flex: 0 0 auto;
  }

  .material-topbar__tools,
  .material-batch-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .material-toolbar-divider {
    display: none;
  }

  .material-search {
    width: 100%;
  }

  .material-filter-drawer {
    grid-template-columns: 1fr;
  }

  .material-asset-grid {
    grid-template-columns: 1fr;
  }

  .material-card__preview {
    height: 210px;
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

  .material-preview-dialog__markdown {
    padding: 18px;
  }
}
</style>

<template>
  <Teleport to="body">
    <div v-if="open" class="material-preview-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
      <div
        class="material-preview-dialog"
        :class="{
          'material-preview-dialog-video': kind === 'image' || kind === 'video',
        }"
      >
        <div class="material-preview-dialog__head">
          <div>
            <h3>{{ title }}</h3>
          </div>
          <div class="material-preview-dialog__actions">
            <button
              v-if="downloadUrl"
              type="button"
              class="material-preview-dialog__download"
              aria-label="下载预览素材"
              @click="handleDownload"
            >
              <IconDownload size="xs" />
              <span>下载</span>
            </button>
            <button type="button" class="material-preview-dialog__close" aria-label="关闭预览" @click="emit('close')">
              <IconClose size="sm" />
            </button>
          </div>
        </div>
        <div v-if="kind === 'image' && !imageLoadFailed" class="material-preview-dialog__media">
          <img
            class="material-preview-dialog__image"
            :src="url"
            :alt="title"
            @load="markMediaReady"
            @error="handleImageError"
          />
          <div v-if="mediaLoading" class="material-preview-dialog__loading" role="status" aria-live="polite">
            <IconLoading size="md" />
            <span>加载预览中</span>
          </div>
        </div>
        <div v-else-if="kind === 'image'" class="material-preview-dialog__fallback">
          <IconImage size="lg" />
          <span>{{ title }}</span>
        </div>
        <div v-else-if="kind === 'video' && url" class="material-preview-dialog__media">
          <video
            class="material-preview-dialog__video"
            :src="url"
            controls
            playsinline
            preload="metadata"
            @loadstart="markMediaLoading"
            @loadedmetadata="markMediaReady"
            @loadeddata="markMediaReady"
            @canplay="markMediaReady"
          ></video>
          <div v-if="mediaLoading" class="material-preview-dialog__loading" role="status" aria-live="polite">
            <IconLoading size="md" />
            <span>加载预览中</span>
          </div>
        </div>
        <div v-else-if="kind === 'video'" class="material-preview-dialog__video-empty">
          <IconVideo size="lg" />
          <span>暂无可播放视频</span>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-else class="material-preview-dialog__markdown" v-html="html"></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { IconClose, IconDownload, IconImage, IconLoading, IconVideo } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, type DownloadMediaKind } from "@/utils/download";

const props = defineProps<{
  open: boolean;
  kind: "storyboard" | "image" | "video";
  title: string;
  html?: string;
  url?: string;
  imageLoadFailed?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  imageError: [];
}>();

const mediaLoadState = ref<"idle" | "loading" | "ready">("idle");
const hasPreviewMedia = computed(() => props.open && Boolean(props.url) && (props.kind === "image" || props.kind === "video"));
const mediaLoading = computed(() => hasPreviewMedia.value && mediaLoadState.value === "loading");
const downloadUrl = computed(() => String(props.url ?? "").trim());
const downloadMediaKind = computed<DownloadMediaKind>(() => props.kind === "image" || props.kind === "video" ? props.kind : "file");

function markMediaLoading() {
  if (hasPreviewMedia.value) {
    mediaLoadState.value = "loading";
  }
}

function markMediaReady() {
  if (hasPreviewMedia.value) {
    mediaLoadState.value = "ready";
  }
}

function handleImageError() {
  mediaLoadState.value = "ready";
  emit("imageError");
}

async function handleDownload() {
  try {
    const result = await downloadMedia({ url: downloadUrl.value, title: props.title, mediaType: downloadMediaKind.value });
    if (result.target === "album") {
      messageApi.success("已保存到相册");
    } else if (result.target === "share") {
      messageApi.info("已打开系统分享，可保存到相册");
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "下载失败");
  }
}

watch(
  () => [props.open, props.kind, props.url],
  () => {
    mediaLoadState.value = hasPreviewMedia.value ? "loading" : "idle";
  },
  { immediate: true },
);
</script>

<style scoped>
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
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 72px rgba(15, 23, 42, 0.16);
}

.material-preview-dialog-video {
  width: min(1120px, calc(100vw - 48px));
}

.material-preview-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.material-preview-dialog__head h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.35;
}

.material-preview-dialog__actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.material-preview-dialog__download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: #eef2ff;
  color: var(--accent-blue);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
}

.material-preview-dialog__download:hover {
  background: rgba(99, 102, 241, 0.16);
}

.material-preview-dialog__close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
}

.material-preview-dialog__close:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.material-preview-dialog__media {
  position: relative;
  overflow: hidden;
  background: #0f172a;
}

.material-preview-dialog__image,
.material-preview-dialog__video {
  display: block;
  width: 100%;
  max-height: calc(86vh - 72px);
  background: #0f172a;
}

.material-preview-dialog__image {
  object-fit: contain;
  background: #f8fafc;
}

.material-preview-dialog__video {
  object-fit: contain;
}

.material-preview-dialog__loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  min-height: 260px;
  padding: 18px;
  background: rgba(15, 23, 42, 0.62);
  color: #fff;
  text-align: center;
  backdrop-filter: blur(8px);
}

.material-preview-dialog__loading span {
  font-size: 0.84rem;
  font-weight: 700;
}

.material-preview-dialog__fallback,
.material-preview-dialog__video-empty {
  display: grid;
  place-items: center;
  gap: 10px;
  min-height: 420px;
  color: var(--text-muted);
  background: #eef2ff;
}

.material-preview-dialog__markdown {
  max-height: calc(86vh - 72px);
  padding: 22px;
  overflow: auto;
  color: var(--text-body);
  line-height: 1.68;
}

.material-preview-dialog__markdown :deep(h1),
.material-preview-dialog__markdown :deep(h2),
.material-preview-dialog__markdown :deep(h3) {
  margin: 0 0 12px;
  color: var(--text-strong);
}

.material-preview-dialog__markdown :deep(p) {
  margin: 0 0 12px;
}

.material-preview-dialog__markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.material-preview-dialog__markdown :deep(th),
.material-preview-dialog__markdown :deep(td) {
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  vertical-align: top;
}

@media (max-width: 720px) {
  .material-preview-overlay {
    padding: 12px;
  }

  .material-preview-dialog,
  .material-preview-dialog-video {
    width: calc(100vw - 24px);
    border-radius: 18px;
  }

  .material-preview-dialog__head {
    padding: 12px 14px;
  }

  .material-preview-dialog__fallback,
  .material-preview-dialog__video-empty {
    min-height: 260px;
  }
}
</style>

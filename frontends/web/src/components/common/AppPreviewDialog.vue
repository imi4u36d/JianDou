<template>
  <Teleport to="body">
    <Transition name="app-preview-dialog-fade">
      <div
        v-if="open"
        class="app-preview-dialog-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="app-preview-dialog-title"
        @click.self="emit('close')"
        @keydown.esc.stop.prevent="emit('close')"
      >
        <div class="app-preview-dialog" :class="{ 'app-preview-dialog-wide': widePanel }">
          <div class="app-preview-dialog__head">
            <div class="app-preview-dialog__title">
              <h3 id="app-preview-dialog-title">{{ title }}</h3>
              <p v-if="subtitle">{{ subtitle }}</p>
            </div>
            <div class="app-preview-dialog__actions">
              <button
                v-if="downloadUrl"
                type="button"
                class="jd-button jd-button--sm"
                aria-label="下载预览内容"
                @click="handleDownload"
              >
                <IconDownload size="xs" />
                <span>下载</span>
              </button>
              <slot name="actions"></slot>
              <button type="button" class="app-preview-dialog__close" aria-label="关闭预览" @click="emit('close')">
                <IconClose size="sm" />
              </button>
            </div>
          </div>

          <slot>
            <div v-if="kind === 'image' && !imageLoadFailed" class="app-preview-dialog__media">
              <img class="app-preview-dialog__image" :src="url" :alt="title" @load="markMediaReady" @error="handleImageError" />
              <div v-if="mediaLoading" class="app-preview-dialog__loading" role="status" aria-live="polite">
                <IconLoading size="md" />
                <span>加载预览中</span>
              </div>
            </div>
            <div v-else-if="kind === 'image'" class="app-preview-dialog__fallback">
              <IconImage size="lg" />
              <span>{{ title }}</span>
            </div>
            <div v-else-if="kind === 'video' && url" class="app-preview-dialog__media">
              <video
                class="app-preview-dialog__video"
                :src="url"
                controls
                playsinline
                preload="metadata"
                @loadstart="markMediaLoading"
                @loadedmetadata="markMediaReady"
                @loadeddata="markMediaReady"
                @canplay="markMediaReady"
              ></video>
              <div v-if="mediaLoading" class="app-preview-dialog__loading" role="status" aria-live="polite">
                <IconLoading size="md" />
                <span>加载预览中</span>
              </div>
            </div>
            <div v-else-if="kind === 'video'" class="app-preview-dialog__fallback">
              <IconVideo size="lg" />
              <span>暂无可播放视频</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-else class="app-preview-dialog__markdown" v-html="html"></div>
          </slot>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { IconClose, IconDownload, IconImage, IconLoading, IconVideo } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia, type DownloadMediaKind } from "@/utils/download";

const props = withDefaults(defineProps<{
  open: boolean;
  kind: "storyboard" | "image" | "video";
  title: string;
  subtitle?: string;
  html?: string;
  url?: string;
  imageLoadFailed?: boolean;
  showDownload?: boolean;
  wide?: boolean;
}>(), {
  subtitle: "",
  html: "",
  url: "",
  imageLoadFailed: false,
  showDownload: true,
});

const emit = defineEmits<{
  close: [];
  imageError: [];
}>();

const mediaLoadState = ref<"idle" | "loading" | "ready">("idle");
const hasPreviewMedia = computed(() => props.open && Boolean(props.url) && (props.kind === "image" || props.kind === "video"));
const mediaLoading = computed(() => hasPreviewMedia.value && mediaLoadState.value === "loading");
const downloadUrl = computed(() => props.showDownload ? String(props.url ?? "").trim() : "");
const downloadMediaKind = computed<DownloadMediaKind>(() => props.kind === "image" || props.kind === "video" ? props.kind : "file");
const widePanel = computed(() => props.wide ?? (props.kind === "image" || props.kind === "video"));

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
.app-preview-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1450;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 10, 20, 0.25);
  backdrop-filter: blur(40px) saturate(2);
}

.app-preview-dialog {
  display: flex;
  flex-direction: column;
  width: min(980px, calc(100vw - 48px));
  max-height: min(86vh, 960px);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(40px) saturate(1.8);
  -webkit-backdrop-filter: blur(40px) saturate(1.8);
}

.app-preview-dialog-wide {
  width: min(1120px, calc(100vw - 48px));
}

.app-preview-dialog__head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.app-preview-dialog__title {
  min-width: 0;
}

.app-preview-dialog__title h3,
.app-preview-dialog__title p {
  margin: 0;
}

.app-preview-dialog__title h3 {
  color: var(--text-strong);
  font-size: 1rem;
  line-height: 1.35;
}

.app-preview-dialog__title p {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.78rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.app-preview-dialog__actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.app-preview-dialog__close {
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

.app-preview-dialog__close:hover {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.app-preview-dialog__media {
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  background: transparent;
}

.app-preview-dialog__image,
.app-preview-dialog__video {
  display: block;
  width: 100%;
  max-height: calc(86vh - 72px);
  object-fit: contain;
}

.app-preview-dialog__image {
  height: auto;
  background: transparent;
}

.app-preview-dialog__video {
  background: #0f172a;
}

.app-preview-dialog__loading {
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

.app-preview-dialog__loading span {
  font-size: 0.84rem;
  font-weight: 700;
}

.app-preview-dialog__fallback {
  display: grid;
  place-items: center;
  gap: 10px;
  min-height: 420px;
  color: var(--text-muted);
  background: #eef2ff;
}

.app-preview-dialog__markdown {
  max-height: calc(86vh - 72px);
  padding: 22px;
  overflow: auto;
  color: var(--text-body);
  line-height: 1.68;
}

.app-preview-dialog__markdown :deep(h1),
.app-preview-dialog__markdown :deep(h2),
.app-preview-dialog__markdown :deep(h3) {
  margin: 0 0 12px;
  color: var(--text-strong);
}

.app-preview-dialog__markdown :deep(p) {
  margin: 0 0 12px;
}

.app-preview-dialog__markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.app-preview-dialog__markdown :deep(th),
.app-preview-dialog__markdown :deep(td) {
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  vertical-align: top;
}

.app-preview-dialog-fade-enter-active,
.app-preview-dialog-fade-leave-active {
  transition: opacity 160ms ease;
}

.app-preview-dialog-fade-enter-active .app-preview-dialog,
.app-preview-dialog-fade-leave-active .app-preview-dialog {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-preview-dialog-fade-enter-from,
.app-preview-dialog-fade-leave-to {
  opacity: 0;
}

.app-preview-dialog-fade-enter-from .app-preview-dialog,
.app-preview-dialog-fade-leave-to .app-preview-dialog {
  transform: translateY(8px) scale(0.985);
}

@media (max-width: 720px) {
  .app-preview-dialog-overlay {
    padding: 12px;
  }

  .app-preview-dialog,
  .app-preview-dialog-wide {
    width: calc(100vw - 24px);
  }

  .app-preview-dialog__head {
    align-items: flex-start;
    flex-direction: column;
    padding: 12px 14px;
  }

  .app-preview-dialog__actions {
    width: 100%;
    justify-content: flex-end;
  }

  .app-preview-dialog__fallback {
    min-height: 260px;
  }
}
</style>

<template>
  <section class="text-generate-view space-y-6">
    <PageHeader
      eyebrow="Generative Studio"
      title="文本生成图片 / 视频"
      description="输入一句描述，选择媒体类型与策略版本，直接产出可预览素材。"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="surface-chip">版本 {{ versionRangeLabel }}</span>
        <span class="surface-chip">{{ optionsSourceLabel }}</span>
      </div>
    </PageHeader>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
      <form class="surface-panel surface-panel-warm grid gap-5 p-6" @submit.prevent="handleSubmit">
        <div v-if="optionsLoading" class="surface-tile p-4 text-sm text-slate-600">
          正在加载版本与可选参数...
        </div>
        <div v-else-if="optionsError" class="surface-tile border border-amber-200 bg-amber-50/85 p-4 text-sm text-amber-800">
          {{ optionsError }}
        </div>

        <label class="grid gap-2 text-sm text-slate-700">
          提示词
          <textarea
            v-model="form.prompt"
            rows="5"
            class="field-textarea"
            placeholder="例如：暮色里的未来都市，霓虹与薄雾交错，电影感广角镜头。"
          ></textarea>
        </label>

        <div class="surface-tile grid gap-4 p-4">
          <div class="grid gap-2 text-sm text-slate-700">
            <p>媒体类型</p>
            <div class="media-kind-grid">
              <button
                type="button"
                class="media-kind-btn"
                :class="form.mediaKind === 'image' ? 'media-kind-btn-active' : ''"
                @click="form.mediaKind = 'image'"
              >
                图片
              </button>
              <button
                type="button"
                class="media-kind-btn"
                :class="form.mediaKind === 'video' ? 'media-kind-btn-active' : ''"
                @click="form.mediaKind = 'video'"
              >
                视频
              </button>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="grid gap-2 text-sm text-slate-700">
              策略版本
              <select v-model.number="form.version" class="field-select">
                <option v-for="item in versionOptions" :key="item.version" :value="item.version">{{ item.label }}</option>
              </select>
              <p class="text-xs text-slate-500">这里的 v1-v10 只代表提示词策略版本，不是底层模型版本。</p>
            </label>
            <label class="grid gap-2 text-sm text-slate-700">
              风格预设（可选）
              <select v-model="form.stylePreset" class="field-select">
                <option value="">不指定</option>
                <option v-for="preset in availableStylePresets" :key="preset.key" :value="preset.key">{{ preset.label }}</option>
              </select>
              <p v-if="selectedStylePreset?.description" class="text-xs text-slate-500">{{ selectedStylePreset.description }}</p>
            </label>
          </div>

          <div v-if="form.mediaKind === 'image'" class="grid gap-2 text-sm text-slate-700">
            <label class="grid gap-2">
              图片尺寸
              <select v-model="form.imageSize" class="field-select">
                <option v-for="size in options.imageSizes" :key="size.value" :value="size.value">{{ size.label }}</option>
              </select>
            </label>
          </div>

          <div v-else class="grid gap-4 text-sm text-slate-700">
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="grid gap-2">
                视频模型
                <select v-model="form.providerModel" class="field-select">
                  <option v-for="model in availableVideoModels" :key="model.value" :value="model.value">
                    {{ model.label }}{{ model.description ? ` · ${model.description}` : "" }}
                  </option>
                </select>
                <p v-if="selectedVideoModel?.description" class="text-xs text-slate-500">{{ selectedVideoModel.description }}</p>
              </label>
              <label class="grid gap-2">
                视频分辨率
                <select v-model="form.videoSize" class="field-select">
                  <option v-for="size in availableVideoSizes" :key="size.value" :value="size.value">{{ size.label }}</option>
                </select>
              </label>
            </div>
            <label class="grid gap-2">
              视频时长
              <select v-model.number="form.videoDurationSeconds" class="field-select">
                <option v-for="duration in availableVideoDurations" :key="duration.value" :value="duration.value">
                  {{ duration.label }}
                </option>
              </select>
            </label>
          </div>
        </div>

        <div v-if="submitError" class="surface-tile border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
          {{ submitError }}
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button type="submit" class="btn-primary" :disabled="!canSubmit">
            {{ submitButtonLabel }}
          </button>
          <p class="text-sm text-slate-600">{{ statusLabel }}</p>
        </div>
      </form>

      <aside class="grid gap-4">
        <div class="surface-tile p-4">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">当前参数</p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
            <span class="surface-chip">{{ form.mediaKind === "image" ? "图片生成" : "视频生成" }}</span>
            <span class="surface-chip">策略 v{{ form.version }}</span>
            <span class="surface-chip">{{ form.stylePreset || "无风格预设" }}</span>
            <span v-if="form.mediaKind === 'video'" class="surface-chip">{{ selectedVideoModel?.label || form.providerModel || "未选视频模型" }}</span>
            <span v-if="form.mediaKind === 'video'" class="surface-chip">{{ form.videoSize }}</span>
            <span class="surface-chip">{{ form.mediaKind === "image" ? form.imageSize : `${form.videoDurationSeconds} 秒` }}</span>
          </div>
        </div>

        <section class="surface-panel p-5">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">预览</p>
              <h3 class="mt-2 text-lg font-semibold text-slate-900">生成结果</h3>
            </div>
            <span v-if="result" class="surface-chip text-xs">{{ result.mediaKind === "image" ? "Image" : "Video" }}</span>
          </div>

          <div v-if="submitting" class="surface-tile mt-4 p-8 text-center text-sm text-slate-600">
            正在生成素材，请稍候...
          </div>

          <div v-else-if="result" class="mt-4 grid gap-4">
            <div class="preview-frame">
              <img
                v-if="!isVideoResult"
                :src="resolvedOutputUrl"
                alt="generated image"
                class="preview-media"
              />
              <video
                v-else
                :src="resolvedOutputUrl"
                :poster="resolvedThumbnailUrl || undefined"
                controls
                playsinline
                preload="metadata"
                class="preview-media"
              ></video>
            </div>

            <dl class="metadata-grid">
              <div v-for="item in metadataItems" :key="item.label" class="metadata-item">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value }}</dd>
              </div>
            </dl>

            <div v-if="modelInfoItems.length" class="surface-tile p-4">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">模型信息</p>
              <dl class="metadata-grid mt-3">
                <div v-for="item in modelInfoItems" :key="item.label" class="metadata-item">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </div>
              </dl>
            </div>

            <div v-if="callChainItems.length" class="surface-tile p-4">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">调用日志链路</p>
              <ol class="call-chain-list mt-3">
                <li v-for="(item, index) in callChainItems" :key="`${item.timestamp}-${index}`" class="call-chain-item">
                  <div class="call-chain-head">
                    <span>{{ item.timestampLabel }}</span>
                    <span :class="['call-chain-status', item.statusClass]">{{ item.statusLabel }}</span>
                  </div>
                  <p class="call-chain-main">{{ item.stage }} / {{ item.event }}</p>
                  <p class="call-chain-message">{{ item.message }}</p>
                  <pre v-if="item.detailsText" class="call-chain-details">{{ item.detailsText }}</pre>
                </li>
              </ol>
            </div>

            <div v-if="metadataJson" class="surface-tile p-4">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Metadata JSON</p>
              <pre class="metadata-json mt-3">{{ metadataJson }}</pre>
            </div>
          </div>

          <div v-else class="surface-tile mt-4 border-dashed p-8 text-center text-sm text-slate-500">
            提交后会在这里展示图片或视频结果。
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { fetchGenerationOptions, generateMediaFromText } from "@/api/generation";
import { getRuntimeConfig } from "@/api/runtime-config";
import PageHeader from "@/components/PageHeader.vue";
import type {
  GenerateMediaRequest,
  GenerateMediaResponse,
  GenerationMediaKind,
  GenerationOptionsResponse,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
} from "@/types";
import { resolveRuntimeUrl } from "@/utils/url";

const FALLBACK_VIDEO_MODELS: GenerationVideoModelInfo[] = [
  { value: "wan2.6-i2v", label: "wan2.6-i2v", isDefault: true },
  { value: "wan2.6-t2v", label: "wan2.6-t2v" },
  { value: "wan2.6-t2v-us", label: "wan2.6-t2v-us" },
  { value: "wan2.5-t2v-preview", label: "wan2.5-t2v-preview" },
  { value: "wan2.2-t2v-plus", label: "wan2.2-t2v-plus" },
  { value: "wanx2.1-t2v-turbo", label: "wanx2.1-t2v-turbo" },
  { value: "wanx2.1-t2v-plus", label: "wanx2.1-t2v-plus" },
];
const FALLBACK_VIDEO_SIZES: GenerationVideoSizeOption[] = [
  { value: "1080x1920", label: "1080 × 1920", width: 1080, height: 1920 },
  { value: "1920x1080", label: "1920 × 1080", width: 1920, height: 1080 },
  { value: "1280x720", label: "1280 × 720", width: 1280, height: 720 },
];
const FALLBACK_VIDEO_DURATIONS: GenerationVideoDurationOption[] = [
  { value: 4, label: "4 秒" },
  { value: 6, label: "6 秒" },
  { value: 8, label: "8 秒" },
];
const FALLBACK_OPTIONS: GenerationOptionsResponse = {
  versions: Array.from({ length: 10 }, (_, index) => index + 1),
  defaultVersion: 1,
  stylePresets: [],
  imageSizes: [
    { value: "768x768", label: "768 × 768" },
    { value: "1024x1024", label: "1024 × 1024" },
    { value: "1365x768", label: "1365 × 768" },
  ],
  videoModels: [...FALLBACK_VIDEO_MODELS],
  defaultVideoModel: "wan2.6-i2v",
  videoSizes: [...FALLBACK_VIDEO_SIZES],
  videoDurations: [...FALLBACK_VIDEO_DURATIONS],
  defaultStylePreset: null,
  defaultImageSize: "1024x1024",
  defaultVideoSize: "1080x1920",
  defaultVideoDurationSeconds: 6,
};

function cloneFallbackOptions(): GenerationOptionsResponse {
  return {
    ...FALLBACK_OPTIONS,
    versions: [...FALLBACK_OPTIONS.versions],
    stylePresets: [...FALLBACK_OPTIONS.stylePresets],
    imageSizes: [...FALLBACK_OPTIONS.imageSizes],
    videoModels: [...FALLBACK_OPTIONS.videoModels],
    videoSizes: [...FALLBACK_OPTIONS.videoSizes],
    videoDurations: [...FALLBACK_OPTIONS.videoDurations],
  };
}

function normalizeGenerationOptions(raw: GenerationOptionsResponse | null | undefined): GenerationOptionsResponse {
  if (!raw) {
    return cloneFallbackOptions();
  }
  return {
    versions: raw.versions?.length ? [...raw.versions] : [...FALLBACK_OPTIONS.versions],
    versionDetails: raw.versionDetails?.length ? [...raw.versionDetails] : undefined,
    defaultVersion: raw.defaultVersion ?? FALLBACK_OPTIONS.defaultVersion,
    stylePresets: raw.stylePresets?.length ? [...raw.stylePresets] : [],
    imageSizes: raw.imageSizes?.length ? [...raw.imageSizes] : [...FALLBACK_OPTIONS.imageSizes],
    videoModels: raw.videoModels?.length ? [...raw.videoModels] : [...FALLBACK_OPTIONS.videoModels],
    defaultVideoModel: raw.defaultVideoModel ?? FALLBACK_OPTIONS.defaultVideoModel,
    videoSizes: raw.videoSizes?.length ? [...raw.videoSizes] : [...FALLBACK_OPTIONS.videoSizes],
    videoDurations: raw.videoDurations?.length ? [...raw.videoDurations] : [...FALLBACK_OPTIONS.videoDurations],
    defaultStylePreset: raw.defaultStylePreset ?? null,
    defaultImageSize: raw.defaultImageSize ?? FALLBACK_OPTIONS.defaultImageSize,
    defaultVideoSize: raw.defaultVideoSize ?? FALLBACK_OPTIONS.defaultVideoSize,
    defaultVideoDurationSeconds: raw.defaultVideoDurationSeconds ?? FALLBACK_OPTIONS.defaultVideoDurationSeconds,
  };
}

const options = ref<GenerationOptionsResponse>(cloneFallbackOptions());
const optionsLoading = ref(true);
const optionsError = ref("");
const optionsFromApi = ref(true);
const submitting = ref(false);
const submitError = ref("");
const result = ref<GenerateMediaResponse | null>(null);

const form = reactive<{
  prompt: string;
  mediaKind: GenerationMediaKind;
  version: number;
  stylePreset: string;
  providerModel: string;
  imageSize: string;
  videoSize: string;
  videoDurationSeconds: number;
}>({
  prompt: "",
  mediaKind: "image",
  version: options.value.defaultVersion ?? options.value.versions[0] ?? 1,
  stylePreset: "",
  providerModel: options.value.defaultVideoModel ?? options.value.videoModels[0]?.value ?? "",
  imageSize: options.value.defaultImageSize ?? options.value.imageSizes[0]?.value ?? "",
  videoSize: options.value.defaultVideoSize ?? options.value.videoSizes[0]?.value ?? "",
  videoDurationSeconds: options.value.defaultVideoDurationSeconds ?? options.value.videoDurations[0]?.value ?? 6,
});

const availableStylePresets = computed(() =>
  options.value.stylePresets.filter((item) => !item.mediaKinds?.length || item.mediaKinds.includes(form.mediaKind))
);

const availableVideoModels = computed(() => options.value.videoModels.length ? options.value.videoModels : FALLBACK_VIDEO_MODELS);

function filterByVideoModel<T extends { supportedModels?: string[] }>(items: T[], model: string): T[] {
  const canonicalModel = model.trim();
  if (!canonicalModel) {
    return items;
  }
  const filtered = items.filter((item) => !item.supportedModels?.length || item.supportedModels.includes(canonicalModel));
  return filtered.length ? filtered : items;
}

const availableVideoSizes = computed(() => filterByVideoModel(options.value.videoSizes.length ? options.value.videoSizes : FALLBACK_VIDEO_SIZES, form.providerModel));

const availableVideoDurations = computed(() =>
  filterByVideoModel(options.value.videoDurations.length ? options.value.videoDurations : FALLBACK_VIDEO_DURATIONS, form.providerModel)
);

const versionOptions = computed(() =>
  options.value.versions.map((version) => {
    const detail = options.value.versionDetails?.find((item) => item.version === version);
    if (!detail) {
      return {
        version,
        label: `v${version}`,
      };
    }
    return {
      version,
      label: `v${version} · ${detail.label}`,
    };
  })
);

const selectedStylePreset = computed(() => availableStylePresets.value.find((item) => item.key === form.stylePreset) ?? null);

const isVideoResult = computed(() => {
  if (!result.value) {
    return false;
  }
  if (result.value.mediaKind === "video") {
    return true;
  }
  return (result.value.mimeType || "").toLowerCase().startsWith("video/");
});

const selectedVideoModel = computed(() => availableVideoModels.value.find((item) => item.value === form.providerModel) ?? null);

const versionRangeLabel = computed(() => {
  const versions = options.value.versions;
  if (!versions.length) {
    return "v1-v10";
  }
  const min = versions[0];
  const max = versions[versions.length - 1];
  return min === max ? `v${min}` : `v${min}-v${max}`;
});

const optionsSourceLabel = computed(() => (optionsFromApi.value ? "来自 API" : "API 不可用"));

const canSubmit = computed(() => {
  return Boolean(form.prompt.trim()) && !submitting.value && !optionsLoading.value && !optionsError.value && optionsFromApi.value;
});

const submitButtonLabel = computed(() => (submitting.value ? "生成中..." : "开始生成"));

const statusLabel = computed(() => {
  if (submitting.value) {
    return "任务提交后正在等待结果返回。";
  }
  if (result.value) {
    return `最近生成：${result.value.mediaKind === "image" ? "图片" : "视频"} · v${result.value.version}`;
  }
  return "填写参数后提交即可预览生成结果。";
});

const resolvedOutputUrl = computed(() => {
  if (!result.value) {
    return "";
  }
  return resolveRuntimeUrl(result.value.outputUrl, getRuntimeConfig().storageBaseUrl);
});

const resolvedThumbnailUrl = computed(() => {
  if (!result.value?.thumbnailUrl) {
    return "";
  }
  return resolveRuntimeUrl(result.value.thumbnailUrl, getRuntimeConfig().storageBaseUrl);
});

const metadataItems = computed(() => {
  if (!result.value) {
    return [];
  }
  const entries: Array<{ label: string; value: string }> = [];
  entries.push({ label: "ID", value: result.value.id });
  entries.push({ label: "策略版本", value: `v${result.value.version}` });
  entries.push({ label: "风格预设", value: result.value.stylePreset || "未指定" });
  entries.push({ label: "MIME", value: result.value.mimeType || "未知" });
  if (result.value.width && result.value.height) {
    entries.push({ label: "分辨率", value: `${result.value.width} × ${result.value.height}` });
  }
  if (typeof result.value.durationSeconds === "number") {
    entries.push({ label: "时长", value: `${result.value.durationSeconds.toFixed(1)} 秒` });
  }
  if (result.value.createdAt) {
    entries.push({ label: "创建时间", value: new Date(result.value.createdAt).toLocaleString() });
  }
  return entries;
});

const modelInfoItems = computed(() => {
  if (!result.value?.modelInfo) {
    return [];
  }
  const info = result.value.modelInfo;
  const entries: Array<{ label: string; value: string }> = [];
  if (info.provider) {
    entries.push({ label: "服务商", value: info.provider });
  }
  if (info.providerModel || (result.value.mediaKind === "video" && info.modelName)) {
    entries.push({ label: "视频模型", value: info.providerModel || info.modelName || "未指定" });
  } else if (info.modelName) {
    entries.push({ label: "底层模型", value: info.modelName });
  }
  if (typeof info.strategyVersion === "number") {
    entries.push({
      label: "策略版本",
      value: `v${info.strategyVersion}${info.strategyVersionLabel ? ` · ${info.strategyVersionLabel}` : ""}`,
    });
  } else if (info.strategyVersionLabel) {
    entries.push({ label: "策略版本", value: info.strategyVersionLabel });
  }
  if (info.endpointHost) {
    entries.push({ label: "模型网关", value: info.endpointHost });
  }
  if (typeof info.temperature === "number") {
    entries.push({ label: "Temperature", value: `${info.temperature}` });
  }
  if (typeof info.maxTokens === "number") {
    entries.push({ label: "Max Tokens", value: `${info.maxTokens}` });
  }
  if (typeof info.timeoutSeconds === "number") {
    entries.push({ label: "超时", value: `${info.timeoutSeconds} 秒` });
  }
  return entries;
});

const callChainItems = computed(() => {
  if (!result.value?.callChain?.length) {
    return [];
  }
  return result.value.callChain.map((item) => {
    const dateValue = new Date(item.timestamp);
    const timestampLabel = Number.isNaN(dateValue.getTime())
      ? item.timestamp
      : dateValue.toLocaleString();
    const normalizedStatus = item.status.toLowerCase();
    const statusLabel =
      normalizedStatus === "ok"
        ? "成功"
        : normalizedStatus === "error"
          ? "失败"
          : normalizedStatus === "retry"
            ? "重试"
            : "信息";
    const statusClass =
      normalizedStatus === "ok"
        ? "call-chain-status-ok"
        : normalizedStatus === "error"
          ? "call-chain-status-error"
          : normalizedStatus === "retry"
            ? "call-chain-status-retry"
            : "call-chain-status-info";
    const detailsText =
      item.details && Object.keys(item.details).length > 0 ? JSON.stringify(item.details, null, 2) : "";
    return {
      ...item,
      timestampLabel,
      statusLabel,
      statusClass,
      detailsText,
    };
  });
});

const metadataJson = computed(() => {
  if (!result.value?.metadata || !Object.keys(result.value.metadata).length) {
    return "";
  }
  return JSON.stringify(result.value.metadata, null, 2);
});

function syncVersion() {
  const available = options.value.versions;
  if (!available.length) {
    form.version = 1;
    return;
  }
  if (!available.includes(form.version)) {
    form.version = options.value.defaultVersion && available.includes(options.value.defaultVersion)
      ? options.value.defaultVersion
      : available[0];
  }
}

function syncStylePreset() {
  const keys = availableStylePresets.value.map((item) => item.key);
  if (form.stylePreset && !keys.includes(form.stylePreset)) {
    form.stylePreset = "";
  }
  if (!form.stylePreset && options.value.defaultStylePreset && keys.includes(options.value.defaultStylePreset)) {
    form.stylePreset = options.value.defaultStylePreset;
  }
}

function syncMediaOptions() {
  if (form.mediaKind === "image") {
    const sizeValues = options.value.imageSizes.map((item) => item.value);
    if (!sizeValues.includes(form.imageSize)) {
      form.imageSize = options.value.defaultImageSize && sizeValues.includes(options.value.defaultImageSize)
        ? options.value.defaultImageSize
        : sizeValues[0] || "";
    }
    return;
  }
  const modelValues = availableVideoModels.value.map((item) => item.value);
  if (!modelValues.includes(form.providerModel)) {
    form.providerModel =
      (options.value.defaultVideoModel && modelValues.includes(options.value.defaultVideoModel) ? options.value.defaultVideoModel : "") ||
      modelValues[0] ||
      "";
  }
  const sizeOptions = filterByVideoModel(
    options.value.videoSizes.length ? options.value.videoSizes : FALLBACK_VIDEO_SIZES,
    form.providerModel
  );
  const sizeValues = sizeOptions.map((item) => item.value);
  if (!sizeValues.includes(form.videoSize)) {
    form.videoSize =
      (options.value.defaultVideoSize && sizeValues.includes(options.value.defaultVideoSize) ? options.value.defaultVideoSize : "") ||
      sizeValues[0] ||
      "";
  }
  const durationOptions = filterByVideoModel(
    options.value.videoDurations.length ? options.value.videoDurations : FALLBACK_VIDEO_DURATIONS,
    form.providerModel
  );
  const durationValues = durationOptions.map((item) => item.value);
  if (!durationValues.includes(form.videoDurationSeconds)) {
    const defaultDuration = options.value.defaultVideoDurationSeconds ?? 0;
    form.videoDurationSeconds = durationValues.includes(defaultDuration)
      ? defaultDuration
      : durationValues[0] || 6;
  }
}

function syncFormWithOptions() {
  syncVersion();
  syncStylePreset();
  syncMediaOptions();
}

watch(availableStylePresets, () => syncStylePreset());
watch(() => form.mediaKind, () => syncFormWithOptions());
watch(() => form.providerModel, () => {
  if (form.mediaKind === "video") {
    syncMediaOptions();
  }
});

async function loadGenerationOptions() {
  optionsLoading.value = true;
  optionsError.value = "";
  try {
    options.value = normalizeGenerationOptions(await fetchGenerationOptions());
    optionsFromApi.value = true;
  } catch (error) {
    optionsError.value = error instanceof Error ? error.message : "加载生成配置失败";
    optionsFromApi.value = false;
  } finally {
    syncFormWithOptions();
    optionsLoading.value = false;
  }
}

async function handleSubmit() {
  if (!canSubmit.value) {
    return;
  }
  submitError.value = "";
  submitting.value = true;
  try {
    const payload: GenerateMediaRequest = {
      prompt: form.prompt.trim(),
      mediaKind: form.mediaKind,
      version: form.version,
      stylePreset: form.stylePreset || null,
    };
    if (form.mediaKind === "image") {
      payload.imageSize = form.imageSize;
    } else {
      payload.providerModel = form.providerModel;
      payload.videoSize = form.videoSize;
      payload.videoDurationSeconds = form.videoDurationSeconds;
    }
    result.value = await generateMediaFromText(payload);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "提交生成失败";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  await loadGenerationOptions();
});
</script>

<style scoped>
.media-kind-grid {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.media-kind-btn {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.34);
  background: rgba(255, 255, 255, 0.62);
  color: #334155;
  padding: 0.6rem 0.9rem;
  text-align: center;
  font-weight: 600;
  transition: all 160ms ease;
}

.media-kind-btn:hover {
  border-color: rgba(59, 130, 246, 0.42);
  color: #0f172a;
}

.media-kind-btn-active {
  border-color: rgba(59, 130, 246, 0.5);
  background: linear-gradient(180deg, rgba(236, 244, 255, 0.92), rgba(229, 240, 255, 0.7));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 10px 22px rgba(102, 134, 180, 0.14);
  color: #1d4ed8;
}

.preview-frame {
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background:
    radial-gradient(circle at top right, rgba(148, 197, 255, 0.18), transparent 38%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(248, 250, 252, 0.72));
  padding: 0.75rem;
}

.preview-media {
  display: block;
  width: 100%;
  max-height: min(56vh, 540px);
  border-radius: 18px;
  object-fit: contain;
  background: rgba(15, 23, 42, 0.95);
}

.metadata-grid {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
}

.metadata-item {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.64);
  padding: 0.7rem 0.8rem;
}

.metadata-item dt {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.metadata-item dd {
  margin-top: 0.35rem;
  font-size: 0.84rem;
  color: #0f172a;
  word-break: break-word;
}

.metadata-json {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.84);
  padding: 0.75rem;
  color: #1e293b;
  font-size: 0.75rem;
  line-height: 1.5;
}

.call-chain-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.65rem;
}

.call-chain-item {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.7rem 0.8rem;
}

.call-chain-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  font-size: 0.72rem;
  color: #64748b;
}

.call-chain-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.14rem 0.46rem;
  font-weight: 600;
}

.call-chain-status-ok {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.call-chain-status-error {
  background: rgba(244, 63, 94, 0.12);
  color: #be123c;
}

.call-chain-status-retry {
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
}

.call-chain-status-info {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.call-chain-main {
  margin-top: 0.36rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #0f172a;
}

.call-chain-message {
  margin-top: 0.24rem;
  font-size: 0.78rem;
  color: #334155;
}

.call-chain-details {
  margin-top: 0.42rem;
  max-height: 164px;
  overflow: auto;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(248, 250, 252, 0.92);
  padding: 0.56rem;
  font-size: 0.72rem;
  line-height: 1.45;
  color: #1f2937;
}
</style>

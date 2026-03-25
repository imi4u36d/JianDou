<template>
  <section class="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
    <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.88),rgba(8,11,24,0.74))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.34)]">
      <PageHeader
        eyebrow="Create"
        title="新建剪辑任务"
        description="选择一个预设模板或从历史任务复制参数，再上传源视频生成新的投放素材。"
      />

      <div class="mb-6 grid gap-3 md:grid-cols-2">
        <button
          v-for="preset in visiblePresets"
          :key="preset.key"
          type="button"
          class="rounded-[24px] border p-4 text-left transition duration-200"
          :class="selectedPresetKey === preset.key ? 'border-rose-300/40 bg-rose-500/12 shadow-[0_0_0_1px_rgba(225,29,72,0.12)]' : 'border-white/10 bg-white/[0.04] hover:border-rose-300/30 hover:bg-white/10'"
          @click="applyPreset(preset)"
        >
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.28em] text-slate-400">{{ presetBadge(preset) }}</p>
              <h3 class="mt-2 text-base font-semibold text-white">{{ preset.name }}</h3>
            </div>
            <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] font-semibold text-slate-200">{{ platformLabel(preset.platform) }}</span>
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-300">{{ preset.description }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
            <span class="rounded-full bg-white/[0.04] px-3 py-1">{{ preset.aspectRatio }}</span>
            <span class="rounded-full bg-white/[0.04] px-3 py-1">{{ preset.minDurationSeconds }}-{{ preset.maxDurationSeconds }}s</span>
            <span class="rounded-full bg-white/[0.04] px-3 py-1">{{ preset.outputCount }} 条</span>
          </div>
        </button>
      </div>

      <form class="grid gap-5" @submit.prevent="submitTask">
        <label class="grid gap-2 text-sm text-slate-200">
          任务标题
          <input v-model="form.title" required class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none ring-0 transition duration-200 placeholder:text-slate-500 focus:border-rose-300/60" placeholder="例如：第 12 集高能反转投放版" />
        </label>

        <label class="grid gap-2 text-sm text-slate-200">
          原始视频
          <input
            type="file"
            accept="video/*"
            required
            @change="onFileChange"
            class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white file:mr-4 file:rounded-full file:border-0 file:bg-rose-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-rose-400"
          />
        </label>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            投放平台
            <select v-model="form.platform" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="douyin">抖音</option>
              <option value="kuaishou">快手</option>
              <option value="xiaohongshu">小红书</option>
              <option value="wechat">视频号</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            画幅比例
            <select v-model="form.aspectRatio" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="9:16">竖版 9:16</option>
              <option value="16:9">横版 16:9</option>
            </select>
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <label class="grid gap-2 text-sm text-slate-200">
            最小时长（秒）
            <input v-model.number="form.minDurationSeconds" type="number" min="5" max="120" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            最大时长（秒）
            <input v-model.number="form.maxDurationSeconds" type="number" min="5" max="120" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            产出数量
            <input v-model.number="form.outputCount" type="number" min="1" max="10" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60" />
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            片头模板
            <select v-model="form.introTemplate" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="none">无</option>
              <option value="hook">Hook</option>
              <option value="cinematic">Cinematic</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            片尾模板
            <select v-model="form.outroTemplate" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="none">无</option>
              <option value="brand">Brand</option>
              <option value="call_to_action">Call To Action</option>
            </select>
          </label>
        </div>

        <label class="grid gap-2 text-sm text-slate-200">
          创意补充
          <textarea v-model="form.creativePrompt" rows="4" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 placeholder:text-slate-500 focus:border-rose-300/60" placeholder="例如：优先保留冲突点、反转点，节奏更快，适合首刷拉停。"></textarea>
        </label>

        <label class="grid gap-2 text-sm text-slate-200">
          字幕 / 台词文本（可选）
          <input ref="transcriptFileInput" type="file" accept=".srt,.vtt,.txt" class="hidden" @change="handleTranscriptFileChange" />
          <textarea
            v-model="form.transcriptText"
            rows="8"
            class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 font-mono text-sm text-white transition duration-200 placeholder:text-slate-500 focus:border-rose-300/60"
            placeholder="建议粘贴 SRT / VTT 或带时间戳台词。没有时间戳时，模型只能优化语义，不能稳定决定切点。"
          ></textarea>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-100 transition duration-200 hover:border-rose-300/40 hover:bg-white/10"
              @click="transcriptFileInput?.click()"
            >
              导入字幕文件
            </button>
            <span class="text-xs text-slate-400">{{ transcriptStats.summary }}</span>
          </div>
        </label>

        <div class="flex flex-wrap items-center gap-4">
          <button
            :disabled="submitting"
            class="rounded-full bg-rose-500 px-5 py-3 text-sm font-medium text-white transition duration-200 hover:bg-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
          >
            {{ submitting ? "提交中..." : "开始生成" }}
          </button>
          <p class="text-sm text-slate-300">{{ statusText }}</p>
        </div>
      </form>
    </div>

    <aside class="space-y-4">
      <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.86),rgba(8,11,24,0.7))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
        <PageHeader
          eyebrow="Preset"
          title="参数摘要"
          description="当前模板、文件状态和提交参数会同步显示在这里，减少来回确认。"
        />

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">当前模板</p>
            <p class="mt-2 text-sm font-semibold text-white">{{ activePreset?.name || "自定义" }}</p>
            <p class="mt-2 text-xs leading-5 text-slate-400">{{ activePreset?.description || "手动配置任务参数" }}</p>
          </div>
          <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">来源</p>
            <p class="mt-2 text-sm font-semibold text-white">{{ sourceHint }}</p>
            <p class="mt-2 text-xs leading-5 text-slate-400">{{ cloneFromHint }}</p>
          </div>
        </div>

        <div class="mt-4 grid gap-2 text-sm text-slate-300">
          <div class="flex items-center justify-between rounded-2xl border border-white/8 bg-slate-950/50 px-4 py-3">
            <span>平台</span>
            <span class="font-medium text-white">{{ platformLabel(form.platform) }}</span>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/8 bg-slate-950/50 px-4 py-3">
            <span>画幅 / 时长</span>
            <span class="font-medium text-white">{{ form.aspectRatio }} / {{ form.minDurationSeconds }}-{{ form.maxDurationSeconds }}s</span>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/8 bg-slate-950/50 px-4 py-3">
            <span>产出数量</span>
            <span class="font-medium text-white">{{ form.outputCount }} 条</span>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/8 bg-slate-950/50 px-4 py-3">
            <span>语义素材</span>
            <span class="font-medium text-white">{{ transcriptModeLabel }}</span>
          </div>
          <div class="rounded-2xl border border-white/8 bg-slate-950/50 px-4 py-3">
            <p class="text-xs uppercase tracking-[0.22em] text-slate-400">输入质量</p>
            <p class="mt-2 text-sm font-medium text-white">{{ transcriptStats.quality }}</p>
            <p class="mt-1 text-xs leading-5 text-slate-400">{{ transcriptStats.hint }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.86),rgba(8,11,24,0.7))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
        <PageHeader
          eyebrow="Media"
          title="视频预览"
          description="上传后会在这里显示本地预览，方便确认素材是否正确。"
        />
        <div v-if="previewUrl" class="overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/60">
          <video :src="previewUrl" controls class="aspect-video w-full bg-black object-cover"></video>
          <div class="border-t border-white/10 p-4 text-sm text-slate-300">
            <p class="font-medium text-white">{{ fileName }}</p>
            <p class="mt-1">{{ fileSummary }}</p>
          </div>
        </div>
        <div v-else class="rounded-[24px] border border-dashed border-white/15 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
          选择视频后可在这里预览文件。
        </div>
      </div>

      <div class="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.86),rgba(8,11,24,0.7))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
        <PageHeader
          eyebrow="Checklist"
          title="工作流提示"
          description="当前版本优先保证稳定出片和参数可控。"
        />
        <ul class="grid gap-3 text-sm leading-6 text-slate-300">
          <li>支持本地视频上传和任务记录。</li>
          <li>支持预设模板、历史任务复制和参数摘要。</li>
          <li>结果页支持轮询状态、预览下载和失败重试。</li>
          <li>模型 provider 采用可配置方式，默认接入 Qwen。</li>
        </ul>
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { cloneTask, createTask, fetchPresets, uploadVideo } from "@/api/tasks";
import PageHeader from "@/components/PageHeader.vue";
import type { CreateTaskRequest, TaskCloneDraft, TaskPreset } from "@/types";

const router = useRouter();
const route = useRoute();

const fallbackPresets: TaskPreset[] = [
  {
    key: "douyin_banger",
    name: "抖音爆款版",
    description: "高节奏、高冲突，适合竖屏投放和首刷停留优化。",
    defaultTitle: "抖音爆款版",
    platform: "douyin",
    aspectRatio: "9:16",
    minDurationSeconds: 15,
    maxDurationSeconds: 30,
    outputCount: 3,
    introTemplate: "hook",
    outroTemplate: "brand",
    creativePrompt: "优先保留冲突点和反转点，节奏更快，适合首刷拉停。"
  },
  {
    key: "feed_balanced",
    name: "信息流均衡版",
    description: "更均衡的节奏和时长，适合多平台投放验证。",
    defaultTitle: "信息流均衡版",
    platform: "wechat",
    aspectRatio: "9:16",
    minDurationSeconds: 20,
    maxDurationSeconds: 35,
    outputCount: 4,
    introTemplate: "cinematic",
    outroTemplate: "call_to_action",
    creativePrompt: "保留剧情推进和人物情绪变化，控制切点更平稳。"
  },
  {
    key: "long_cut",
    name: "长视频切条版",
    description: "适合长内容拆条，强调段落完整度和信息覆盖。",
    defaultTitle: "长视频切条版",
    platform: "kuaishou",
    aspectRatio: "16:9",
    minDurationSeconds: 30,
    maxDurationSeconds: 60,
    outputCount: 3,
    introTemplate: "none",
    outroTemplate: "brand",
    creativePrompt: "尽量保留完整片段逻辑，减少过激剪切。"
  }
];

const availablePresets = ref<TaskPreset[]>(fallbackPresets);
const selectedPresetKey = ref<string>(fallbackPresets[0].key);
const file = ref<File | null>(null);
const previewUrl = ref("");
const submitting = ref(false);
const statusText = ref("等待上传视频");
const cloneSource = ref<TaskCloneDraft | null>(null);
const transcriptFileInput = ref<HTMLInputElement | null>(null);

const form = ref<CreateTaskRequest>({
  title: "抖音爆款版",
  sourceAssetId: "",
  sourceFileName: "",
  platform: fallbackPresets[0].platform,
  aspectRatio: fallbackPresets[0].aspectRatio,
  minDurationSeconds: fallbackPresets[0].minDurationSeconds,
  maxDurationSeconds: fallbackPresets[0].maxDurationSeconds,
  outputCount: fallbackPresets[0].outputCount,
  introTemplate: fallbackPresets[0].introTemplate,
  outroTemplate: fallbackPresets[0].outroTemplate,
  creativePrompt: fallbackPresets[0].creativePrompt,
  transcriptText: ""
});

const fileName = computed(() => file.value?.name ?? "未选择文件");
const fileSummary = computed(() => {
  if (!file.value) {
    return "请选择一个视频文件开始创建任务。";
  }

  const sizeMb = (file.value.size / 1024 / 1024).toFixed(1);
  return `${sizeMb} MB · ${file.value.type || "video/*"}`;
});

const activePreset = computed(() => availablePresets.value.find((preset) => preset.key === selectedPresetKey.value) ?? null);

const visiblePresets = computed(() => availablePresets.value);

const sourceHint = computed(() => {
  if (cloneSource.value) {
    return `来自任务：${cloneSource.value.title}`;
  }
  return "当前为新任务";
});

const cloneFromHint = computed(() => {
  if (cloneSource.value) {
    return "已复制历史任务参数，请重新上传对应原视频后提交。";
  }
  return "点击预设卡片即可快速填充任务配置。";
});

const transcriptModeLabel = computed(() => {
  const text = form.value.transcriptText?.trim() ?? "";
  if (!text) {
    return "未提供";
  }
  return /-->/.test(text) ? "带时间戳字幕" : "纯文本语义";
});

const transcriptStats = computed(() => {
  const text = form.value.transcriptText?.trim() ?? "";
  if (!text) {
    return {
      summary: "未提供语义输入",
      quality: "基础模式",
      hint: "当前只会根据创意提示、元信息和候选片段做规划。"
    };
  }

  const lineCount = text.split(/\r?\n/).filter(Boolean).length;
  const hasTiming = /-->/.test(text);
  if (hasTiming) {
    return {
      summary: `${lineCount} 行字幕/台词`,
      quality: "语义切点模式",
      hint: "模型会优先参考字幕时间边界决定切点，适合短剧剧情剪辑。"
    };
  }

  return {
    summary: `${lineCount} 行纯文本`,
    quality: "语义弱引导模式",
    hint: "有语义，但没有时间戳，模型更适合优化标题和候选理由。"
  };
});

function normalizeQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] == null ? "" : String(value[0]);
  }
  return value == null ? "" : String(value);
}

function platformLabel(platform: string) {
  switch (platform) {
    case "douyin":
      return "抖音";
    case "kuaishou":
      return "快手";
    case "xiaohongshu":
      return "小红书";
    case "wechat":
      return "视频号";
    default:
      return platform;
  }
}

function presetBadge(preset: TaskPreset) {
  switch (preset.platform) {
    case "douyin":
      return "Hot";
    case "wechat":
      return "Balanced";
    case "kuaishou":
      return "Series";
    case "xiaohongshu":
      return "Longform";
    default:
      return "Preset";
  }
}

function applyPreset(preset: TaskPreset) {
  selectedPresetKey.value = preset.key;
  form.value.platform = preset.platform;
  form.value.aspectRatio = preset.aspectRatio;
  form.value.minDurationSeconds = preset.minDurationSeconds;
  form.value.maxDurationSeconds = preset.maxDurationSeconds;
  form.value.outputCount = preset.outputCount;
  form.value.introTemplate = preset.introTemplate;
  form.value.outroTemplate = preset.outroTemplate;
  form.value.creativePrompt = preset.creativePrompt ?? "";
  if (!cloneSource.value) {
    form.value.title = preset.defaultTitle;
  }
  statusText.value = `已应用模板：${preset.name}`;
}

function applyCloneSource(task: TaskCloneDraft) {
  cloneSource.value = task;
  const matchedPreset = availablePresets.value.find((preset) => preset.platform === task.platform && preset.aspectRatio === task.aspectRatio);
  selectedPresetKey.value = matchedPreset?.key ?? "custom";
  form.value.title = task.title;
  form.value.platform = task.platform;
  form.value.aspectRatio = task.aspectRatio;
  form.value.minDurationSeconds = task.minDurationSeconds;
  form.value.maxDurationSeconds = task.maxDurationSeconds;
  form.value.outputCount = task.outputCount;
  form.value.introTemplate = task.introTemplate;
  form.value.outroTemplate = task.outroTemplate;
  form.value.creativePrompt = task.creativePrompt ?? "";
  form.value.transcriptText = task.transcriptText ?? "";
  form.value.sourceFileName = task.sourceFileName;
  statusText.value = `已从历史任务「${task.title}」复制参数`;
}

async function loadPresets() {
  try {
    const remotePresets = await fetchPresets();
    if (remotePresets.length > 0) {
      availablePresets.value = remotePresets;
      if (!availablePresets.value.some((preset) => preset.key === selectedPresetKey.value)) {
        selectedPresetKey.value = availablePresets.value[0].key;
      }
      if (cloneSource.value) {
        applyCloneSource(cloneSource.value);
      } else {
        applyPreset(availablePresets.value[0]);
      }
    }
  } catch {
    availablePresets.value = fallbackPresets;
  }
}

async function loadCloneSource() {
  const cloneFrom = normalizeQueryValue(route.query.cloneFrom);
  if (!cloneFrom) {
    return;
  }

  try {
    const task = await cloneTask(cloneFrom);
    applyCloneSource(task);
  } catch {
    statusText.value = "未找到可复制的历史任务，已保留当前表单。";
  }
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const selectedFile = target.files?.[0] ?? null;
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
    previewUrl.value = "";
  }

  file.value = selectedFile;
  if (file.value) {
    form.value.sourceFileName = file.value.name;
    previewUrl.value = URL.createObjectURL(file.value);
    if (!form.value.title.trim()) {
      form.value.title = file.value.name.replace(/\.[^.]+$/, "");
    }
    statusText.value = `已选择：${file.value.name}`;
  } else {
    form.value.sourceAssetId = "";
    form.value.sourceFileName = "";
    statusText.value = "等待上传视频";
  }
}

async function handleTranscriptFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const selectedFile = target.files?.[0];
  if (!selectedFile) {
    return;
  }
  try {
    form.value.transcriptText = await selectedFile.text();
    statusText.value = `已导入字幕文件：${selectedFile.name}`;
  } catch {
    statusText.value = "字幕文件读取失败";
  } finally {
    target.value = "";
  }
}

async function submitTask() {
  if (!file.value) {
    statusText.value = "请先选择视频文件";
    return;
  }

  const payload: CreateTaskRequest = {
    ...form.value,
    title: form.value.title.trim(),
    creativePrompt: form.value.creativePrompt?.trim() || "",
    transcriptText: form.value.transcriptText?.trim() || ""
  };

  if (!payload.title) {
    statusText.value = "请输入任务标题";
    return;
  }

  if (payload.minDurationSeconds > payload.maxDurationSeconds) {
    statusText.value = "最小时长不能大于最大时长";
    return;
  }

  submitting.value = true;

  try {
    statusText.value = "正在上传视频...";
    const uploadResult = await uploadVideo(file.value);
    form.value.sourceAssetId = uploadResult.assetId;
    payload.sourceAssetId = uploadResult.assetId;

    statusText.value = "正在创建任务...";
    const task = await createTask(payload);
    await router.push(`/tasks/${task.id}`);
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "创建任务失败";
  } finally {
    submitting.value = false;
  }
}

watch(
  () => route.query.cloneFrom,
  async () => {
    const cloneFrom = normalizeQueryValue(route.query.cloneFrom);
    if (!cloneFrom) {
      cloneSource.value = null;
      applyPreset(availablePresets.value[0]);
      return;
    }
    cloneSource.value = null;
    await loadCloneSource();
  },
  { immediate: true }
);

onMounted(async () => {
  await loadPresets();
});

onBeforeUnmount(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
});
</script>

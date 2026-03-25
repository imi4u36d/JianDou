<template>
  <section class="grid gap-6 lg:grid-cols-[1.35fr_0.85fr]">
    <div class="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-panel">
      <PageHeader
        eyebrow="Create"
        title="新建剪辑任务"
        description="上传原视频并设置剪辑参数，系统将自动生成多条可预览素材。"
      />

      <form class="grid gap-5" @submit.prevent="submitTask">
        <label class="grid gap-2 text-sm text-slate-200">
          任务标题
          <input v-model="form.title" required class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none ring-0 transition focus:border-orange-300" placeholder="例如：第 12 集高能反转投放版" />
        </label>

        <label class="grid gap-2 text-sm text-slate-200">
          原始视频
          <input
            type="file"
            accept="video/*"
            required
            @change="onFileChange"
            class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white file:mr-4 file:rounded-full file:border-0 file:bg-orange-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-orange-400"
          />
        </label>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            投放平台
            <select v-model="form.platform" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white">
              <option value="douyin">抖音</option>
              <option value="kuaishou">快手</option>
              <option value="xiaohongshu">小红书</option>
              <option value="wechat">视频号</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            画幅比例
            <select v-model="form.aspectRatio" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white">
              <option value="9:16">竖版 9:16</option>
              <option value="16:9">横版 16:9</option>
            </select>
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <label class="grid gap-2 text-sm text-slate-200">
            最小时长（秒）
            <input v-model.number="form.minDurationSeconds" type="number" min="5" max="120" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            最大时长（秒）
            <input v-model.number="form.maxDurationSeconds" type="number" min="5" max="120" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            产出数量
            <input v-model.number="form.outputCount" type="number" min="1" max="10" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white" />
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            片头模板
            <select v-model="form.introTemplate" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white">
              <option value="none">无</option>
              <option value="hook">Hook</option>
              <option value="cinematic">Cinematic</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            片尾模板
            <select v-model="form.outroTemplate" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white">
              <option value="none">无</option>
              <option value="brand">Brand</option>
              <option value="call_to_action">Call To Action</option>
            </select>
          </label>
        </div>

        <label class="grid gap-2 text-sm text-slate-200">
          创意补充
          <textarea v-model="form.creativePrompt" rows="4" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white" placeholder="例如：优先保留冲突点、反转点，节奏更快，适合首刷拉停。"></textarea>
        </label>

        <div class="flex items-center gap-4">
          <button
            :disabled="submitting"
            class="rounded-full bg-orange-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ submitting ? "提交中..." : "开始生成" }}
          </button>
          <p class="text-sm text-slate-300">{{ statusText }}</p>
        </div>
      </form>
    </div>

    <aside class="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-panel">
      <PageHeader
        eyebrow="Preset"
        title="MVP 说明"
        description="当前版本优先保证稳定出片和参数可控。"
      />
      <div v-if="previewUrl" class="mb-5 overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/60">
        <video :src="previewUrl" controls class="aspect-video w-full bg-black object-cover"></video>
        <div class="border-t border-white/10 p-4 text-sm text-slate-300">
          <p class="font-medium text-white">{{ fileName }}</p>
          <p class="mt-1">{{ fileSummary }}</p>
        </div>
      </div>
      <ul class="grid gap-3 text-sm leading-6 text-slate-300">
        <li>支持本地视频上传和任务记录。</li>
        <li>支持时长区间、产出数量、片头片尾模板、平台方向。</li>
        <li>模型 provider 采用可配置方式，默认接入 Qwen。</li>
        <li>结果页支持轮询状态、预览下载和失败重试。</li>
      </ul>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { createTask, uploadVideo } from "@/api/tasks";
import PageHeader from "@/components/PageHeader.vue";
import type { CreateTaskRequest } from "@/types";

const router = useRouter();

const form = ref<CreateTaskRequest>({
  title: "",
  sourceAssetId: "",
  sourceFileName: "",
  platform: "douyin",
  aspectRatio: "9:16",
  minDurationSeconds: 15,
  maxDurationSeconds: 30,
  outputCount: 3,
  introTemplate: "hook",
  outroTemplate: "brand",
  creativePrompt: ""
});

const file = ref<File | null>(null);
const previewUrl = ref("");
const submitting = ref(false);
const statusText = ref("等待上传视频");

const fileName = computed(() => file.value?.name ?? "未选择文件");
const fileSummary = computed(() => {
  if (!file.value) {
    return "请选择一个视频文件开始创建任务。";
  }

  const sizeMb = (file.value.size / 1024 / 1024).toFixed(1);
  return `${sizeMb} MB · ${file.value.type || "video/*"}`;
});

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

async function submitTask() {
  if (!file.value) {
    statusText.value = "请先选择视频文件";
    return;
  }

  const payload: CreateTaskRequest = {
    ...form.value,
    title: form.value.title.trim(),
    creativePrompt: form.value.creativePrompt?.trim() || ""
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

onBeforeUnmount(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
});
</script>

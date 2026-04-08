<template>
  <form class="surface-panel form-card p-6" @submit.prevent="$emit('submit')">
    <div class="form-head">
      <div>
        <p class="eyebrow">Prompt Mode</p>
        <h2>提示词生成视频</h2>
      </div>
      <button type="button" class="usage-btn" @click="$emit('open-usage')">
        {{ props.usageLoading ? "读取中..." : "模型用量" }}
      </button>
    </div>

    <div v-if="props.optionsLoading" class="surface-tile rounded-2xl p-4 text-sm text-slate-600">
      正在加载配置...
    </div>
    <div v-else-if="props.optionsError" class="surface-tile rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-700">
      {{ props.optionsError }}
    </div>

    <label class="field">
      <span class="field-label">提示词</span>
      <textarea
        v-model="props.form.prompt"
        rows="7"
        class="field-textarea"
        placeholder="例如：雨夜街头，人物回头，镜头缓慢推进，霓虹反射，电影感。"
      ></textarea>
    </label>

    <div class="field-grid">
      <label class="field">
        <span class="field-label">文本分析模型</span>
        <select v-model="props.form.textAnalysisModel" class="field-select">
          <option v-for="item in props.textAnalysisModels" :key="item.value" :value="item.value">
            {{ item.label }}{{ item.description ? ` · ${item.description}` : "" }}
          </option>
        </select>
        <TextModelProbeInline
          ref="textModelProbeRef"
          :model-value="props.form.textAnalysisModel"
          :disabled="props.optionsLoading || props.submitting"
        />
      </label>
      <label class="field">
        <span class="field-label">视频模型</span>
        <select v-model="props.form.providerModel" class="field-select">
          <option v-for="item in props.videoModels" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <p v-if="props.selectedVideoModel?.description" class="field-hint">
          {{ props.selectedVideoModel.description }}
        </p>
      </label>
    </div>

    <div class="field-grid">
      <label class="field">
        <span class="field-label">分辨率</span>
        <select v-model="props.form.videoSize" class="field-select">
          <option v-for="item in props.videoSizes" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <p class="field-hint">按当前视频模型过滤可用分辨率。</p>
      </label>
    </div>

    <div class="field-grid field-grid-duration">
      <label class="field">
        <span class="field-label">最小时长</span>
        <input
          v-model="props.form.minDurationSeconds"
          class="field-input"
          type="number"
          min="1"
          max="120"
          step="1"
          placeholder="可留空"
        />
      </label>
      <label class="field">
        <span class="field-label">最大时长</span>
        <input
          v-model="props.form.maxDurationSeconds"
          class="field-input"
          type="number"
          min="1"
          max="120"
          step="1"
          placeholder="可留空"
        />
      </label>
    </div>

    <div class="model-inline">
      <span>{{ props.selectedVideoModel?.label || props.form.providerModel }}</span>
      <span v-if="props.selectedVideoModel?.provider">{{ props.selectedVideoModel.provider }}</span>
      <span>{{ props.form.videoSize || "未选分辨率" }}</span>
      <span>{{ durationHint }}</span>
    </div>

    <div v-if="props.submitError" class="surface-tile rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-700">
      {{ props.submitError }}
    </div>

    <button type="submit" class="btn-primary submit-btn justify-center" :disabled="!props.canSubmit">
      {{ props.submitting ? "生成中..." : "生成视频" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import TextModelProbeInline from "@/components/TextModelProbeInline.vue";
import type { GenerateFormCardProps } from "./types";

const props = defineProps<GenerateFormCardProps>();
const textModelProbeRef = ref<{ ensureReady: (force?: boolean) => Promise<boolean> } | null>(null);

const durationHint = computed(() => {
  const values = props.videoDurations.map((item) => item.value).filter((item) => Number.isFinite(item));
  return values.length ? `常见时长 ${values.join(" / ")} 秒` : "按模型默认时长处理";
});

defineEmits<{
  submit: [];
  "open-usage": [];
}>();

defineExpose({
  async ensureTextModelReady() {
    return (await textModelProbeRef.value?.ensureReady()) !== false;
  },
});
</script>

<style scoped>
.form-card {
  display: grid;
  gap: 1rem;
}

.form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.eyebrow {
  margin: 0 0 0.2rem;
  color: #6b819b;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.form-head h2 {
  margin: 0;
  font-family: "Sora", "PingFang SC", sans-serif;
  font-size: 1.28rem;
  font-weight: 750;
  letter-spacing: -0.04em;
  color: #102842;
}

.usage-btn {
  border: 1px solid rgba(102, 126, 158, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: #244364;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.52rem 0.9rem;
}

.field {
  display: grid;
  gap: 0.5rem;
}

.field-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-grid-duration {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-label {
  color: #35526f;
  font-size: 0.82rem;
  font-weight: 700;
}

.field-hint {
  margin: 0;
  color: #6b819b;
  font-size: 0.74rem;
  line-height: 1.5;
}

.field-input,
.field-select,
.field-textarea {
  width: 100%;
  border: 1px solid rgba(124, 149, 182, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: #12233d;
  padding: 0.88rem 0.95rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.field-textarea {
  min-height: 10rem;
  resize: vertical;
  line-height: 1.7;
}

.field-input:focus,
.field-select:focus,
.field-textarea:focus {
  outline: none;
  border-color: rgba(46, 125, 255, 0.34);
  box-shadow:
    0 0 0 4px rgba(46, 125, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.model-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.model-inline span {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(111, 143, 185, 0.16);
  padding: 0.42rem 0.72rem;
  color: #4d6581;
  font-size: 0.75rem;
  font-weight: 700;
}

.submit-btn {
  min-height: 3.1rem;
}

@media (max-width: 820px) {
  .field-grid,
  .field-grid-duration {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 640px) {
  .form-card {
    padding: 1.1rem;
  }

  .form-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

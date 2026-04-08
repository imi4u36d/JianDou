<script lang="ts">
export interface TextModelProbeInlineExpose {
  ensureReady: (force?: boolean) => Promise<boolean>;
  reset: () => void;
}
</script>

<template>
  <div class="text-model-probe">
    <button
      type="button"
      class="text-model-probe__button"
      :disabled="buttonDisabled"
      @click="handleProbe"
    >
      {{ buttonLabel }}
    </button>
    <p class="text-model-probe__status" :class="statusClass">
      {{ statusText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { probeTextAnalysisModel } from "@/api/generation";
import type { ProbeTextAnalysisModelResponse } from "@/types";

const props = withDefaults(defineProps<{
  modelValue: string;
  disabled?: boolean;
}>(), {
  disabled: false,
});

const probeState = ref<"idle" | "loading" | "success" | "error">("idle");
const checkedModel = ref("");
const errorMessage = ref("");
const probeResult = ref<ProbeTextAnalysisModelResponse | null>(null);
const probeToken = ref(0);

const normalizedModel = computed(() => props.modelValue.trim());
const isCurrentModelReady = computed(
  () => probeState.value === "success" && checkedModel.value === normalizedModel.value
);
const buttonDisabled = computed(() => props.disabled || probeState.value === "loading" || !normalizedModel.value);
const buttonLabel = computed(() => {
  if (probeState.value === "loading") {
    return "测试中...";
  }
  if (isCurrentModelReady.value) {
    return "重新测试";
  }
  return "测试模型";
});
const statusClass = computed(() => {
  if (probeState.value === "success") {
    return "text-model-probe__status-success";
  }
  if (probeState.value === "error") {
    return "text-model-probe__status-error";
  }
  return "text-model-probe__status-idle";
});
const statusText = computed(() => {
  if (probeState.value === "loading") {
    return `正在测试 ${normalizedModel.value || "当前模型"} 连通性...`;
  }
  if (probeState.value === "success" && probeResult.value) {
    const provider = probeResult.value.provider || "provider";
    const resolvedModel = probeResult.value.resolvedModel || normalizedModel.value || "unknown";
    const latency = Number.isFinite(probeResult.value.latencyMs) ? `${probeResult.value.latencyMs} ms` : "";
    return `${provider} / ${resolvedModel} 已连通${latency ? ` · ${latency}` : ""}`;
  }
  if (probeState.value === "error") {
    return errorMessage.value || "模型测试失败";
  }
  return "切换模型后建议先测试一次；正式提交前也会自动校验。";
});

function reset() {
  probeToken.value += 1;
  probeState.value = "idle";
  checkedModel.value = "";
  errorMessage.value = "";
  probeResult.value = null;
}

watch(normalizedModel, () => {
  reset();
});

async function ensureReady(force = false) {
  const currentModel = normalizedModel.value;
  if (!currentModel) {
    probeState.value = "error";
    errorMessage.value = "请先选择文本模型";
    return false;
  }
  if (!force && isCurrentModelReady.value) {
    return true;
  }
  const token = probeToken.value + 1;
  probeToken.value = token;
  probeState.value = "loading";
  errorMessage.value = "";
  try {
    const response = await probeTextAnalysisModel({ textAnalysisModel: currentModel });
    if (probeToken.value !== token) {
      return false;
    }
    probeResult.value = response;
    checkedModel.value = currentModel;
    probeState.value = "success";
    return true;
  } catch (error) {
    if (probeToken.value !== token) {
      return false;
    }
    checkedModel.value = currentModel;
    probeState.value = "error";
    errorMessage.value = error instanceof Error ? error.message : "模型测试失败";
    probeResult.value = null;
    return false;
  }
}

async function handleProbe() {
  await ensureReady(true);
}

defineExpose<TextModelProbeInlineExpose>({
  ensureReady,
  reset,
});
</script>

<style scoped>
.text-model-probe {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.text-model-probe__button {
  border: 1px solid rgba(59, 130, 246, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #1d4ed8;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1;
  padding: 0.5rem 0.8rem;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
}

.text-model-probe__button:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.42);
  background: rgba(239, 246, 255, 0.92);
}

.text-model-probe__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.text-model-probe__status {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.45;
}

.text-model-probe__status-idle {
  color: #64748b;
}

.text-model-probe__status-success {
  color: #047857;
}

.text-model-probe__status-error {
  color: #be123c;
}
</style>

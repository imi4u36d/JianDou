<template>
  <section class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">Model Readiness</p>
        <h3 class="mt-2 text-sm font-semibold text-white">模型就绪状态</h3>
        <p class="mt-1 text-xs leading-5 text-slate-400">
          只检查配置完整度和规划能力，不发真实模型请求，不额外消耗 token。
        </p>
      </div>
      <span
        :class="health?.runtime.model.ready ? 'border-emerald-400/20 bg-emerald-500/15 text-emerald-100' : 'border-amber-400/20 bg-amber-500/15 text-amber-100'"
        class="rounded-full border px-3 py-1 text-xs font-semibold"
      >
        {{ health?.runtime.model.ready ? "模型配置就绪" : "模型配置未完成" }}
      </span>
    </div>

    <div v-if="loading" class="mt-4 text-sm text-slate-400">正在读取运行时状态...</div>
    <div v-else-if="errorMessage" class="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-100">
      {{ errorMessage }}
    </div>
    <div v-else-if="health" class="mt-4 grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
          <p class="text-xs uppercase tracking-[0.22em] text-slate-400">主模型</p>
          <p class="mt-2 text-sm font-semibold text-white">{{ health.runtime.model.primary_model }}</p>
          <p class="mt-1 text-xs text-slate-400">{{ health.runtime.model.provider }} · {{ health.runtime.execution_mode }}</p>
        </div>
        <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
          <p class="text-xs uppercase tracking-[0.22em] text-slate-400">回退模型</p>
          <p class="mt-2 text-sm font-semibold text-white">{{ health.runtime.model.fallback_model || "未配置" }}</p>
          <p class="mt-1 text-xs text-slate-400">主模型失败时自动回退</p>
        </div>
        <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
          <p class="text-xs uppercase tracking-[0.22em] text-slate-400">Endpoint</p>
          <p class="mt-2 truncate text-sm font-semibold text-white">{{ health.runtime.model.endpoint_host || "未配置" }}</p>
          <p class="mt-1 text-xs text-slate-400">只展示 host，不暴露 key</p>
        </div>
        <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
          <p class="text-xs uppercase tracking-[0.22em] text-slate-400">参数</p>
          <p class="mt-2 text-sm font-semibold text-white">T={{ health.runtime.model.temperature }} · Max={{ health.runtime.model.max_tokens }}</p>
          <p class="mt-1 text-xs text-slate-400">{{ health.runtime.model.api_key_present ? "API Key 已配置" : "API Key 缺失" }}</p>
        </div>
      </div>

      <div class="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
        <p class="text-xs uppercase tracking-[0.22em] text-slate-400">规划能力</p>
        <div class="mt-3 grid gap-2 text-sm text-slate-300">
          <div class="flex items-center justify-between">
            <span>带时间戳字幕优先</span>
            <span class="font-medium text-white">{{ yesNo(health.runtime.planning_capabilities.timed_transcript_supported) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span>字幕语义规划</span>
            <span class="font-medium text-white">{{ yesNo(health.runtime.planning_capabilities.transcript_semantic_planning) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span>启发式回退</span>
            <span class="font-medium text-white">{{ yesNo(health.runtime.planning_capabilities.fallback_heuristic_enabled) }}</span>
          </div>
        </div>
        <div v-if="health.runtime.model.config_errors.length" class="mt-3 rounded-2xl border border-amber-400/15 bg-amber-500/10 p-3 text-xs text-amber-100">
          配置问题：{{ health.runtime.model.config_errors.join(" / ") }}
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchHealth } from "@/api/health";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const loading = ref(true);
const errorMessage = ref("");

function yesNo(value: boolean) {
  return value ? "已启用" : "未启用";
}

async function loadHealth() {
  loading.value = true;
  errorMessage.value = "";
  try {
    health.value = await fetchHealth();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取运行时状态失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadHealth();
});
</script>

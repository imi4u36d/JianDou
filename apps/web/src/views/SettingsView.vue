<template>
  <section class="settings-view">
    <div class="settings-main">
      <header class="settings-page-head">
        <p class="panel-eyebrow">模型设置</p>
        <h2 class="page-title">运行时模型配置</h2>
        <p class="settings-page-head__summary">端点和模型目录由后端维护，前端只负责补充各模型接入的 API Key。</p>
      </header>

      <section class="settings-section">
        <div class="settings-section__head">
          <div>
            <h3>模型接入密钥</h3>
            <p>输入新 key 后可先校验，再保存到后端 secrets 覆盖文件并立即刷新运行时。</p>
          </div>
          <div class="settings-actions">
            <HintBell
              v-if="validationBellVisible"
              title="配置摘要"
              :text="validationBellText"
              :items="validationBellItems"
              align="right"
            />
            <button class="btn-secondary btn-sm" type="button" :disabled="loading" @click="loadConfig">
              {{ loading ? "刷新中..." : "刷新运行时" }}
            </button>
            <button class="btn-secondary btn-sm" type="button" :disabled="!runtimeConfig || loading" @click="resetDraft">
              重置输入
            </button>
            <button class="btn-secondary btn-sm" type="button" :disabled="!runtimeConfig || validating || saving" @click="validateDraft">
              {{ validating ? "校验中..." : "校验密钥" }}
            </button>
            <button class="btn-primary btn-sm" type="button" :disabled="saving || validating || pendingUpdateCount === 0" @click="saveDraft">
              {{ saving ? "保存中..." : "保存并生效" }}
            </button>
          </div>
        </div>

        <div v-if="loading" class="surface-panel state-panel">
          正在读取模型配置...
        </div>
        <div v-else-if="errorMessage" class="surface-panel state-panel state-panel-error">
          {{ errorMessage }}
        </div>
        <div v-else-if="runtimeConfig" class="settings-section__content">
          <section class="summary-grid">
            <article class="surface-panel summary-card summary-card-primary">
              <p class="summary-card__eyebrow">运行时来源</p>
              <strong>{{ displayedConfig?.configSource || "未知" }}</strong>
              <p>厂商 {{ displayedConfig?.summary.vendorCount ?? 0 }} 个 · 模型接入 {{ displayedConfig?.summary.providerCount ?? 0 }} 个</p>
              <p>模型 {{ displayedConfig?.summary.modelCount ?? 0 }} 个</p>
              <p>就绪 {{ displayedConfig?.summary.readyModelCount ?? 0 }}/{{ displayedConfig?.summary.modelCount ?? 0 }}</p>
            </article>

            <article class="surface-panel summary-card">
              <p class="summary-card__eyebrow">草稿状态</p>
              <strong>{{ pendingUpdateCount > 0 ? `待保存 ${pendingUpdateCount} 项` : "无待保存改动" }}</strong>
              <p>已配置接入 Key {{ configuredProviderCount }}/{{ providerRows.length }}</p>
              <p v-if="successMessage">{{ successMessage }}</p>
              <p v-else-if="validationResult">{{ validationResult.valid ? "校验通过" : "校验未通过" }}</p>
              <p v-else>可先校验，再保存到后端。</p>
            </article>

            <article class="surface-panel summary-card">
              <p class="summary-card__eyebrow">默认参数</p>
              <div class="summary-list">
                <div>
                  <span>画幅</span>
                  <strong>{{ displayedConfig?.defaults.aspectRatio || "-" }}</strong>
                </div>
                <div>
                  <span>风格</span>
                  <strong>{{ displayedConfig?.defaults.stylePreset || "-" }}</strong>
                </div>
                <div>
                  <span>图片尺寸</span>
                  <strong>{{ displayedConfig?.defaults.imageSize || "-" }}</strong>
                </div>
                <div>
                  <span>视频尺寸</span>
                  <strong>{{ displayedConfig?.defaults.videoSize || "-" }}</strong>
                </div>
                <div>
                  <span>视频时长</span>
                  <strong>{{ displayedConfig?.defaults.videoDurationSeconds ?? "-" }} 秒</strong>
                </div>
                <div>
                  <span>Timeout / Tokens</span>
                  <strong>{{ displayedConfig?.defaults.timeoutSeconds ?? "-" }} / {{ displayedConfig?.defaults.maxTokens ?? "-" }}</strong>
                </div>
              </div>
            </article>
          </section>

          <div v-if="displayedConfig?.configErrors.length" class="surface-panel state-panel state-panel-error">
            {{ displayedConfig.configErrors.join(" / ") }}
          </div>

          <section class="settings-block">
            <div class="settings-block__head">
              <h4>模型接入 Key 输入</h4>
              <span class="surface-chip">{{ providerRows.length }} 个</span>
            </div>

            <div class="vendor-groups">
              <section v-for="group in groupedProviders" :key="group.vendor" class="vendor-group">
                <div class="vendor-group__head">
                  <div>
                    <p class="provider-card__eyebrow">厂商</p>
                    <h5>{{ group.title }}</h5>
                  </div>
                  <span class="surface-chip">{{ group.items.length }} 个接入</span>
                </div>

                <div class="provider-grid">
                  <article v-for="provider in group.items" :key="provider.key" class="surface-panel provider-card">
                    <div class="provider-card__head">
                      <div>
                        <p class="provider-card__eyebrow">{{ provider.key }}</p>
                        <h5>{{ provider.provider || provider.key }}</h5>
                      </div>
                      <span class="status-pill" :class="resolveProviderStatus(provider).tone">
                        {{ resolveProviderStatus(provider).label }}
                      </span>
                    </div>

                    <label class="settings-field">
                      <span>API Key</span>
                      <input
                        v-model="providerDrafts[provider.draftIndex].apiKey"
                        class="field-input"
                        type="password"
                        :placeholder="provider.apiKeyConfigured ? '已存在 key，留空表示不修改' : '请输入新的 API Key'"
                      />
                    </label>

                    <div class="summary-list provider-card__summary">
                      <div>
                        <span>厂商</span>
                        <strong>{{ group.title }}</strong>
                      </div>
                      <div>
                        <span>Endpoint Host</span>
                        <strong>{{ provider.endpointHost || "未配置" }}</strong>
                      </div>
                      <div>
                        <span>Task Host</span>
                        <strong>{{ provider.taskEndpointHost || "未配置" }}</strong>
                      </div>
                      <div>
                        <span>模型数</span>
                        <strong>{{ provider.modelNames.length }}</strong>
                      </div>
                      <div>
                        <span>类型</span>
                        <strong>{{ provider.kinds.join(" / ") || "未关联" }}</strong>
                      </div>
                    </div>

                    <div class="chip-list">
                      <span class="meta-chip meta-chip-muted">{{ formatVendor(provider.vendor) }}</span>
                      <span class="meta-chip" :class="provider.apiKeyConfigured ? 'meta-chip-ready' : 'meta-chip-muted'">
                        {{ provider.apiKeyConfigured ? "运行时已有 Key" : "运行时无 Key" }}
                      </span>
                      <span v-if="provider.apiKey.trim()" class="meta-chip meta-chip-ready">本次将覆盖</span>
                      <span class="meta-chip meta-chip-muted">
                        {{ provider.baseUrlConfigured ? "端点已配置" : "端点缺失" }}
                      </span>
                      <span v-if="provider.taskBaseUrlConfigured" class="meta-chip meta-chip-muted">含 Task Endpoint</span>
                    </div>

                    <div v-if="provider.modelNames.length" class="provider-card__models">
                      <strong>关联模型</strong>
                      <div class="chip-list">
                        <span v-for="name in provider.modelNames" :key="name" class="meta-chip meta-chip-muted">{{ name }}</span>
                      </div>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </section>

          <section class="settings-block">
            <div class="settings-block__head">
              <h4>模型目录</h4>
              <span class="surface-chip">{{ groupedModels.reduce((total, group) => total + group.items.length, 0) }} 个模型</span>
            </div>

            <div class="model-groups">
              <article v-for="group in groupedModels" :key="group.kind" class="surface-panel model-group-card">
                <div class="model-group-card__head">
                  <div>
                    <p class="provider-card__eyebrow">{{ formatKind(group.kind) }}</p>
                    <h5>{{ group.title }}</h5>
                  </div>
                  <span class="surface-chip">{{ group.items.length }} 个</span>
                </div>

                <div class="model-vendor-groups">
                  <section v-for="vendorGroup in group.vendorGroups" :key="`${group.kind}-${vendorGroup.vendor}`" class="model-vendor-group">
                    <div class="model-vendor-group__head">
                      <div>
                        <p class="provider-card__eyebrow">厂商</p>
                        <h6>{{ vendorGroup.title }}</h6>
                      </div>
                      <span class="surface-chip">{{ vendorGroup.items.length }} 个</span>
                    </div>

                    <div class="model-list">
                      <div v-for="item in vendorGroup.items" :key="`${group.kind}-${item.name}`" class="model-item">
                        <div class="model-item__head">
                          <div>
                            <strong>{{ item.label || item.name }}</strong>
                            <p>{{ item.name }}</p>
                          </div>
                          <span class="status-pill" :class="item.ready ? 'status-connected' : 'status-disconnected'">
                            {{ item.ready ? "就绪" : "缺配置" }}
                          </span>
                        </div>

                        <p v-if="item.description" class="model-item__description">{{ item.description }}</p>

                        <div class="model-meta-grid">
                          <div>
                            <span>厂商</span>
                            <strong>{{ vendorGroup.title }}</strong>
                          </div>
                          <div>
                            <span>模型接入</span>
                            <strong>{{ item.provider || "-" }}</strong>
                          </div>
                          <div>
                            <span>Family</span>
                            <strong>{{ item.family || "-" }}</strong>
                          </div>
                          <div>
                            <span>Endpoint Host</span>
                            <strong>{{ item.endpointHost || "-" }}</strong>
                          </div>
                          <div>
                            <span>Task Host</span>
                            <strong>{{ item.taskEndpointHost || "-" }}</strong>
                          </div>
                        </div>

                        <div class="chip-list">
                          <span class="meta-chip meta-chip-muted">{{ formatVendor(item.vendor) }}</span>
                          <span v-if="item.fallbackModel" class="meta-chip meta-chip-muted">Fallback: {{ item.fallbackModel }}</span>
                          <span v-if="item.generationMode" class="meta-chip meta-chip-muted">Mode: {{ item.generationMode }}</span>
                          <span v-if="item.supportsSeed" class="meta-chip meta-chip-ready">支持 Seed</span>
                          <span v-if="item.supportsResponsesApi" class="meta-chip meta-chip-ready">Responses API</span>
                          <span v-if="item.prefersChatCompletionsForVision" class="meta-chip meta-chip-muted">Vision Chat</span>
                          <span v-for="size in item.supportedSizes" :key="`${item.name}-size-${size}`" class="meta-chip meta-chip-muted">{{ size }}</span>
                          <span v-for="duration in item.supportedDurations" :key="`${item.name}-duration-${duration}`" class="meta-chip meta-chip-muted">{{ duration }} 秒</span>
                        </div>

                        <p v-if="item.issues.length" class="control-card__error">{{ item.issues.join(" / ") }}</p>
                      </div>
                    </div>
                  </section>
                </div>
              </article>
            </div>
          </section>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import HintBell from "@/components/HintBell.vue";
import { fetchAdminModelConfig, saveAdminModelConfigKeys, validateAdminModelConfig } from "@/api/admin";
import type {
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigProviderItem,
  AdminModelConfigResponse,
  AdminModelConfigValidationResponse,
} from "@/types";

interface ProviderKeyDraftRow {
  key: string;
  apiKey: string;
}

interface ProviderViewRow extends AdminModelConfigProviderItem {
  apiKey: string;
  draftIndex: number;
}

interface ProviderVendorGroup {
  vendor: string;
  title: string;
  items: ProviderViewRow[];
}

interface ModelVendorGroup {
  vendor: string;
  title: string;
  items: AdminModelConfigResponse["models"];
}

interface ModelGroup {
  kind: string;
  title: string;
  items: AdminModelConfigResponse["models"];
  vendorGroups: ModelVendorGroup[];
}

const runtimeConfig = ref<AdminModelConfigResponse | null>(null);
const providerDrafts = ref<ProviderKeyDraftRow[]>([]);
const validationResult = ref<AdminModelConfigValidationResponse | null>(null);
const loading = ref(false);
const validating = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const displayedConfig = computed(() => validationResult.value?.snapshot ?? runtimeConfig.value);

const providerRows = computed<ProviderViewRow[]>(() => {
  const runtimeMap = new Map((runtimeConfig.value?.providers ?? []).map((item) => [item.key, item]));
  const displayedMap = new Map((displayedConfig.value?.providers ?? []).map((item) => [item.key, item]));
  return providerDrafts.value.map((draft, index) => {
    const provider = displayedMap.get(draft.key) ?? runtimeMap.get(draft.key);
    return {
      key: draft.key,
      provider: provider?.provider ?? draft.key,
      vendor: provider?.vendor ?? "",
      kinds: provider?.kinds ?? [],
      baseUrl: provider?.baseUrl ?? "",
      taskBaseUrl: provider?.taskBaseUrl ?? "",
      endpointHost: provider?.endpointHost ?? "",
      taskEndpointHost: provider?.taskEndpointHost ?? "",
      apiKeyConfigured: provider?.apiKeyConfigured ?? false,
      baseUrlConfigured: provider?.baseUrlConfigured ?? false,
      taskBaseUrlConfigured: provider?.taskBaseUrlConfigured ?? false,
      extras: provider?.extras ?? {},
      modelNames: provider?.modelNames ?? [],
      apiKey: draft.apiKey,
      draftIndex: index,
    };
  });
});

const groupedProviders = computed<ProviderVendorGroup[]>(() => {
  const buckets = new Map<string, ProviderViewRow[]>();
  for (const provider of providerRows.value) {
    const key = normalizeVendor(provider.vendor);
    const current = buckets.get(key) ?? [];
    current.push(provider);
    buckets.set(key, current);
  }
  return Array.from(buckets.entries())
    .map(([vendor, items]) => ({
      vendor,
      title: formatVendor(vendor),
      items: items.slice().sort((left, right) => left.key.localeCompare(right.key)),
    }))
    .sort((left, right) => left.title.localeCompare(right.title));
});

const configuredProviderCount = computed(() => {
  return providerRows.value.filter((item) => item.apiKeyConfigured).length;
});

const pendingUpdateCount = computed(() => {
  return providerDrafts.value.filter((item) => item.apiKey.trim()).length;
});

const groupedModels = computed<ModelGroup[]>(() => {
  const source = displayedConfig.value?.models ?? [];
  const groups: Array<{ kind: string; title: string }> = [
    { kind: "text", title: "文本模型" },
    { kind: "vision", title: "视觉模型" },
    { kind: "image", title: "关键帧模型" },
    { kind: "video", title: "视频模型" },
  ];
  return groups
    .map((group) => {
      const items = source.filter((item) => item.kind === group.kind);
      const buckets = new Map<string, AdminModelConfigResponse["models"]>();
      for (const item of items) {
        const key = normalizeVendor(item.vendor);
        const current = buckets.get(key) ?? [];
        current.push(item);
        buckets.set(key, current);
      }
      return {
        kind: group.kind,
        title: group.title,
        items,
        vendorGroups: Array.from(buckets.entries())
          .map(([vendor, vendorItems]) => ({
            vendor,
            title: formatVendor(vendor),
            items: vendorItems.slice().sort((left, right) => left.name.localeCompare(right.name)),
          }))
          .sort((left, right) => left.title.localeCompare(right.title)),
      };
    })
    .filter((group) => group.items.length > 0);
});

const unreadyModels = computed(() => (displayedConfig.value?.models ?? []).filter((item) => !item.ready));

const validationBellVisible = computed(() => {
  return Boolean(displayedConfig.value || validationResult.value || successMessage.value);
});

const validationBellText = computed(() => {
  if (successMessage.value) {
    return successMessage.value;
  }
  if (validationResult.value && displayedConfig.value) {
    return validationResult.value.valid
      ? `校验通过，当前 ${displayedConfig.value.summary.readyModelCount}/${displayedConfig.value.summary.modelCount} 个模型满足运行条件。`
      : `校验未通过，当前 ${displayedConfig.value.summary.readyModelCount}/${displayedConfig.value.summary.modelCount} 个模型满足运行条件。`;
  }
  if (displayedConfig.value) {
    return `当前运行时有 ${displayedConfig.value.summary.readyModelCount}/${displayedConfig.value.summary.modelCount} 个模型已就绪。`;
  }
  return "读取运行时后会在这里展示配置摘要。";
});

const validationBellItems = computed(() => {
  const items: string[] = [];
  if (pendingUpdateCount.value > 0) {
    items.push(`待保存模型接入: ${pendingUpdateCount.value} 个`);
  }
  for (const issue of displayedConfig.value?.configErrors.slice(0, 3) ?? []) {
    items.push(`全局问题: ${issue}`);
  }
  for (const item of unreadyModels.value.slice(0, 4)) {
    items.push(`${item.label || item.name}: ${item.issues.join("，") || "配置不完整"}`);
  }
  if (!items.length) {
    items.push("当前没有全局错误，运行时目录中的模型均满足配置条件。");
  }
  return items;
});

function toKeyDraft(config: AdminModelConfigResponse): ProviderKeyDraftRow[] {
  return config.providers.map((provider) => ({
    key: provider.key,
    apiKey: "",
  }));
}

function buildRequest(): AdminModelConfigKeyUpdateRequest {
  return {
    providers: providerDrafts.value.map((provider) => ({
      key: provider.key,
      apiKey: provider.apiKey.trim(),
    })),
  };
}

function formatKind(kind: string) {
  switch (kind) {
    case "text":
      return "文本";
    case "vision":
      return "视觉";
    case "image":
      return "关键帧";
    case "video":
      return "视频";
    default:
      return kind || "未知";
  }
}

function normalizeVendor(vendor: string) {
  const normalized = vendor.trim().toLowerCase();
  return normalized || "unknown";
}

function formatVendor(vendor: string) {
  switch (normalizeVendor(vendor)) {
    case "aliyun":
      return "Aliyun";
    case "volcengine":
      return "Volcengine";
    case "openai":
      return "OpenAI";
    case "unknown":
      return "未归类厂商";
    default:
      return vendor || "未归类厂商";
  }
}

function resolveProviderStatus(provider: ProviderViewRow) {
  if (provider.apiKey.trim()) {
    return { label: "待保存", tone: "status-pending" };
  }
  if (provider.apiKeyConfigured) {
    return { label: "已配置", tone: "status-connected" };
  }
  return { label: "待补全", tone: "status-disconnected" };
}

function resetDraft() {
  if (!runtimeConfig.value) {
    return;
  }
  providerDrafts.value = toKeyDraft(runtimeConfig.value);
  validationResult.value = null;
  errorMessage.value = "";
  successMessage.value = "";
}

async function loadConfig() {
  loading.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const response = await fetchAdminModelConfig();
    runtimeConfig.value = response;
    providerDrafts.value = toKeyDraft(response);
    validationResult.value = null;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取模型配置失败";
  } finally {
    loading.value = false;
  }
}

async function validateDraft() {
  if (!runtimeConfig.value) {
    return;
  }
  validating.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    validationResult.value = await validateAdminModelConfig(buildRequest());
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "密钥校验失败";
  } finally {
    validating.value = false;
  }
}

async function saveDraft() {
  if (!runtimeConfig.value || pendingUpdateCount.value === 0) {
    return;
  }
  saving.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const response = await saveAdminModelConfigKeys(buildRequest());
    runtimeConfig.value = response;
    providerDrafts.value = toKeyDraft(response);
    validationResult.value = null;
    successMessage.value = "API Key 已保存，并刷新了当前运行时配置。";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "保存 API Key 失败";
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadConfig();
});
</script>

<style scoped>
.settings-view {
  height: 100%;
  min-height: 0;
  overflow: auto;
}

.settings-main {
  display: grid;
  grid-template-rows: auto auto;
  gap: 18px;
  min-height: 100%;
}

.settings-page-head {
  padding: 4px 6px 0;
}

.settings-page-head__summary {
  margin: 0.6rem 0 0;
  color: var(--text-body);
}

.settings-section {
  display: grid;
  grid-template-rows: auto auto;
  gap: 16px;
  min-height: 0;
}

.settings-section__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.settings-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}

.settings-section__head h3 {
  margin: 0;
  font-size: 1.95rem;
  font-family: "Sora", "Inter", sans-serif;
  letter-spacing: -0.04em;
}

.settings-section__head p {
  margin: 0.45rem 0 0;
  color: var(--text-body);
  line-height: 1.7;
}

.settings-section__content {
  display: grid;
  gap: 16px;
  min-height: 0;
  overflow: visible;
  padding-right: 6px;
}

.state-panel {
  padding: 20px;
  color: var(--text-body);
}

.state-panel-error {
  color: #ff9eb0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.summary-card,
.provider-card,
.model-group-card {
  padding: 18px;
}

.summary-card {
  display: grid;
  gap: 8px;
}

.summary-card-primary {
  box-shadow:
    var(--shadow-panel),
    0 0 0 1px rgba(145, 180, 255, 0.18),
    0 0 42px rgba(176, 92, 255, 0.12),
    0 0 64px rgba(78, 219, 255, 0.1);
}

.summary-card__eyebrow,
.provider-card__eyebrow {
  margin: 0;
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.summary-card strong {
  font-size: 1.15rem;
  word-break: break-all;
}

.summary-card p {
  margin: 0;
  color: var(--text-body);
}

.summary-list {
  display: grid;
  gap: 10px;
}

.summary-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.summary-list span {
  color: var(--text-body);
}

.summary-list strong {
  font-size: 0.96rem;
  text-align: right;
}

.settings-block {
  display: grid;
  gap: 14px;
}

.settings-block__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.settings-block__head h4 {
  margin: 0;
  font-size: 1.15rem;
}

.settings-field {
  display: grid;
  gap: 8px;
}

.settings-field span {
  color: var(--text-body);
  font-size: 0.88rem;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.vendor-groups,
.model-vendor-groups {
  display: grid;
  gap: 16px;
}

.vendor-group,
.model-vendor-group {
  display: grid;
  gap: 14px;
}

.vendor-group__head,
.model-vendor-group__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.vendor-group__head h5,
.model-vendor-group__head h6 {
  margin: 0.45rem 0 0;
}

.model-vendor-group {
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.model-vendor-group:first-child {
  padding-top: 0;
  border-top: 0;
}

.provider-card,
.model-group-card {
  display: grid;
  gap: 14px;
}

.provider-card {
  align-content: start;
}

.provider-card__head,
.model-group-card__head,
.model-item__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.provider-card__head h5,
.model-group-card__head h5 {
  margin: 0.45rem 0 0;
  font-size: 1.2rem;
}

.provider-card__summary {
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(145, 180, 255, 0.12);
  background: rgba(8, 11, 18, 0.56);
}

.provider-card__models {
  display: grid;
  gap: 10px;
}

.provider-card__models strong {
  font-size: 0.95rem;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}

.meta-chip {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-height: 32px;
  padding: 0 0.8rem;
  border-radius: 14px;
  border: 1px solid rgba(145, 180, 255, 0.22);
  background: rgba(8, 11, 18, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 10px 24px rgba(0, 0, 0, 0.16);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  line-height: 1;
  white-space: nowrap;
  box-sizing: border-box;
}

.meta-chip-ready {
  border-color: rgba(91, 215, 139, 0.24);
  background: rgba(91, 215, 139, 0.08);
  color: #c5f7d6;
}

.meta-chip-muted {
  border-color: rgba(145, 180, 255, 0.22);
  background: rgba(8, 11, 18, 0.78);
  color: rgba(255, 255, 255, 0.72);
}

.model-groups {
  display: grid;
  gap: 16px;
}

.model-list {
  display: grid;
  gap: 14px;
}

.model-item {
  display: grid;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.model-item:first-child {
  padding-top: 0;
  border-top: 0;
}

.model-item__head strong {
  display: block;
  font-size: 1rem;
}

.model-item__head p,
.model-item__description {
  margin: 0.4rem 0 0;
  color: var(--text-body);
}

.model-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.model-meta-grid div {
  display: grid;
  gap: 4px;
}

.model-meta-grid span {
  color: var(--text-body);
  font-size: 0.82rem;
}

.model-meta-grid strong {
  font-size: 0.94rem;
  word-break: break-word;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-height: 34px;
  padding: 0 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(145, 180, 255, 0.22);
  background: rgba(8, 11, 18, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 10px 24px rgba(0, 0, 0, 0.16);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.status-connected {
  border-color: rgba(91, 215, 139, 0.24);
  background: rgba(91, 215, 139, 0.08);
  color: #c5f7d6;
}

.status-disconnected {
  border-color: rgba(255, 118, 150, 0.24);
  background: rgba(255, 118, 150, 0.08);
  color: #ff95aa;
}

.status-pending {
  border-color: rgba(255, 196, 92, 0.24);
  background: rgba(255, 196, 92, 0.08);
  color: #ffe29f;
}

.control-card__error {
  margin: 0;
  color: #ff9eb0;
}

@media (max-width: 1200px) {
  .summary-grid,
  .provider-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .settings-section__head,
  .vendor-group__head,
  .model-vendor-group__head,
  .provider-card__head,
  .model-group-card__head,
  .model-item__head {
    display: grid;
    grid-template-columns: 1fr;
  }

  .settings-actions {
    justify-content: stretch;
  }

  .summary-card,
  .provider-card,
  .model-group-card {
    padding: 16px;
  }

  .model-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>

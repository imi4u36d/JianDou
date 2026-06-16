<template>
  <section class="settings-view">
    <div class="settings-main">
      <header class="settings-page-head">
        <p class="panel-eyebrow">模型设置</p>
        <h2 class="page-title">我的模型配置</h2>
      </header>

      <section class="settings-section">
        <div class="settings-section__head">
          <div>
            <h3>模型接入密钥</h3>
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
        <div v-else-if="runtimeConfig" class="settings-section__content">
          <div class="settings-layout">
            <aside class="settings-overview-rail">
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
            </aside>

            <div class="settings-workspace">
              <section class="settings-block">
                <div class="settings-block__head">
                  <div>
                    <h4>模型接入 Key 输入</h4>
                    <p class="settings-block__hint">按厂商统一管理接入密钥，并在同一组内查看文本、视觉、视频模型。</p>
                  </div>
                  <span class="surface-chip">{{ providerRows.length }} 个</span>
                </div>

                <div class="vendor-groups">
                  <section v-for="group in groupedProviders" :key="group.vendor" class="vendor-group">
                    <div class="vendor-group__head">
                      <div>
                        <p class="provider-card__eyebrow">厂商</p>
                        <h5>{{ group.title }}</h5>
                      </div>
                      <span class="surface-chip">{{ group.items.length }} 个接入 · {{ group.modelCount }} 个模型</span>
                    </div>

                    <div class="provider-grid">
                      <article v-for="provider in group.items" :key="provider.key" class="surface-panel provider-card">
                        <div class="provider-card__top">
                          <div class="provider-card__head">
                            <div>
                              <p class="provider-card__eyebrow">{{ provider.key }}</p>
                              <h5>{{ provider.provider || provider.key }}</h5>
                            </div>
                            <span class="status-pill" :class="resolveProviderStatus(provider).tone">
                              {{ resolveProviderStatus(provider).label }}
                            </span>
                          </div>

                          <label class="settings-field provider-card__field">
                            <span>API Key</span>
                            <input
                              v-model="providerDrafts[provider.draftIndex].apiKey"
                              class="field-input"
                              type="password"
                              :placeholder="provider.apiKeyConfigured ? '已存在 key，留空表示不修改' : '请输入新的 API Key'"
                            />
                          </label>
                        </div>

                        <div class="provider-card__facts">
                          <div class="provider-card__fact">
                            <span>厂商</span>
                            <strong>{{ group.title }}</strong>
                          </div>
                          <div class="provider-card__fact">
                            <span>Endpoint Host</span>
                            <strong>{{ provider.endpointHost || "未配置" }}</strong>
                          </div>
                          <div v-if="shouldShowProviderTaskHost(provider)" class="provider-card__fact">
                            <span>Task Host</span>
                            <strong>{{ provider.taskEndpointHost || "未配置" }}</strong>
                          </div>
                          <div class="provider-card__fact">
                            <span>模型数</span>
                            <strong>{{ provider.modelNames.length }}</strong>
                          </div>
                          <div class="provider-card__fact">
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

                    <div v-if="group.modelSections.length" class="vendor-model-sections">
                      <section v-for="section in group.modelSections" :key="`${group.vendor}-${section.key}`" class="surface-panel vendor-model-section">
                        <div class="vendor-model-section__head">
                          <div>
                            <p class="provider-card__eyebrow">模型类型</p>
                            <h6>{{ section.title }}</h6>
                          </div>
                          <span class="surface-chip">{{ section.items.length }} 个</span>
                        </div>

                        <div class="model-list">
                          <div v-for="item in section.items" :key="`${group.vendor}-${section.key}-${item.name}`" class="model-item">
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

                            <div class="model-detail-chips">
                              <div class="model-detail-chip">
                                <span>模型接入</span>
                                <strong>{{ item.provider || "-" }}</strong>
                              </div>
                              <div class="model-detail-chip">
                                <span>Family</span>
                                <strong>{{ item.family || "-" }}</strong>
                              </div>
                              <div class="model-detail-chip">
                                <span>Endpoint Host</span>
                                <strong>{{ item.endpointHost || "-" }}</strong>
                              </div>
                              <div v-if="shouldShowModelTaskHost(item)" class="model-detail-chip">
                                <span>Task Host</span>
                                <strong>{{ item.taskEndpointHost || "-" }}</strong>
                              </div>
                            </div>

                            <div class="chip-list">
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
                  </section>
                </div>
              </section>
            </div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import HintBell from "@/components/HintBell.vue";
import { messageApi } from "@/composables/useMessage";
import { fetchUserModelConfig, saveUserModelConfigKeys, validateUserModelConfig } from "@/api/auth";
import type {
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigModelItem,
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
  modelCount: number;
  modelSections: Array<{
    key: string;
    title: string;
    items: AdminModelConfigModelItem[];
  }>;
}

const runtimeConfig = ref<AdminModelConfigResponse | null>(null);
const providerDrafts = ref<ProviderKeyDraftRow[]>([]);
const validationResult = ref<AdminModelConfigValidationResponse | null>(null);
const loading = ref(false);
const validating = ref(false);
const saving = ref(false);
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
  const providerBuckets = new Map<string, ProviderViewRow[]>();
  for (const provider of providerRows.value) {
    const key = normalizeVendor(provider.vendor);
    const current = providerBuckets.get(key) ?? [];
    current.push(provider);
    providerBuckets.set(key, current);
  }

  const modelBuckets = new Map<string, AdminModelConfigModelItem[]>();
  for (const model of displayedConfig.value?.models ?? []) {
    const key = normalizeVendor(model.vendor);
    const current = modelBuckets.get(key) ?? [];
    current.push(model);
    modelBuckets.set(key, current);
  }

  const sectionDefinitions: Array<{
    key: string;
    title: string;
    matcher: (item: AdminModelConfigModelItem) => boolean;
  }> = [
    { key: "text", title: "文本模型", matcher: (item) => item.kind === "text" },
    { key: "visual", title: "视觉模型", matcher: (item) => item.kind === "vision" || item.kind === "image" },
    { key: "video", title: "视频模型", matcher: (item) => item.kind === "video" },
  ];

  const vendors = new Set<string>([...providerBuckets.keys(), ...modelBuckets.keys()]);
  return Array.from(vendors)
    .map((vendor) => {
      const items = (providerBuckets.get(vendor) ?? []).slice().sort((left, right) => left.key.localeCompare(right.key));
      const vendorModels = (modelBuckets.get(vendor) ?? []).slice().sort((left, right) => left.name.localeCompare(right.name));
      return {
        vendor,
        title: formatVendor(vendor),
        items,
        modelCount: vendorModels.length,
        modelSections: sectionDefinitions
          .map((section) => ({
            key: section.key,
            title: section.title,
            items: vendorModels.filter(section.matcher),
          }))
          .filter((section) => section.items.length > 0),
      };
    })
    .sort((left, right) => left.title.localeCompare(right.title));
});

const configuredProviderCount = computed(() => {
  return providerRows.value.filter((item) => item.apiKeyConfigured).length;
});

const pendingUpdateCount = computed(() => {
  return providerDrafts.value.filter((item) => item.apiKey.trim()).length;
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

function normalizeVendor(vendor: string) {
  const normalized = vendor.trim().toLowerCase();
  return normalized || "unknown";
}

function formatVendor(vendor: string) {
  switch (normalizeVendor(vendor)) {
    case "deepseek":
      return "DeepSeek";
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

function shouldShowProviderTaskHost(provider: Pick<ProviderViewRow, "kinds">) {
  return provider.kinds.includes("video");
}

function shouldShowModelTaskHost(model: Pick<AdminModelConfigModelItem, "kind">) {
  return model.kind === "video";
}

function resetDraft() {
  if (!runtimeConfig.value) {
    return;
  }
  providerDrafts.value = toKeyDraft(runtimeConfig.value);
  validationResult.value = null;
  successMessage.value = "";
}

async function loadConfig() {
  loading.value = true;
  successMessage.value = "";
  try {
    const response = await fetchUserModelConfig();
    runtimeConfig.value = response;
    providerDrafts.value = toKeyDraft(response);
    validationResult.value = null;
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "读取模型配置失败");
  } finally {
    loading.value = false;
  }
}

async function validateDraft() {
  if (!runtimeConfig.value) {
    return;
  }
  validating.value = true;
  successMessage.value = "";
  try {
    validationResult.value = await validateUserModelConfig(buildRequest());
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "密钥校验失败");
  } finally {
    validating.value = false;
  }
}

async function saveDraft() {
  if (!runtimeConfig.value || pendingUpdateCount.value === 0) {
    return;
  }
  saving.value = true;
  successMessage.value = "";
  try {
    const response = await saveUserModelConfigKeys(buildRequest());
    runtimeConfig.value = response;
    providerDrafts.value = toKeyDraft(response);
    validationResult.value = null;
    successMessage.value = "API Key 已保存，并刷新了当前运行时配置。";
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "保存 API Key 失败");
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

.settings-layout {
  display: grid;
  grid-template-columns: minmax(260px, 300px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.settings-overview-rail {
  display: grid;
  gap: 16px;
  position: sticky;
  top: 0;
}

.settings-workspace {
  display: grid;
  gap: 16px;
  min-width: 0;
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
  grid-template-columns: 1fr;
  gap: 12px;
}

.summary-card,
.provider-card,
.model-group-card {
  padding: 16px;
}

.summary-card {
  display: grid;
  gap: 6px;
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
  gap: 8px;
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
  align-items: flex-start;
}

.settings-block__head h4 {
  margin: 0;
  font-size: 1.15rem;
}

.settings-block__hint {
  margin: 0.42rem 0 0;
  color: var(--text-body);
  line-height: 1.6;
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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

.vendor-model-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}

.vendor-model-section {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 16px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.02)),
    rgba(20, 23, 34, 0.9);
}

.vendor-model-section__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.vendor-model-section__head h6 {
  margin: 0.45rem 0 0;
  font-size: 1rem;
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
  align-content: start;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.model-vendor-group:first-child {
  padding-top: 0;
  border-top: 0;
}

.model-vendor-groups {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.provider-card,
.model-group-card {
  display: grid;
  gap: 12px;
}

.provider-card {
  align-content: start;
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.02)),
    rgba(24, 27, 39, 0.88);
}

.provider-card__top {
  display: grid;
  gap: 12px;
  align-items: start;
  padding-bottom: 2px;
}

.provider-card__head,
.model-group-card__head,
.model-item__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.provider-card__head h5,
.model-group-card__head h5 {
  margin: 0.45rem 0 0;
  font-size: 1.2rem;
}

.provider-card__field {
  align-content: start;
}

.provider-card__field span {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.provider-card__field .field-input {
  min-height: 54px;
}

.provider-card__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.provider-card__fact {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(145, 180, 255, 0.1);
  background: rgba(8, 11, 18, 0.5);
}

.provider-card__fact span {
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.provider-card__fact strong {
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.98rem;
  line-height: 1.4;
  word-break: break-word;
}

.provider-card__models {
  display: grid;
  gap: 8px;
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
  min-height: 28px;
  padding: 0 0.72rem;
  border-radius: 12px;
  border: 1px solid rgba(145, 180, 255, 0.22);
  background: rgba(8, 11, 18, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 10px 24px rgba(0, 0, 0, 0.16);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.model-list {
  display: grid;
  gap: 12px;
}

.model-item {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(145, 180, 255, 0.08);
  background: rgba(8, 11, 18, 0.42);
}

.model-item:first-child {
  padding-top: 14px;
  border-top: 1px solid rgba(145, 180, 255, 0.08);
}

.model-item__head strong {
  display: block;
  font-size: 1.02rem;
}

.model-item__head p,
.model-item__description {
  margin: 0.4rem 0 0;
  color: var(--text-body);
}

.model-item__description {
  line-height: 1.65;
}

.model-detail-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.model-detail-chip {
  display: grid;
  gap: 6px;
  min-width: 140px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(145, 180, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}

.model-detail-chip span {
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.model-detail-chip strong {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  line-height: 1.4;
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
  .settings-layout {
    grid-template-columns: 1fr;
  }

  .settings-overview-rail {
    position: static;
  }

  .summary-grid,
  .provider-grid,
  .model-groups {
    grid-template-columns: 1fr;
  }

  .provider-card__top,
  .provider-card__facts,
  .vendor-model-sections,
  .model-vendor-groups {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .settings-section__head,
  .settings-block__head,
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

  .provider-card__top {
    gap: 12px;
  }

  .model-detail-chip {
    min-width: 100%;
  }
}
</style>

<template>
  <Teleport to="body">
    <Transition name="key-dialog-fade">
      <div
        v-if="visible"
        class="key-dialog-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="key-dialog-title"
        @click.self="handleClose"
      >
        <section class="key-dialog">
          <header class="key-dialog__head">
            <h2 id="key-dialog-title">API Key 管理</h2>
            <button class="key-dialog__close" type="button" aria-label="关闭" @click="handleClose">
              <IconClose size="sm" />
            </button>
          </header>

          <p class="key-dialog__hint">
            设置个人 API Key 后将优先使用，留空则使用平台默认 Key。已配置的 Key 不会显示明文，输入新值即可替换。
          </p>

          <div v-if="loading" class="key-dialog__loading">
            <IconLoading size="sm" />
            <span>加载中…</span>
          </div>

          <div v-else-if="providers.length === 0" class="key-dialog__empty">
            暂无可用的模型厂商配置
          </div>

          <div v-else class="key-dialog__list">
            <div v-for="item in providers" :key="item.key" class="key-dialog__card">
              <div class="key-dialog__card-header">
                <div class="key-dialog__card-info">
                  <strong>{{ item.vendor || item.provider || item.key }}</strong>
                  <span class="key-dialog__card-kinds">{{ item.kinds.map(formatKind).join(" / ") || "模型接入" }}</span>
                </div>
                <span
                  class="key-dialog__status"
                  :class="item.apiKeyConfigured ? 'key-dialog__status--active' : 'key-dialog__status--empty'"
                >
                  <span class="key-dialog__status-dot"></span>
                  {{ item.apiKeyConfigured ? "已配置" : "未配置" }}
                </span>
              </div>
              <label class="key-dialog__field">
                <span class="key-dialog__field-label">{{ item.vendor || item.provider || item.key }} API Key</span>
                <div class="key-dialog__input-wrap">
                  <input
                    v-model.trim="item.apiKey"
                    :type="item._showKey ? 'text' : 'password'"
                    :placeholder="item.apiKeyConfigured ? '输入新 Key 替换现有配置' : '请输入 API Key'"
                    autocomplete="off"
                  />
                  <button
                    class="key-dialog__toggle"
                    type="button"
                    :aria-label="item._showKey ? '隐藏' : '显示'"
                    @click="item._showKey = !item._showKey"
                  >
                    {{ item._showKey ? '隐藏' : '显示' }}
                  </button>
                </div>
              </label>
            </div>
          </div>

          <div class="key-dialog__actions">
            <button class="key-dialog__btn key-dialog__btn--cancel" type="button" @click="handleClose">取消</button>
            <button class="key-dialog__btn key-dialog__btn--save" type="button" :disabled="saving" @click="handleSave">
              <IconLoading v-if="saving" size="sm" />
              <span>{{ saving ? "保存中…" : "保存" }}</span>
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * API Key 管理弹窗 — 纯 CSS 实现，不依赖 Element Plus。
 */
import { ref, watch } from "vue";
import { fetchUserModelConfig, saveUserModelConfigKeys } from "@/api/auth";
import type { AdminModelConfigProviderItem } from "@/types";
import { IconClose, IconLoading } from "@/components/icons";
import { messageApi } from "@/composables/useMessage";

interface ProviderState extends AdminModelConfigProviderItem {
  apiKey: string;
  _showKey: boolean;
}

const visible = defineModel<boolean>({ default: false });

const loading = ref(false);
const saving = ref(false);
const providers = ref<ProviderState[]>([]);

watch(visible, (val) => {
  if (val) {
    loadConfig();
  }
});

async function loadConfig() {
  loading.value = true;
  try {
    const response = await fetchUserModelConfig();
    providers.value = (response.providers ?? []).map((p) => ({
      ...p,
      apiKey: "",
      _showKey: false,
    }));
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "读取模型配置失败");
  } finally {
    loading.value = false;
  }
}

async function handleSave() {
  const updates = providers.value
    .map((p) => ({ key: p.key, apiKey: p.apiKey.trim() }))
    .filter((p) => p.apiKey);

  if (updates.length === 0) {
    messageApi.error("请至少输入一个 API Key");
    return;
  }

  saving.value = true;
  try {
    await saveUserModelConfigKeys({ providers: updates });
    messageApi.success("Key 已保存");
    visible.value = false;
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "保存 Key 失败");
  } finally {
    saving.value = false;
  }
}

function handleClose() {
  if (saving.value) return;
  visible.value = false;
  providers.value = [];
}

function formatKind(kind: string) {
  const normalized = kind.trim().toLowerCase();
  if (normalized === "text") return "文本";
  if (normalized === "image") return "图片";
  if (normalized === "video") return "视频";
  return kind;
}
</script>

<style scoped>
.key-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: grid;
  place-items: center;
  padding: 18px;
  background: rgba(15, 20, 25, 0.42);
  backdrop-filter: blur(14px);
}

.key-dialog {
  width: min(560px, 100%);
  max-height: min(680px, calc(100dvh - 36px));
  overflow: auto;
  display: grid;
  gap: 16px;
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 56px rgba(15, 20, 25, 0.14);
  backdrop-filter: blur(20px);
}

.key-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.key-dialog__head h2 {
  margin: 0;
  color: var(--text-strong);
  font-size: 1.18rem;
  font-weight: 850;
}

.key-dialog__close {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border: 0;
  border-radius: 11px;
  background: #f1f4f6;
  color: var(--text-body);
  line-height: 0;
  cursor: pointer;
}

.key-dialog__close:hover {
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(15, 20, 25, 0.08);
}

.key-dialog__hint {
  margin: 0;
  color: var(--text-body);
  font-size: 0.82rem;
  line-height: 1.6;
}

.key-dialog__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  color: var(--text-body);
  font-size: 0.88rem;
}

.key-dialog__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  color: var(--text-body);
  font-size: 0.88rem;
}

.key-dialog__list {
  display: grid;
  gap: 12px;
  max-height: 50vh;
  overflow: auto;
  padding-right: 4px;
}

.key-dialog__card {
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: rgba(255, 255, 255, 0.72);
  transition: border-color 0.2s;
}

.key-dialog__card:hover {
  border-color: rgba(15, 20, 25, 0.12);
}

.key-dialog__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.key-dialog__card-info {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.key-dialog__card-info strong {
  font-size: 0.92rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.key-dialog__card-kinds {
  color: var(--text-body);
  font-size: 0.78rem;
  white-space: nowrap;
}

.key-dialog__status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  font-size: 0.76rem;
  font-weight: 700;
}

.key-dialog__status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.key-dialog__status--active {
  color: #23c778;
}

.key-dialog__status--active .key-dialog__status-dot {
  background: #23c778;
  box-shadow: 0 0 4px rgba(35, 199, 120, 0.4);
}

.key-dialog__status--empty {
  color: var(--text-body);
  opacity: 0.5;
}

.key-dialog__status--empty .key-dialog__status-dot {
  background: var(--text-body);
}

.key-dialog__field {
  display: grid;
  gap: 6px;
}

.key-dialog__field-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.key-dialog__input-wrap {
  position: relative;
}

.key-dialog__input-wrap input {
  width: 100%;
  min-height: 42px;
  padding: 0 60px 0 13px;
  border-radius: 12px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: rgba(255, 255, 255, 0.92);
  color: var(--text-strong);
  font-size: 0.86rem;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.key-dialog__input-wrap input:focus {
  border-color: rgba(0, 169, 187, 0.42);
  box-shadow:
    0 0 0 3px rgba(0, 169, 187, 0.1),
    0 10px 24px rgba(27, 124, 255, 0.06);
  outline: none;
}

.key-dialog__input-wrap input::placeholder {
  color: var(--text-body);
  opacity: 0.5;
}

.key-dialog__toggle {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
  min-height: 30px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #f3f6f8;
  color: var(--text-body);
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}

.key-dialog__toggle:hover {
  background: #edf5ff;
  color: var(--accent-blue);
}

.key-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

.key-dialog__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: 14px;
  font-size: 0.86rem;
  font-weight: 820;
  cursor: pointer;
  transition: box-shadow 180ms ease, transform 180ms ease, opacity 180ms ease;
}

.key-dialog__btn--cancel {
  background: #f3f6f8;
  color: var(--text-body);
}

.key-dialog__btn--cancel:hover {
  background: #e8ecef;
}

.key-dialog__btn--save {
  background: var(--bg-accent);
  color: #fff;
  box-shadow: 0 12px 26px rgba(27, 124, 255, 0.18);
}

.key-dialog__btn--save:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(27, 124, 255, 0.22);
}

.key-dialog__btn--save:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

/* Transition */
.key-dialog-fade-enter-active,
.key-dialog-fade-leave-active {
  transition: opacity 160ms ease;
}

.key-dialog-fade-enter-active .key-dialog,
.key-dialog-fade-leave-active .key-dialog {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.key-dialog-fade-enter-from,
.key-dialog-fade-leave-to {
  opacity: 0;
}

.key-dialog-fade-enter-from .key-dialog,
.key-dialog-fade-leave-to .key-dialog {
  transform: translateY(8px) scale(0.985);
}

@media (max-width: 520px) {
  .key-dialog-backdrop {
    align-items: end;
    padding: 14px;
  }

  .key-dialog {
    width: 100%;
    max-height: min(680px, calc(100dvh - 72px));
    padding: 20px 16px 16px;
    border-radius: 22px;
  }

  .key-dialog::before {
    content: "";
    justify-self: center;
    width: 38px;
    height: 4px;
    margin: -9px 0 2px;
    border-radius: 999px;
    background: rgba(15, 20, 25, 0.16);
  }

  .key-dialog__card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
}
</style>

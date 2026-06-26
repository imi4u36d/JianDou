<template>
  <Teleport to="body">
    <Transition name="credit-dialog-fade">
      <div
        v-if="modelValue"
        class="credit-dialog-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="credit-dialog-title"
        @click.self="close"
        @keydown.esc.stop.prevent="handleEscape"
      >
        <section class="credit-dialog">
          <header class="credit-dialog__head">
            <div>
              <p class="credit-dialog__eyebrow">积分账户</p>
              <h2 id="credit-dialog-title">积分明细</h2>
            </div>
            <button class="credit-dialog__close" type="button" aria-label="关闭积分明细" @click="close">
              <IconClose size="sm" />
            </button>
          </header>

          <div class="credit-dialog__summary">
            <article class="credit-dialog__metric">
              <span>当前积分</span>
              <strong>{{ balanceLabel }}</strong>
            </article>
            <article class="credit-dialog__metric">
              <span>累计消耗</span>
              <strong>{{ formatNumber(summary?.totalConsumed ?? 0) }}</strong>
            </article>
            <article class="credit-dialog__metric">
              <span>累计调整</span>
              <strong>{{ formatSignedNumber(summary?.totalAdjusted ?? 0) }}</strong>
            </article>
          </div>

          <div class="credit-dialog__toolbar">
            <button v-if="!summary?.exempt" class="credit-dialog__recharge" type="button" @click="openRecharge">
              充值
            </button>
            <p v-else class="credit-dialog__exempt-note">管理员账号积分免扣，无需充值。</p>
            <button class="credit-dialog__refresh" type="button" :disabled="loading" @click="refresh">
              <IconLoading v-if="loading" size="xs" />
              <IconRefresh v-else size="xs" />
              刷新
            </button>
          </div>

          <section class="credit-dialog__ledger" aria-label="积分使用明细">
            <div class="credit-dialog__ledger-head">
              <h3>使用明细</h3>
              <span>{{ totalLabel }}</span>
            </div>

            <div v-if="errorMessage" class="credit-dialog__notice credit-dialog__notice-error">
              {{ errorMessage }}
            </div>
            <div v-else-if="loading && transactions.length === 0" class="credit-dialog__notice">
              正在读取积分明细
            </div>
            <div v-else-if="transactions.length === 0" class="credit-dialog__empty">
              暂无积分使用记录
            </div>
            <div v-else class="credit-dialog__table-wrap">
              <table class="credit-dialog__table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>类型</th>
                    <th class="credit-dialog__numeric">变动</th>
                    <th class="credit-dialog__numeric">余额</th>
                    <th>功能</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in transactions" :key="item.transactionId">
                    <td>{{ formatDateTime(item.createdAt) }}</td>
                    <td>
                      <span class="credit-dialog__tag" :class="item.amountDelta >= 0 ? 'credit-dialog__tag-positive' : 'credit-dialog__tag-negative'">
                        {{ transactionTypeLabel(item.transactionType) }}
                      </span>
                    </td>
                    <td class="credit-dialog__numeric" :class="item.amountDelta >= 0 ? 'credit-dialog__positive' : 'credit-dialog__negative'">
                      {{ formatSignedNumber(item.amountDelta) }}
                    </td>
                    <td class="credit-dialog__numeric">{{ formatNumber(item.balanceAfter) }}</td>
                    <td>{{ featureLabel(item.featureCode) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <footer class="credit-dialog__pager">
            <button type="button" :disabled="!canGoPrev || loading" @click="goPrev">上一页</button>
            <span>{{ pageLabel }}</span>
            <button type="button" :disabled="!canGoNext || loading" @click="goNext">下一页</button>
          </footer>
        </section>

        <Transition name="credit-recharge-fade">
          <div
            v-if="rechargeOpen"
            class="credit-recharge"
            role="dialog"
            aria-modal="true"
            aria-labelledby="credit-recharge-title"
            @click.self="closeRecharge"
          >
            <section class="credit-recharge__panel">
              <header class="credit-recharge__head">
                <h3 id="credit-recharge-title">充值积分</h3>
                <button type="button" aria-label="关闭充值弹窗" @click="closeRecharge">
                  <IconClose size="xs" />
                </button>
              </header>
              <p>加群联系群主获取积分。</p>
              <div class="credit-recharge__group">
                <span>QQ群</span>
                <strong>{{ qqGroup }}</strong>
              </div>
              <button class="credit-recharge__copy" type="button" @click="copyQqGroup">
                {{ copyStatus || "复制群号" }}
              </button>
            </section>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fetchCreditSummary, fetchCreditTransactions } from "@/api/credits";
import type { CreditSummary, CreditTransaction, CreditTransactionType } from "@/types";
import { IconClose, IconLoading, IconRefresh } from "@/components/icons";

const props = defineProps<{
  modelValue: boolean;
  initialSummary?: CreditSummary | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const qqGroup = "1090387362";
const pageSize = 8;

const summary = ref<CreditSummary | null>(props.initialSummary ?? null);
const transactions = ref<CreditTransaction[]>([]);
const total = ref(0);
const offset = ref(0);
const loading = ref(false);
const errorMessage = ref("");
const rechargeOpen = ref(false);
const copyStatus = ref("");

const balanceLabel = computed(() => {
  if (summary.value?.exempt) {
    return "免扣";
  }
  return formatNumber(summary.value?.balance ?? 0);
});
const pageNumber = computed(() => Math.floor(offset.value / pageSize) + 1);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const canGoPrev = computed(() => offset.value > 0);
const canGoNext = computed(() => offset.value + pageSize < total.value);
const pageLabel = computed(() => `${pageNumber.value} / ${totalPages.value}`);
const totalLabel = computed(() => (total.value > 0 ? `共 ${total.value} 条` : "无记录"));

watch(
  () => props.initialSummary,
  (value) => {
    if (value) {
      summary.value = value;
    }
  },
);

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      rechargeOpen.value = false;
      return;
    }
    offset.value = 0;
    copyStatus.value = "";
    void refresh();
  },
);

function close() {
  emit("update:modelValue", false);
}

function openRecharge() {
  copyStatus.value = "";
  rechargeOpen.value = true;
}

function closeRecharge() {
  rechargeOpen.value = false;
}

function handleEscape() {
  if (rechargeOpen.value) {
    closeRecharge();
    return;
  }
  close();
}

async function refresh() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const [nextSummary, page] = await Promise.all([
      fetchCreditSummary(),
      fetchCreditTransactions({ offset: offset.value, limit: pageSize }),
    ]);
    summary.value = nextSummary;
    transactions.value = page.items;
    total.value = page.total;
    offset.value = page.offset;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取积分明细失败";
  } finally {
    loading.value = false;
  }
}

function goPrev() {
  if (!canGoPrev.value) {
    return;
  }
  offset.value = Math.max(0, offset.value - pageSize);
  void refresh();
}

function goNext() {
  if (!canGoNext.value) {
    return;
  }
  offset.value += pageSize;
  void refresh();
}

async function copyQqGroup() {
  try {
    if (!navigator.clipboard) {
      copyStatus.value = "群号在上方";
      return;
    }
    await navigator.clipboard.writeText(qqGroup);
    copyStatus.value = "已复制";
  } catch {
    copyStatus.value = "群号在上方";
  }
}

function formatNumber(value: number | null | undefined) {
  const numeric = Number(value ?? 0);
  return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2).replace(/\.?0+$/, "");
}

function formatSignedNumber(value: number) {
  if (value > 0) {
    return `+${formatNumber(value)}`;
  }
  return formatNumber(value);
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function featureLabel(value?: string | null) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (normalized === "IMAGE_GENERATION") {
    return "图片生成";
  }
  if (normalized === "VIDEO_GENERATION") {
    return "视频生成";
  }
  return normalized || "--";
}

function transactionTypeLabel(value: CreditTransactionType) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (normalized === "CONSUME") {
    return "消耗";
  }
  if (normalized === "USAGE") {
    return "使用";
  }
  if (normalized === "REFUND") {
    return "退还";
  }
  if (normalized === "ADJUST") {
    return "调整";
  }
  return normalized || "--";
}
</script>

<style scoped>
.credit-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(34px) saturate(1.7);
  -webkit-backdrop-filter: blur(34px) saturate(1.7);
}

.credit-dialog {
  width: min(780px, 100%);
  max-height: min(720px, calc(100vh - 48px));
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--text-strong);
  box-shadow: 0 26px 70px rgba(15, 23, 42, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.96);
  overflow: hidden;
}

.credit-dialog__head,
.credit-dialog__toolbar,
.credit-dialog__ledger-head,
.credit-dialog__pager,
.credit-recharge__head {
  display: flex;
  align-items: center;
}

.credit-dialog__head {
  justify-content: space-between;
  gap: 16px;
}

.credit-dialog__eyebrow,
.credit-dialog__head h2,
.credit-dialog__ledger-head h3,
.credit-recharge__head h3,
.credit-recharge p {
  margin: 0;
}

.credit-dialog__eyebrow {
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.credit-dialog__head h2 {
  margin-top: 3px;
  font-size: 1.18rem;
  font-weight: 900;
  line-height: 1.25;
}

.credit-dialog__close,
.credit-recharge__head button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-body);
  cursor: pointer;
}

.credit-dialog__close:hover,
.credit-recharge__head button:hover {
  background: rgba(0, 0, 0, 0.08);
}

.credit-dialog__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.credit-dialog__metric {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 13px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.62);
}

.credit-dialog__metric span {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 760;
}

.credit-dialog__metric strong {
  overflow: hidden;
  color: var(--accent-blue);
  font-size: 1.24rem;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.credit-dialog__toolbar {
  justify-content: space-between;
  gap: 10px;
}

.credit-dialog__exempt-note {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 820;
  line-height: 1.5;
}

.credit-dialog__recharge,
.credit-dialog__refresh,
.credit-dialog__pager button,
.credit-recharge__copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  border: 0;
  border-radius: 12px;
  font-size: 0.82rem;
  font-weight: 850;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.credit-dialog__recharge {
  padding: 0 18px;
  background: var(--bg-accent);
  color: #fff;
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.22);
}

.credit-dialog__refresh,
.credit-dialog__pager button {
  gap: 6px;
  padding: 0 12px;
  background: rgba(0, 0, 0, 0.045);
  color: var(--text-body);
}

.credit-dialog__recharge:hover,
.credit-dialog__refresh:hover:not(:disabled),
.credit-dialog__pager button:hover:not(:disabled),
.credit-recharge__copy:hover {
  transform: translateY(-1px);
}

.credit-dialog__refresh:disabled,
.credit-dialog__pager button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
  transform: none;
}

.credit-dialog__ledger {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}

.credit-dialog__ledger-head {
  justify-content: space-between;
  gap: 12px;
}

.credit-dialog__ledger-head h3 {
  font-size: 0.92rem;
  font-weight: 900;
}

.credit-dialog__ledger-head span {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 760;
}

.credit-dialog__notice,
.credit-dialog__empty {
  display: grid;
  place-items: center;
  min-height: 176px;
  border: 1px dashed rgba(15, 23, 42, 0.1);
  border-radius: 16px;
  color: var(--text-muted);
  font-size: 0.86rem;
  font-weight: 760;
}

.credit-dialog__notice-error {
  color: var(--accent-danger);
}

.credit-dialog__table-wrap {
  min-height: 0;
  overflow: auto;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.46);
}

.credit-dialog__table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.credit-dialog__table th,
.credit-dialog__table td {
  padding: 11px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  text-align: left;
  white-space: nowrap;
}

.credit-dialog__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(255, 255, 255, 0.94);
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 850;
}

.credit-dialog__table tr:last-child td {
  border-bottom: 0;
}

.credit-dialog__numeric {
  text-align: right !important;
}

.credit-dialog__tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 850;
}

.credit-dialog__tag-positive {
  background: rgba(22, 163, 74, 0.1);
  color: #15803d;
}

.credit-dialog__tag-negative {
  background: rgba(229, 72, 101, 0.1);
  color: var(--accent-coral);
}

.credit-dialog__positive {
  color: #15803d;
  font-weight: 850;
}

.credit-dialog__negative {
  color: var(--accent-coral);
  font-weight: 850;
}

.credit-dialog__pager {
  justify-content: flex-end;
  gap: 10px;
}

.credit-dialog__pager span {
  min-width: 54px;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 820;
  text-align: center;
}

.credit-recharge {
  position: fixed;
  inset: 0;
  z-index: 1510;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.18);
}

.credit-recharge__panel {
  width: min(360px, 100%);
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 22px 56px rgba(15, 23, 42, 0.16);
}

.credit-recharge__head {
  justify-content: space-between;
  gap: 12px;
}

.credit-recharge__head h3 {
  font-size: 1rem;
  font-weight: 900;
}

.credit-recharge p {
  color: var(--text-body);
  font-size: 0.88rem;
  line-height: 1.6;
}

.credit-recharge__group {
  display: grid;
  gap: 5px;
  padding: 13px;
  border-radius: 15px;
  background: rgba(99, 102, 241, 0.08);
}

.credit-recharge__group span {
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.credit-recharge__group strong {
  color: var(--accent-blue);
  font-size: 1.3rem;
  font-weight: 900;
  letter-spacing: 0;
}

.credit-recharge__copy {
  width: 100%;
  background: var(--bg-accent);
  color: #fff;
}

.credit-dialog-fade-enter-active,
.credit-dialog-fade-leave-active,
.credit-recharge-fade-enter-active,
.credit-recharge-fade-leave-active {
  transition: opacity 160ms ease;
}

.credit-dialog-fade-enter-active .credit-dialog,
.credit-dialog-fade-leave-active .credit-dialog,
.credit-recharge-fade-enter-active .credit-recharge__panel,
.credit-recharge-fade-leave-active .credit-recharge__panel {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.credit-dialog-fade-enter-from,
.credit-dialog-fade-leave-to,
.credit-recharge-fade-enter-from,
.credit-recharge-fade-leave-to {
  opacity: 0;
}

.credit-dialog-fade-enter-from .credit-dialog,
.credit-dialog-fade-leave-to .credit-dialog,
.credit-recharge-fade-enter-from .credit-recharge__panel,
.credit-recharge-fade-leave-to .credit-recharge__panel {
  transform: translateY(10px) scale(0.985);
}

@media (max-width: 640px) {
  .credit-dialog-backdrop {
    align-items: end;
    padding: 12px;
  }

  .credit-dialog {
    width: 100%;
    max-height: calc(100vh - 24px);
    border-radius: 20px;
    padding: 14px;
  }

  .credit-dialog__summary {
    grid-template-columns: 1fr;
  }

  .credit-dialog__metric {
    grid-template-columns: 1fr auto;
    align-items: center;
  }

  .credit-dialog__metric strong {
    max-width: 150px;
    font-size: 1.05rem;
    text-align: right;
  }

  .credit-dialog__pager {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
  }

  .credit-recharge {
    align-items: end;
    padding: 12px;
  }

  .credit-recharge__panel {
    width: 100%;
  }
}
</style>

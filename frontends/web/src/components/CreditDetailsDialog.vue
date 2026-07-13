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
import type { CreditSummary, CreditTransaction } from "@/types";
import { featureLabel, formatDateTime, formatNumber, formatSignedNumber, transactionTypeLabel } from "@/features/credits/credit-details-presenters";
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

</script>

<style scoped src="./credit-details-dialog.css"></style>

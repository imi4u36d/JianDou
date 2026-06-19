<template>
  <section class="credit-page">
    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="credit-page__toolbar">
          <div>
            <h3>用户积分</h3>
          </div>
          <el-button :icon="Refresh" plain @click="refreshActiveTab">刷新</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="credit-page__tabs" @tab-change="handleTabChange">
        <el-tab-pane label="用户积分" name="users">
          <el-form class="credit-page__filters" inline @submit.prevent="loadCreditUsers">
            <el-form-item label="关键词">
              <el-input v-model.trim="userFilters.q" clearable placeholder="用户名 / 显示名" />
            </el-form-item>
            <el-form-item class="credit-page__filters-action">
              <el-button :loading="loadingUsers" native-type="submit" type="primary">查询</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="userErrorMessage"
            :closable="false"
            class="credit-page__alert"
            show-icon
            type="error"
            :title="userErrorMessage"
          />

          <el-table v-loading="loadingUsers" :data="creditUsers" class="credit-page__table">
            <el-table-column label="用户" min-width="180">
              <template #default="{ row }">
                <div class="credit-page__primary-cell">
                  <strong>{{ row.displayName || row.username }}</strong>
                  <span>{{ row.username }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column align="right" label="当前积分" min-width="120" prop="balance" />
            <el-table-column align="right" label="累计消耗" min-width="120" prop="totalConsumed" />
            <el-table-column align="right" label="累计调整" min-width="120" prop="totalAdjusted" />
            <el-table-column align="right" label="图片次数" min-width="110" prop="imageGenerationCount" />
            <el-table-column align="right" label="视频次数" min-width="110" prop="videoGenerationCount" />
            <el-table-column label="最近使用" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.lastUsedAt) }}
              </template>
            </el-table-column>
            <el-table-column align="right" fixed="right" label="操作" min-width="170">
              <template #default="{ row }">
                <div class="credit-page__actions">
                  <el-button link type="primary" @click="openTransactionDialog(row)">流水</el-button>
                  <el-button link type="warning" @click="openAdjustDialog(row)">调整</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="消耗规则" name="rules">
          <el-alert
            v-if="ruleErrorMessage"
            :closable="false"
            class="credit-page__alert"
            show-icon
            type="error"
            :title="ruleErrorMessage"
          />

          <el-table v-loading="loadingRules" :data="creditRules" class="credit-page__table">
            <el-table-column label="功能" min-width="180">
              <template #default="{ row }">
                <div class="credit-page__primary-cell">
                  <strong>{{ row.displayName || row.featureCode }}</strong>
                  <span>{{ row.featureCode }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column align="right" label="单次消耗" min-width="120" prop="cost" />
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column align="right" fixed="right" label="操作" min-width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRuleDialog(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="transactionDialogVisible" :title="transactionDialogTitle" width="900px">
      <el-table v-loading="loadingTransactions" :data="transactions" class="credit-page__table">
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="类型" min-width="120">
          <template #default="{ row }">
            <el-tag :type="transactionTagType(row.amountDelta)" effect="light">
              {{ transactionTypeLabel(row.transactionType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column align="right" label="变动" min-width="100">
          <template #default="{ row }">
            <span :class="row.amountDelta >= 0 ? 'credit-page__positive' : 'credit-page__negative'">
              {{ formatSignedNumber(row.amountDelta) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column align="right" label="变动前" min-width="100" prop="balanceBefore" />
        <el-table-column align="right" label="变动后" min-width="100" prop="balanceAfter" />
        <el-table-column label="功能" min-width="130" prop="featureCode" />
        <el-table-column label="原因" min-width="220" prop="reason" show-overflow-tooltip />
      </el-table>
    </el-dialog>

    <el-dialog v-model="adjustDialogVisible" :title="adjustDialogTitle" width="460px">
      <el-form label-position="top">
        <el-form-item label="调整数量">
          <el-input-number v-model="adjustForm.amount" :step="10" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="调整原因">
          <el-input
            v-model.trim="adjustForm.reason"
            maxlength="200"
            placeholder="调整原因"
            show-word-limit
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button :loading="submittingAdjustment" type="primary" @click="submitAdjustment">保存调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ruleDialogVisible" :title="ruleDialogTitle" width="420px">
      <el-form label-position="top">
        <el-form-item label="单次消耗积分">
          <el-input-number v-model="ruleForm.cost" :min="0" :step="5" controls-position="right" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button :loading="submittingRule" type="primary" @click="submitRule">保存规则</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import {
  adjustAdminUserCredits,
  fetchAdminCreditRules,
  fetchAdminCreditTransactions,
  fetchAdminCreditUsers,
  updateAdminCreditRule
} from "@/admin/features/credits/services/creditService";
import type { AdminCreditRule, AdminCreditTransaction, AdminCreditUser } from "@/types";

const activeTab = ref<"users" | "rules">("users");
const loadingUsers = ref(false);
const loadingRules = ref(false);
const loadingTransactions = ref(false);
const submittingAdjustment = ref(false);
const submittingRule = ref(false);
const userErrorMessage = ref("");
const ruleErrorMessage = ref("");
const creditUsers = ref<AdminCreditUser[]>([]);
const creditRules = ref<AdminCreditRule[]>([]);
const transactions = ref<AdminCreditTransaction[]>([]);
const selectedUser = ref<AdminCreditUser | null>(null);
const selectedRule = ref<AdminCreditRule | null>(null);
const transactionDialogVisible = ref(false);
const adjustDialogVisible = ref(false);
const ruleDialogVisible = ref(false);
const userFilters = reactive({
  q: ""
});
const adjustForm = reactive({
  amount: 0,
  reason: ""
});
const ruleForm = reactive({
  cost: 0
});

const transactionDialogTitle = computed(() => {
  if (!selectedUser.value) {
    return "积分流水";
  }
  return `积分流水 - ${selectedUser.value.displayName || selectedUser.value.username}`;
});

const adjustDialogTitle = computed(() => {
  if (!selectedUser.value) {
    return "调整积分";
  }
  return `调整积分 - ${selectedUser.value.displayName || selectedUser.value.username}`;
});

const ruleDialogTitle = computed(() => {
  if (!selectedRule.value) {
    return "编辑消耗规则";
  }
  return `编辑消耗规则 - ${selectedRule.value.displayName || selectedRule.value.featureCode}`;
});

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "未记录";
  }
  return date.toLocaleString("zh-CN");
}

function formatSignedNumber(value: number) {
  return value > 0 ? `+${value}` : `${value}`;
}

function transactionTypeLabel(type: string) {
  switch (type) {
    case "ADJUST":
      return "管理员调整";
    case "CONSUME":
      return "功能消耗";
    case "USAGE":
      return "功能使用";
    case "REFUND":
      return "退回";
    default:
      return type || "-";
  }
}

function transactionTagType(amountDelta: number) {
  return amountDelta >= 0 ? "success" : "warning";
}

async function loadCreditUsers() {
  loadingUsers.value = true;
  userErrorMessage.value = "";
  try {
    creditUsers.value = (await fetchAdminCreditUsers(userFilters)) ?? [];
  } catch (error) {
    userErrorMessage.value = error instanceof Error ? error.message : "读取用户积分失败";
  } finally {
    loadingUsers.value = false;
  }
}

async function loadCreditRules() {
  loadingRules.value = true;
  ruleErrorMessage.value = "";
  try {
    creditRules.value = (await fetchAdminCreditRules()) ?? [];
  } catch (error) {
    ruleErrorMessage.value = error instanceof Error ? error.message : "读取积分规则失败";
  } finally {
    loadingRules.value = false;
  }
}

async function refreshActiveTab() {
  if (activeTab.value === "rules") {
    await loadCreditRules();
    return;
  }
  await loadCreditUsers();
}

async function handleTabChange(name: string | number) {
  if (name === "rules" && creditRules.value.length === 0) {
    await loadCreditRules();
  }
}

async function openTransactionDialog(user: AdminCreditUser) {
  selectedUser.value = user;
  transactionDialogVisible.value = true;
  transactions.value = [];
  loadingTransactions.value = true;
  try {
    transactions.value = (await fetchAdminCreditTransactions(user.id)) ?? [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取积分流水失败");
  } finally {
    loadingTransactions.value = false;
  }
}

function openAdjustDialog(user: AdminCreditUser) {
  selectedUser.value = user;
  adjustForm.amount = 0;
  adjustForm.reason = "";
  adjustDialogVisible.value = true;
}

async function submitAdjustment() {
  if (!selectedUser.value) {
    return;
  }
  if (!Number.isFinite(adjustForm.amount) || adjustForm.amount === 0) {
    ElMessage.warning("调整数量不能为 0");
    return;
  }
  if (!adjustForm.reason.trim()) {
    ElMessage.warning("填写调整原因");
    return;
  }
  submittingAdjustment.value = true;
  try {
    const updated = await adjustAdminUserCredits(selectedUser.value.id, {
      amount: adjustForm.amount,
      reason: adjustForm.reason.trim()
    });
    const index = creditUsers.value.findIndex((item) => item.id === updated.id);
    if (index >= 0) {
      creditUsers.value.splice(index, 1, updated);
    }
    adjustDialogVisible.value = false;
    ElMessage.success("积分已调整");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "调整积分失败");
  } finally {
    submittingAdjustment.value = false;
  }
}

function openRuleDialog(rule: AdminCreditRule) {
  selectedRule.value = rule;
  ruleForm.cost = rule.cost;
  ruleDialogVisible.value = true;
}

async function submitRule() {
  if (!selectedRule.value) {
    return;
  }
  if (!Number.isFinite(ruleForm.cost) || ruleForm.cost < 0) {
    ElMessage.warning("单次消耗不能小于 0");
    return;
  }
  submittingRule.value = true;
  try {
    const updated = await updateAdminCreditRule(selectedRule.value.featureCode, {
      cost: ruleForm.cost
    });
    const index = creditRules.value.findIndex((item) => item.featureCode === updated.featureCode);
    if (index >= 0) {
      creditRules.value.splice(index, 1, updated);
    }
    ruleDialogVisible.value = false;
    ElMessage.success("积分规则已更新");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "更新积分规则失败");
  } finally {
    submittingRule.value = false;
  }
}

onMounted(async () => {
  await loadCreditUsers();
});
</script>

<style scoped>
.credit-page {
  display: grid;
  gap: 20px;
}

.credit-page > *,
.credit-page .surface-card {
  min-width: 0;
  max-width: 100%;
}

.credit-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.credit-page__toolbar h3 {
  margin: 0;
  font-family: inherit;
}

.credit-page__tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.credit-page__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 6px 10px;
  margin-bottom: 14px;
}

.credit-page__filters-action {
  margin-right: 0;
}

.credit-page__alert {
  margin-bottom: 14px;
}

.credit-page__table {
  width: 100%;
}

.credit-page__primary-cell {
  display: grid;
  gap: 4px;
}

.credit-page__primary-cell span {
  color: var(--jd-text-soft);
  font-size: 0.9rem;
}

.credit-page__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.credit-page__positive {
  color: var(--el-color-success);
  font-weight: 600;
}

.credit-page__negative {
  color: var(--el-color-warning);
  font-weight: 600;
}
</style>

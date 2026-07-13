import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  adjustAdminUserCredits,
  fetchAdminCreditRules,
  fetchAdminCreditTransactions,
  fetchAdminCreditUsers,
  updateAdminCreditRule,
} from "@/admin/features/credits/services/creditService";
import type { AdminCreditRule, AdminCreditTransaction, AdminCreditUser } from "@/types";

interface CreditManagementApi {
  fetchUsers(filters: { q: string }): Promise<AdminCreditUser[]>;
  fetchRules(): Promise<AdminCreditRule[]>;
  fetchTransactions(userId: number): Promise<AdminCreditTransaction[]>;
  adjustUser(userId: number, payload: { amount: number; reason: string }): Promise<AdminCreditUser>;
  updateRule(featureCode: string, payload: { cost: number }): Promise<AdminCreditRule>;
}

interface CreditManagementMessages {
  success(message: string): void;
  warning(message: string): void;
  error(message: string): void;
}

interface CreditManagementDependencies {
  api?: CreditManagementApi;
  message?: CreditManagementMessages;
  loadOnMount?: boolean;
}

const defaultApi: CreditManagementApi = {
  fetchUsers: fetchAdminCreditUsers,
  fetchRules: fetchAdminCreditRules,
  fetchTransactions: fetchAdminCreditTransactions,
  adjustUser: adjustAdminUserCredits,
  updateRule: updateAdminCreditRule,
};

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function useCreditManagement(dependencies: CreditManagementDependencies = {}) {
  const api = dependencies.api ?? defaultApi;
  const message = dependencies.message ?? ElMessage;
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
  const userFilters = reactive({ q: "" });
  const adjustForm = reactive({ amount: 0, reason: "" });
  const ruleForm = reactive({ cost: 0 });

  const transactionDialogTitle = computed(() =>
    selectedUser.value ? `积分流水 - ${selectedUser.value.username}` : "积分流水",
  );
  const adjustDialogTitle = computed(() =>
    selectedUser.value ? `调整积分 - ${selectedUser.value.username}` : "调整积分",
  );
  const ruleDialogTitle = computed(() => {
    if (!selectedRule.value) return "编辑消耗规则";
    return `编辑消耗规则 - ${selectedRule.value.displayName || selectedRule.value.featureCode}`;
  });

  async function loadCreditUsers() {
    loadingUsers.value = true;
    userErrorMessage.value = "";
    try {
      creditUsers.value = (await api.fetchUsers(userFilters)) ?? [];
    } catch (error) {
      userErrorMessage.value = errorMessage(error, "读取用户积分失败");
    } finally {
      loadingUsers.value = false;
    }
  }

  async function loadCreditRules() {
    loadingRules.value = true;
    ruleErrorMessage.value = "";
    try {
      creditRules.value = (await api.fetchRules()) ?? [];
    } catch (error) {
      ruleErrorMessage.value = errorMessage(error, "读取积分规则失败");
    } finally {
      loadingRules.value = false;
    }
  }

  async function refreshActiveTab() {
    await (activeTab.value === "rules" ? loadCreditRules() : loadCreditUsers());
  }

  async function handleTabChange(name: string | number) {
    if (name === "rules" && creditRules.value.length === 0) await loadCreditRules();
  }

  async function openTransactionDialog(user: AdminCreditUser) {
    selectedUser.value = user;
    transactionDialogVisible.value = true;
    transactions.value = [];
    loadingTransactions.value = true;
    try {
      transactions.value = (await api.fetchTransactions(user.id)) ?? [];
    } catch (error) {
      message.error(errorMessage(error, "读取积分流水失败"));
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
    if (!selectedUser.value) return;
    if (!Number.isFinite(adjustForm.amount) || adjustForm.amount === 0) {
      message.warning("调整数量不能为 0");
      return;
    }
    if (!adjustForm.reason.trim()) {
      message.warning("填写调整原因");
      return;
    }
    submittingAdjustment.value = true;
    try {
      const updated = await api.adjustUser(selectedUser.value.id, {
        amount: adjustForm.amount,
        reason: adjustForm.reason.trim(),
      });
      const index = creditUsers.value.findIndex((item) => item.id === updated.id);
      if (index >= 0) creditUsers.value.splice(index, 1, updated);
      adjustDialogVisible.value = false;
      message.success("积分已调整");
    } catch (error) {
      message.error(errorMessage(error, "调整积分失败"));
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
    if (!selectedRule.value) return;
    if (!Number.isFinite(ruleForm.cost) || ruleForm.cost < 0) {
      message.warning("单次消耗不能小于 0");
      return;
    }
    submittingRule.value = true;
    try {
      const updated = await api.updateRule(selectedRule.value.featureCode, { cost: ruleForm.cost });
      const index = creditRules.value.findIndex((item) => item.featureCode === updated.featureCode);
      if (index >= 0) creditRules.value.splice(index, 1, updated);
      ruleDialogVisible.value = false;
      message.success("积分规则已更新");
    } catch (error) {
      message.error(errorMessage(error, "更新积分规则失败"));
    } finally {
      submittingRule.value = false;
    }
  }

  if (dependencies.loadOnMount !== false) onMounted(loadCreditUsers);

  return {
    activeTab, loadingUsers, loadingRules, loadingTransactions, submittingAdjustment, submittingRule,
    userErrorMessage, ruleErrorMessage, creditUsers, creditRules, transactions, transactionDialogVisible,
    adjustDialogVisible, ruleDialogVisible, userFilters, adjustForm, ruleForm, transactionDialogTitle,
    adjustDialogTitle, ruleDialogTitle, loadCreditUsers, loadCreditRules, refreshActiveTab, handleTabChange,
    openTransactionDialog, openAdjustDialog, submitAdjustment, openRuleDialog, submitRule,
  };
}

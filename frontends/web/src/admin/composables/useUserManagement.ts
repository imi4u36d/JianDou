import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createAdminUser,
  deleteAdminUser,
  disableAdminUser,
  enableAdminUser,
  fetchAdminUsers,
  fetchUserModelConfig,
  resetAdminUserModelConfigKeys,
  updateAdminUser,
  updateAdminUserPassword,
} from "@/admin/features/users/services/userService";
import type {
  AdminModelConfigProviderItem,
  AdminUser,
  CreateAdminUserRequest,
  UpdateAdminUserRequest,
  UserRole,
  UserStatus,
} from "@/types";

export interface UserManagementApi {
  fetchUsers: typeof fetchAdminUsers;
  createUser: typeof createAdminUser;
  updateUser: typeof updateAdminUser;
  deleteUser: typeof deleteAdminUser;
  enableUser: typeof enableAdminUser;
  disableUser: typeof disableAdminUser;
  updatePassword: typeof updateAdminUserPassword;
  fetchModelConfig: typeof fetchUserModelConfig;
  resetModelKeys: typeof resetAdminUserModelConfigKeys;
}

interface UserManagementDependencies {
  api?: UserManagementApi;
  confirm?: (
    message: string,
    title: string,
    options: { type: "warning"; confirmButtonText?: string; cancelButtonText?: string },
  ) => Promise<unknown>;
  message?: Pick<typeof ElMessage, "success" | "warning" | "error">;
  loadOnMount?: boolean;
}

const defaultApi: UserManagementApi = {
  fetchUsers: fetchAdminUsers,
  createUser: createAdminUser,
  updateUser: updateAdminUser,
  deleteUser: deleteAdminUser,
  enableUser: enableAdminUser,
  disableUser: disableAdminUser,
  updatePassword: updateAdminUserPassword,
  fetchModelConfig: fetchUserModelConfig,
  resetModelKeys: resetAdminUserModelConfigKeys,
};

export function useUserManagement(dependencies: UserManagementDependencies = {}) {
  const api = dependencies.api ?? defaultApi;
  const confirm = dependencies.confirm ?? ElMessageBox.confirm;
  const message = dependencies.message ?? ElMessage;
  const initialLoading = ref(true);
  const loading = ref(false);
  const submittingEditor = ref(false);
  const submittingPassword = ref(false);
  const loadingModelConfig = ref(false);
  const submittingModelKeys = ref(false);
  const users = ref<AdminUser[]>([]);
  const totalUsers = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const filters = reactive({ q: "", role: "" as UserRole | "", status: "" as UserStatus | "" });
  const editorVisible = ref(false);
  const editorMode = ref<"create" | "edit">("create");
  const editingUserId = ref<number | null>(null);
  const editorForm = reactive({
    username: "", password: "", role: "USER" as UserRole,
    status: "ACTIVE" as UserStatus, taskConcurrencyLimit: 1,
  });
  const passwordDialogVisible = ref(false);
  const passwordUserId = ref<number | null>(null);
  const passwordForm = reactive({ password: "" });
  const modelKeyDialogVisible = ref(false);
  const modelKeyUser = ref<AdminUser | null>(null);
  const modelKeyForm = reactive({
    providers: [] as Array<AdminModelConfigProviderItem & { apiKey: string }>,
  });
  const modelKeyDialogTitle = computed(() =>
    modelKeyUser.value ? `默认 Key - ${modelKeyUser.value.username}` : "默认 Key",
  );
  const summaryCards = computed(() => [
    { label: "全部账号", value: totalUsers.value, note: "可管理" },
    { label: "当前页", value: users.value.length, note: `每页 ${pageSize.value}` },
  ]);

  function resetEditorForm() {
    Object.assign(editorForm, {
      username: "", password: "", role: "USER", status: "ACTIVE", taskConcurrencyLimit: 1,
    });
    editingUserId.value = null;
  }

  async function loadUsers() {
    loading.value = true;
    try {
      const result = await api.fetchUsers({
        ...filters,
        offset: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value,
      });
      users.value = result?.items ?? [];
      totalUsers.value = result?.total ?? 0;
    } catch (error) {
      message.error(error instanceof Error ? error.message : "读取用户列表失败");
    } finally {
      loading.value = false;
      initialLoading.value = false;
    }
  }

  function handlePageChange() { void loadUsers(); }
  function handleSizeChange() { currentPage.value = 1; void loadUsers(); }
  function resetFilters() {
    Object.assign(filters, { q: "", role: "", status: "" });
    currentPage.value = 1;
    void loadUsers();
  }

  function openCreateDialog() {
    editorMode.value = "create";
    resetEditorForm();
    editorVisible.value = true;
  }

  function openEditDialog(user: AdminUser) {
    editorMode.value = "edit";
    editorVisible.value = true;
    editingUserId.value = user.id;
    Object.assign(editorForm, {
      username: user.username, password: "", role: user.role, status: user.status,
      taskConcurrencyLimit: user.taskConcurrencyLimit ?? 1,
    });
  }

  function openPasswordDialog(user: AdminUser) {
    passwordUserId.value = user.id;
    passwordForm.password = "";
    passwordDialogVisible.value = true;
  }

  async function openModelKeyDialog(user: AdminUser) {
    if (user.role !== "ADMIN") {
      message.warning("普通用户不支持配置模型 Key");
      return;
    }
    modelKeyUser.value = user;
    modelKeyDialogVisible.value = true;
    loadingModelConfig.value = true;
    try {
      const response = await api.fetchModelConfig(user.id);
      modelKeyForm.providers = (response.providers ?? []).map((provider) => ({
        ...provider,
        apiKey: "",
      }));
    } catch (error) {
      message.error(error instanceof Error ? error.message : "读取厂商列表失败");
    } finally {
      loadingModelConfig.value = false;
    }
  }

  async function submitEditor() {
    submittingEditor.value = true;
    try {
      if (editorMode.value === "create") {
        const payload: CreateAdminUserRequest = { ...editorForm };
        await api.createUser(payload);
        message.success("用户创建成功");
      } else if (editingUserId.value != null) {
        const payload: UpdateAdminUserRequest = {
          role: editorForm.role,
          status: editorForm.status,
          taskConcurrencyLimit: editorForm.taskConcurrencyLimit,
        };
        await api.updateUser(editingUserId.value, payload);
        message.success("用户信息已更新");
      }
      editorVisible.value = false;
      resetEditorForm();
      await loadUsers();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存用户失败");
    } finally {
      submittingEditor.value = false;
    }
  }

  async function submitPassword() {
    if (passwordUserId.value == null) return;
    submittingPassword.value = true;
    try {
      await api.updatePassword(passwordUserId.value, { password: passwordForm.password });
      passwordDialogVisible.value = false;
      passwordForm.password = "";
      message.success("用户密码已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新密码失败");
    } finally {
      submittingPassword.value = false;
    }
  }

  async function submitModelKeys() {
    if (!modelKeyUser.value) return;
    const providers = modelKeyForm.providers
      .map((provider) => ({ key: provider.key, apiKey: provider.apiKey.trim() }))
      .filter((provider) => provider.apiKey);
    if (!providers.length) {
      message.warning("请至少输入一个平台默认 Key");
      return;
    }
    submittingModelKeys.value = true;
    try {
      await api.resetModelKeys(modelKeyUser.value.id, { providers });
      modelKeyDialogVisible.value = false;
      modelKeyForm.providers = [];
      message.success("平台默认 Key 已重新设置");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "重新设置平台默认 Key 失败");
    } finally {
      submittingModelKeys.value = false;
    }
  }

  async function toggleUserStatus(user: AdminUser, action: "enable" | "disable") {
    try {
      await confirm(
        action === "enable" ? `确认启用账号 ${user.username} 吗？` : `确认禁用账号 ${user.username} 吗？`,
        "状态变更",
        { type: "warning" },
      );
      await (action === "enable" ? api.enableUser(user.id) : api.disableUser(user.id));
      message.success(action === "enable" ? "用户已启用" : "用户已禁用");
      await loadUsers();
    } catch (error) {
      if (error !== "cancel") message.error(error instanceof Error ? error.message : "状态更新失败");
    }
  }

  async function removeUser(user: AdminUser) {
    try {
      await confirm(`删除后不可恢复，确认删除账号 ${user.username} 吗？`, "删除用户", {
        type: "warning", confirmButtonText: "确认删除", cancelButtonText: "取消",
      });
      await api.deleteUser(user.id);
      message.success("用户已删除");
      await loadUsers();
    } catch (error) {
      if (error !== "cancel") message.error(error instanceof Error ? error.message : "删除用户失败");
    }
  }

  if (dependencies.loadOnMount !== false) onMounted(loadUsers);

  return {
    initialLoading, loading, submittingEditor, submittingPassword, loadingModelConfig,
    submittingModelKeys, users, totalUsers, currentPage, pageSize, filters, editorVisible,
    editorMode, editorForm, passwordDialogVisible, passwordForm, modelKeyDialogVisible,
    modelKeyForm, modelKeyDialogTitle, summaryCards, loadUsers, handlePageChange,
    handleSizeChange, resetFilters, openCreateDialog, openEditDialog, openPasswordDialog,
    openModelKeyDialog, submitEditor, submitPassword, submitModelKeys, toggleUserStatus, removeUser,
  };
}

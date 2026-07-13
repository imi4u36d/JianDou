import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createAdminInvite,
  fetchAdminInvites,
  revokeAdminInvite,
} from "@/admin/features/invites/services/inviteService";
import { inviteSummaryCards } from "@/admin/features/invites/invite-management-presenters";
import type { AdminInvite, UserRole } from "@/types";

interface InviteManagementDependencies {
  fetch?: typeof fetchAdminInvites;
  create?: typeof createAdminInvite;
  revoke?: typeof revokeAdminInvite;
  confirm?: (
    message: string,
    title: string,
    options: {
      type: "warning";
      confirmButtonText: string;
      cancelButtonText: string;
    },
  ) => Promise<unknown>;
  copy?: (value: string) => Promise<void>;
  message?: Pick<typeof ElMessage, "success" | "info" | "error">;
  loadOnMount?: boolean;
}

export function useInviteManagement(dependencies: InviteManagementDependencies = {}) {
  const fetchInvites = dependencies.fetch ?? fetchAdminInvites;
  const createInvite = dependencies.create ?? createAdminInvite;
  const revoke = dependencies.revoke ?? revokeAdminInvite;
  const confirm = dependencies.confirm ?? ElMessageBox.confirm;
  const copy = dependencies.copy ?? ((value: string) => navigator.clipboard.writeText(value));
  const message = dependencies.message ?? ElMessage;
  const loading = ref(false);
  const submitting = ref(false);
  const invites = ref<AdminInvite[]>([]);
  const createDialogVisible = ref(false);
  const createForm = reactive({ role: "USER" as UserRole });
  const summaryCards = computed(() => inviteSummaryCards(invites.value));

  async function loadInvites() {
    loading.value = true;
    try {
      invites.value = (await fetchInvites()) ?? [];
    } catch (error) {
      message.error(error instanceof Error ? error.message : "读取邀请码列表失败");
    } finally {
      loading.value = false;
    }
  }

  function openCreateDialog() {
    createForm.role = "USER";
    createDialogVisible.value = true;
  }

  async function copyInviteCode(code: string) {
    try {
      await copy(code);
      message.success("邀请码已复制");
    } catch {
      message.info(`邀请码：${code}`);
    }
  }

  async function submitCreate() {
    submitting.value = true;
    try {
      const created = await createInvite({ role: createForm.role });
      createDialogVisible.value = false;
      message.success(`邀请码 ${created.code} 已生成`);
      await copyInviteCode(created.code);
      await loadInvites();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "生成邀请码失败");
    } finally {
      submitting.value = false;
    }
  }

  async function revokeInvite(invite: AdminInvite) {
    try {
      await confirm(`确认撤销邀请码 ${invite.code} 吗？`, "撤销邀请码", {
        type: "warning",
        confirmButtonText: "确认撤销",
        cancelButtonText: "取消",
      });
      await revoke(invite.id);
      message.success("邀请码已撤销");
      await loadInvites();
    } catch (error) {
      if (error !== "cancel") message.error(error instanceof Error ? error.message : "撤销邀请码失败");
    }
  }

  if (dependencies.loadOnMount !== false) onMounted(loadInvites);

  return {
    loading, submitting, invites, createDialogVisible, createForm, summaryCards,
    loadInvites, openCreateDialog, submitCreate, revokeInvite, copyInviteCode,
  };
}

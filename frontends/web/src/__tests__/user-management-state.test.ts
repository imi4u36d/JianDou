import { describe, expect, it, vi } from "vitest";
import {
  useUserManagement,
  type UserManagementApi,
} from "@/admin/composables/useUserManagement";
import type { AdminModelConfigProviderItem, AdminModelConfigResponse, AdminUser } from "@/types";

const adminUser = (overrides: Partial<AdminUser> = {}): AdminUser => ({
  id: 7,
  username: "admin",
  role: "ADMIN",
  status: "ACTIVE",
  taskConcurrencyLimit: 2,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  ...overrides,
});

const provider: AdminModelConfigProviderItem = {
  key: "openai",
  provider: "openai",
  vendor: "OpenAI",
  kinds: ["text"],
  baseUrl: "",
  taskBaseUrl: "",
  endpointHost: "",
  taskEndpointHost: "",
  apiKeyConfigured: false,
  baseUrlConfigured: false,
  taskBaseUrlConfigured: false,
  extras: {},
  modelNames: ["gpt-test"],
};

const modelConfig: AdminModelConfigResponse = {
  configSource: "test",
  summary: {
    providerCount: 1,
    vendorCount: 1,
    modelCount: 0,
    readyModelCount: 0,
    readyTextModelCount: 0,
    readyVisionModelCount: 0,
    readyImageModelCount: 0,
    readyVideoModelCount: 0,
  },
  defaults: {
    aspectRatio: "16:9",
    imageSize: "1024x1024",
    videoSize: "720p",
    videoDurationSeconds: 5,
    timeoutSeconds: 60,
    temperature: 0.7,
    maxTokens: 1024,
  },
  providers: [provider],
  models: [],
  configErrors: [],
};

function harness() {
  const user = adminUser();
  const api = {
    fetchUsers: vi.fn(async () => ({ items: [user], total: 1, offset: 0, limit: 20 })),
    createUser: vi.fn(async () => user),
    updateUser: vi.fn(async () => user),
    deleteUser: vi.fn(async () => undefined),
    enableUser: vi.fn(async () => user),
    disableUser: vi.fn(async () => user),
    updatePassword: vi.fn(async () => user),
    fetchModelConfig: vi.fn(async () => modelConfig),
    resetModelKeys: vi.fn(async () => modelConfig),
  } satisfies UserManagementApi;
  const message = { success: vi.fn(), warning: vi.fn(), error: vi.fn() };
  const confirm = vi.fn(async () => undefined);
  const state = useUserManagement({ api, message, confirm, loadOnMount: false });
  return { api, confirm, message, state, user };
}

describe("user management state", () => {
  it("loads paginated users and submits a create command", async () => {
    const { api, state } = harness();
    state.currentPage.value = 2;
    await state.loadUsers();

    expect(api.fetchUsers).toHaveBeenCalledWith({
      q: "",
      role: "",
      status: "",
      offset: 20,
      limit: 20,
    });
    expect(state.users.value).toHaveLength(1);

    state.openCreateDialog();
    Object.assign(state.editorForm, { username: "new-user", password: "secret" });
    await state.submitEditor();
    expect(api.createUser).toHaveBeenCalledWith({
      username: "new-user",
      password: "secret",
      role: "USER",
      status: "ACTIVE",
      taskConcurrencyLimit: 1,
    });
    expect(state.editorVisible.value).toBe(false);
  });

  it("validates model-key access and trims submitted keys", async () => {
    const { api, message, state, user } = harness();
    await state.openModelKeyDialog(adminUser({ role: "USER" }));
    expect(message.warning).toHaveBeenCalledWith("普通用户不支持配置模型 Key");
    expect(api.fetchModelConfig).not.toHaveBeenCalled();

    await state.openModelKeyDialog(user);
    state.modelKeyForm.providers[0].apiKey = "  key-value  ";
    await state.submitModelKeys();
    expect(api.resetModelKeys).toHaveBeenCalledWith(7, {
      providers: [{ key: "openai", apiKey: "key-value" }],
    });
    expect(state.modelKeyDialogVisible.value).toBe(false);
  });

  it("confirms status changes and refreshes the list", async () => {
    const { api, confirm, state, user } = harness();
    await state.toggleUserStatus(user, "disable");
    expect(confirm).toHaveBeenCalledWith("确认禁用账号 admin 吗？", "状态变更", {
      type: "warning",
    });
    expect(api.disableUser).toHaveBeenCalledWith(7);
    expect(api.fetchUsers).toHaveBeenCalledOnce();
  });
});
